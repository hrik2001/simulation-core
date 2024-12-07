import graphene
from graphene_django import DjangoObjectType
from django.db.models import Prefetch
from django.utils import timezone
from typing import Dict, Any
from .types import PoolType, SimulationRunType, TimeseriesDataType
from .models import Pool, SimulationRun, TimeseriesData, SimulationParameters

from graphene import Schema
import json
import hashlib
from django.core.cache import cache

ISO_FORMAT_LENGTH = 19
CACHE_TTL = 86400  # 24hours
CACHE_PREFIX = "curvesim"


class Query(graphene.ObjectType):
    all_pools = graphene.List(PoolType)
    all_simulations = graphene.List(SimulationRunType)
    simulation_by_pool_and_date = graphene.List(
        SimulationRunType, pool_name=graphene.String(required=True), date=graphene.String()
    )
    pool_dates = graphene.List(graphene.DateTime, pool_name=graphene.String(required=True))
    simulations_summary = graphene.JSONString()

    def resolve_all_pools(self, info):
        cache_key = f"{CACHE_PREFIX}all_pools"
        result = cache.get(cache_key)

        if result is None:
            result = list(Pool.objects.filter(enabled=True))
            cache.set(cache_key, result, CACHE_TTL)

        return result

    def resolve_all_simulations(self, info):
        cache_key = f"{CACHE_PREFIX}all_simulations"
        result = cache.get(cache_key)

        if result is None:
            result = list(SimulationRun.objects.all().order_by("-run_date").select_related("parameters"))
            cache.set(cache_key, result, CACHE_TTL)

        return result

    @staticmethod
    def _build_params_filter(params_dict):
        filter_kwargs = {}

        for key, value in params_dict.items():
            if value is not None and key in ["A", "D", "fee", "fee_mul", "admin_fee"]:
                if key == "fee" and isinstance(value, list):
                    fee_values = [float(v) / 1e10 for v in value]
                    filter_kwargs[f"{key}__in"] = fee_values
                else:
                    filter_kwargs[f"{key}__in"] = value

        return filter_kwargs

    def resolve_simulation_by_pool_and_date(self, info, pool_name, date=None):

        pool = Pool.objects.filter(name=pool_name).first()
        if not pool:
            return []

        date_obj = timezone.datetime.strptime(date[:19], "%Y-%m-%dT%H:%M:%S")
        query = SimulationRun.objects.filter(run_date__date=date_obj.date(), pool_name=pool_name)

        result = query.prefetch_related(
            "parameters",
            "summary_metrics",
            Prefetch("timeseries_data", queryset=TimeseriesData.objects.order_by("timestamp")),
            "price_error_distribution",
        )

        return list(result)

    def resolve_pool_dates(self, info, pool_name):
        cache_key = f"{CACHE_PREFIX}pool_dates_{pool_name}"
        dates_list = cache.get(cache_key)

        if dates_list is not None:
            return dates_list

        pool = Pool.objects.filter(name=pool_name).first()
        if not pool:
            return []

        filter_kwargs = Query._build_params_filter(pool.params_dict)
        params = SimulationParameters.objects.filter(**filter_kwargs)

        dates = (
            SimulationRun.objects.filter(parameters__in=params)
            .values_list("run_date", flat=True)
            .order_by("-run_date")
            .distinct()
        )
        dates_list = list(dates)
        cache.set(cache_key, dates_list, CACHE_TTL)

        return dates_list

    def resolve_simulations_summary(self, info) -> Dict[str, Any]:
        pools = Pool.objects.filter(enabled=True)
        simulations = SimulationRun.objects.all().order_by("-run_date").select_related("parameters")

        dates_by_pool = {}
        for pool in pools:
            filter_kwargs = Query._build_params_filter(pool.params_dict)
            params = SimulationParameters.objects.filter(**filter_kwargs)
            dates = list(
                SimulationRun.objects.filter(parameters__in=params)
                .values_list("run_date", flat=True)
                .order_by("-run_date")
                .distinct()
            )
            dates_by_pool[pool.name] = [d.isoformat() for d in dates]

        return {
            "simulations": [
                {
                    "id": sim.pool_name,
                    "run_date": sim.run_date.isoformat(),
                    "A": sim.parameters.A,
                    "fee": sim.parameters.fee,
                    "D": sim.parameters.D,
                    "fee_mul": sim.parameters.fee_mul,
                }
                for sim in simulations
            ],
            "pools": [
                {
                    "name": pool.name,
                    "address": pool.address,
                    "params": pool.params_dict,
                }
                for pool in pools
            ],
            "dates_by_pool": dates_by_pool,
        }


class CachedSchema(Schema):
    def __init__(self, ttl=3600, **kwargs):
        super().__init__(**kwargs)
        self.ttl = ttl

    def execute(self, *args, **kwargs):
        query = kwargs.get("query", args[0] if args else "")
        variables = kwargs.get("variables", {})

        if kwargs.get("operation_name", "").lower() == "mutation":
            return super().execute(*args, **kwargs)

        cache_key = f"graphql:{hashlib.md5(f'{query}:{json.dumps(variables, sort_keys=True)}'.encode()).hexdigest()}"

        cached = cache.get(cache_key)

        if cached:
            return cached

        result = super().execute(*args, **kwargs)
        if result:
            cache.set(cache_key, result, self.ttl)

        return result


schema = CachedSchema(query=Query, ttl=CACHE_TTL)
