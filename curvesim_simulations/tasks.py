from celery import shared_task
from .models import Pool
from django.utils import timezone
import logging

import curvesim
from curvesim.metrics.results.sim_results import SimResults
from .models import SimulationParameters, SimulationRun, TimeseriesData, SummaryMetrics, PriceErrorDistribution, Pool
from django.utils.timezone import make_aware
from pandas import DataFrame
from django.utils import timezone
from django.core.cache import cache
from typing import List
import logging

CACHE_TTL = 86400  # 24hours
CACHE_PREFIX = "curvesim"


@shared_task(name="run_simulation_task")
def run_simulation_task():
    print(f"Simulation task started at {timezone.now()}")

    enabled_pools = Pool.objects.filter(enabled=True)

    for pool in enabled_pools:
        logging.info(f"Running simulation for pool {pool.name}")
        _run_and_save_simulation(pool)

    return f"Run and saves simulations for {enabled_pools.count()} pools"


def _run_and_save_simulation(pool: Pool):
    params = pool.params_dict
    logging.info(f"Running simulation for pool {pool.name} with parameters {params}")
    raw_results: SimResults = curvesim.autosim(pool.address, **params)
    _format_and_save_results(raw_results, pool.name)
    logging.info(f"Simulation for pool {pool.name} completed")


def _format_and_save_results(results: SimResults, pool_name: str) -> None:

    summary_df = results.summary(full=True)

    for index, summary_row in summary_df.iterrows():

        sim_params, _ = _get_or_create_simulation_parameters(summary_row)

        sim_run = SimulationRun.objects.create(
            parameters=sim_params,
            pool_name=pool_name,
            run_date=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0),
        )
        data_per_trade: DataFrame = results.data_per_trade[results.data_per_trade["run"] == index]
        price_error_distribution = data_per_trade["price_error"].value_counts(normalize=True)

        _save_timeseries_data(sim_run, data_per_trade)
        _save_price_error_distribution(sim_run, price_error_distribution)
        _save_summary_metrics(sim_run, summary_row)


def _get_or_create_simulation_parameters(summary_row: DataFrame) -> tuple[SimulationParameters, bool]:
    return SimulationParameters.objects.get_or_create(
        A=summary_row["A"],
        D=summary_row["D"],
        fee=summary_row["fee"],
        fee_mul=summary_row["fee_mul"],
        admin_fee=summary_row["admin_fee"],
    )


def _save_timeseries_data(sim_run: SimulationRun, data_per_trade: DataFrame) -> None:
    for _, row in data_per_trade.iterrows():
        TimeseriesData.objects.create(
            simulation_run=sim_run,
            timestamp=row["timestamp"].to_pydatetime(),
            pool_value_virtual=row["pool_value_virtual"],
            pool_value=row["pool_value"],
            pool_balance=row["pool_balance"],
            liquidity_density=row["liquidity_density"],
            pool_volume=row["pool_volume"],
            arb_profit=row["arb_profit"],
            pool_fees=row["pool_fees"],
        )


def _save_price_error_distribution(sim_run: SimulationRun, price_error_distribution: DataFrame) -> None:
    for error_value, frequency in price_error_distribution.items():
        PriceErrorDistribution.objects.get_or_create(
            simulation_run=sim_run, price_error=error_value, defaults={"frequency": frequency}
        )


def _save_summary_metrics(sim_run: SimulationRun, summary_row: DataFrame) -> None:
    summary_row = summary_row.to_dict()
    SummaryMetrics.objects.create(
        simulation_run=sim_run,
        pool_value_virtual_annualized_returns=summary_row["pool_value_virtual annualized_returns"],
        pool_value_annualized_returns=summary_row["pool_value annualized_returns"],
        pool_balance_median=summary_row["pool_balance median"],
        pool_balance_min=summary_row["pool_balance min"],
        liquidity_density_median=summary_row["liquidity_density median"],
        liquidity_density_min=summary_row["liquidity_density min"],
        pool_volume_sum=summary_row["pool_volume sum"],
        arb_profit_sum=summary_row["arb_profit sum"],
        pool_fees_sum=summary_row["pool_fees sum"],
        price_error_median=summary_row["price_error median"],
    )


@shared_task(name="warmup_graphql_cache")
def warmup_graphql_cache():
    """
    Task to pre-warm the GraphQL query cache for commonly accessed data.
    Helps reduce latency for initial user requests.
    """
    logging.info("Starting GraphQL cache warmup")
    warmed_keys: List[str] = []

    try:
        # Cache all_pools
        pools = Pool.objects.filter(enabled=True)
        cache_key = f"{CACHE_PREFIX}all_pools"
        cache.set(cache_key, pools, CACHE_TTL)
        warmed_keys.append(cache_key)

        # Cache all_simulations
        simulations = list(SimulationRun.objects.all().order_by("-run_date").select_related("parameters"))
        cache_key = f"{CACHE_PREFIX}all_simulations"
        cache.set(cache_key, simulations, CACHE_TTL)
        warmed_keys.append(cache_key)

        # Cache pool_dates and latest simulation for each pool
        for pool in pools:
            # Pool dates
            filter_kwargs = _build_params_filter(pool.params_dict)
            params = SimulationParameters.objects.filter(**filter_kwargs)
            dates = list(
                SimulationRun.objects.filter(parameters__in=params)
                .values_list("run_date", flat=True)
                .order_by("-run_date")
                .distinct()
            )

            cache_key = f"{CACHE_PREFIX}pool_dates_{pool.name}"
            cache.set(cache_key, dates, CACHE_TTL)
            warmed_keys.append(cache_key)

            # Latest simulation
            latest_sim = (
                SimulationRun.objects.filter(parameters__in=params)
                .order_by("-run_date")
                .prefetch_related(
                    "parameters",
                    "summary_metrics",
                    "timeseries_data",
                    "price_error_distribution",
                )
                .first()
            )
            if latest_sim:
                cache_key = f"{CACHE_PREFIX}sim_{pool.name}_None"
                cache.set(cache_key, latest_sim, CACHE_TTL)
                warmed_keys.append(cache_key)

        logging.info(f"Cache warmup completed. Warmed up {len(warmed_keys)} keys")
        return f"Successfully warmed up {len(warmed_keys)} cache keys"

    except Exception as e:
        logging.error(f"Error during cache warmup: {str(e)}")
        for key in warmed_keys:
            cache.delete(key)
        raise


def _build_params_filter(params_dict):
    """
    Helper function to build filter kwargs from params dict.
    Same implementation as in Query class to maintain consistency.
    """
    filter_kwargs = {}

    for key, value in params_dict.items():
        if value is not None and key in ["A", "D", "fee", "fee_mul", "admin_fee"]:
            if key == "fee" and isinstance(value, list):
                fee_values = [float(v) / 1e10 for v in value]
                filter_kwargs[f"{key}__in"] = fee_values
            else:
                filter_kwargs[f"{key}__in"] = value

    return filter_kwargs
