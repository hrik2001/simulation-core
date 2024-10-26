from .models import SimulationRun, Pool, TimeseriesData, SummaryMetrics, PriceErrorDistribution, SimulationParameters
from graphene_django import DjangoObjectType


class PoolType(DjangoObjectType):
    class Meta:
        model = Pool
        fields = ("id", "name", "address", "params_dict", "enabled")


class SimulationParametersType(DjangoObjectType):
    class Meta:
        model = SimulationParameters
        fields = ("id", "A", "fee", "D", "fee_mul")


class TimeseriesDataType(DjangoObjectType):
    class Meta:
        model = TimeseriesData
        fields = (
            "id",
            "timestamp",
            "pool_value_virtual",
            "pool_value",
            "pool_balance",
            "liquidity_density",
            "pool_volume",
            "arb_profit",
            "pool_fees",
        )


class SummaryMetricsType(DjangoObjectType):
    class Meta:
        model = SummaryMetrics
        fields = (
            "id",
            "pool_value_virtual_annualized_returns",
            "pool_value_annualized_returns",
            "pool_balance_median",
            "pool_balance_min",
            "liquidity_density_median",
            "liquidity_density_min",
            "pool_volume_sum",
            "arb_profit_sum",
            "pool_fees_sum",
            "price_error_median",
        )


class PriceErrorDistributionType(DjangoObjectType):
    class Meta:
        model = PriceErrorDistribution
        fields = ("id", "price_error", "frequency")


class SimulationRunType(DjangoObjectType):
    class Meta:
        model = SimulationRun
        fields = ("id", "parameters", "run_date", "timeseries_data", "summary_metrics", "price_error_distribution")
