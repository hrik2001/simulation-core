from datetime import datetime

import graphene
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import F
from django.db.models.functions import JSONObject
from graphene import Int, String

from django.core.cache import cache
from ethena.models import ReserveFundMetrics, CollateralMetrics, ChainMetrics, ReserveFundBreakdown, \
    UniswapPoolSnapshots, \
    CurvePoolInfo, CurvePoolSnapshots, StakingMetrics, ExitQueueMetrics, ApyMetrics, FundingRateMetrics, \
    UstbYieldMetrics, BuidlYieldMetrics, UsdmMetrics, BuidlRedemptionMetrics
from ethena.types import ChainMetricsType, CollateralMetricsType, ReserveFundMetricsType, ReserveFundBreakdownType, \
    CurvePoolMetricsType, SnapshotType, AggregatedSnapshotsType, StakingMetricsType, ExitQueueMetricsType, \
    FundingRateMetricsType, UstbYieldMetricsType, BuidlYieldMetricsType, \
    UsdmMetricsType, BuidlRedemptionMetricsType, AggregatedApyMetricsType, ApyMetricApiType, FundingMetricsApyType


def _aggregate_snapshots(model, start_time=None, end_time=None, limit=None, sort_by=None):
    queryset = model.objects.all()
    if start_time:
        queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
    if end_time:
        queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))
    if limit:
        queryset = queryset[:limit]
    if not sort_by:
        sort_by = "timestamp"

    aggregated_data = (
        queryset
        .values('address')
        .annotate(
            snapshots=ArrayAgg(
                JSONObject(snapshot=F('snapshot'), timestamp=F('timestamp')),
                ordering=sort_by
            )
        )
    )

    result = []
    for data in aggregated_data:
        snapshots = [
            SnapshotType(
                snapshot=item['snapshot'],
                timestamp=item['timestamp'],
            )
            for item in data['snapshots']
        ]
        result.append(AggregatedSnapshotsType(address=data['address'], snapshots=snapshots))

    return result


class Query(graphene.ObjectType):
    chain_metrics = graphene.List(ChainMetricsType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String())
    collateral_metrics = graphene.List(CollateralMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                       sort_by=String())
    reserve_fund_metrics = graphene.List(ReserveFundMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                         sort_by=String())
    reserve_fund_breakdown = graphene.List(ReserveFundBreakdownType, start_time=Int(), end_time=Int(), limit=Int(),
                                           sort_by=String())
    uniswap_pool_snapshots = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(),
                                           sort_by=String())
    curve_pool_metrics = graphene.List(CurvePoolMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                       sort_by=String())
    curve_pool_snapshots = graphene.List(AggregatedSnapshotsType, start_time=Int(), end_time=Int(), limit=Int(),
                                         sort_by=String())
    staking_metrics = graphene.List(StakingMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                    sort_by=String())
    exit_queue_metrics = graphene.List(ExitQueueMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                       sort_by=String())
    apy_metrics = graphene.List(AggregatedApyMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                sort_by=String())
    funding_rate_metrics = graphene.List(FundingRateMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                         sort_by=String())
    ustb_yield_metrics = graphene.List(UstbYieldMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                       sort_by=String())
    buidl_yield_metrics = graphene.List(BuidlYieldMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                        sort_by=String())
    buidl_redemption_metrics = graphene.List(BuidlRedemptionMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                             sort_by=String())
    usdm_metrics = graphene.List(UsdmMetricsType, start_time=Int(), end_time=Int(), limit=Int(),
                                 sort_by=String())

    def resolve_chain_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        key = f"chain-metrics-{start_time}-{end_time}-{limit}-{sort_by}"
        cached_response = cache.get(key, None)
        if cached_response is not None:
            return cached_response
        print("cached_response", cached_response)

        queryset = ChainMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(block_timestamp__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(block_timestamp__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('block_timestamp')
        if limit:
            queryset = queryset[:limit]

        cache.set(key, queryset, timeout=3600)
        return queryset

    def resolve_collateral_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        key = f"collateral-metrics-{start_time}-{end_time}-{limit}-{sort_by}"
        cached_response = cache.get(key, None)
        if cached_response is not None:
            return cached_response

        queryset = CollateralMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]

        cache.set(key, queryset, timeout=3600)
        return queryset

    def resolve_reserve_fund_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        key = f"reserve-fund-metrics-{start_time}-{end_time}-{limit}-{sort_by}"
        cached_response = cache.get(key, None)
        if cached_response is not None:
            return cached_response

        queryset = ReserveFundMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('timestamp')
        if limit:
            queryset = queryset[:limit]

        cache.set(key, queryset, timeout=3600)
        return queryset

    def resolve_reserve_fund_breakdown(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        key = f"reserve-fund-breakdown-{start_time}-{end_time}-{limit}-{sort_by}"
        cached_response = cache.get(key, None)
        if cached_response is not None:
            return cached_response

        queryset = ReserveFundBreakdown.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]

        cache.set(key, queryset, timeout=3600)
        return queryset

    def resolve_curve_pool_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = CurvePoolInfo.objects.all()
        if start_time:
            queryset = queryset.filter(created_at__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(created_at__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('created_at')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_curve_pool_snapshots(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        return _aggregate_snapshots(CurvePoolSnapshots, start_time, end_time, limit, sort_by)

    def resolve_uniswap_pool_snapshots(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        return _aggregate_snapshots(UniswapPoolSnapshots, start_time, end_time, limit, sort_by)

    def resolve_staking_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = StakingMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(day__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(day__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('day')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_exit_queue_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = ExitQueueMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(unlock_day__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(unlock_day__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('unlock_day')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_apy_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = ApyMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))
        if limit:
            queryset = queryset[:limit]

        queryset = (
            queryset
            .values('symbol')
            .annotate(
                metrics=ArrayAgg(
                    JSONObject(timestamp=F('timestamp'), apy=F('apy')),
                    ordering=sort_by
                )
            )
        )

        aggregated_data = []
        for row in queryset:
            aggregated_data.append(AggregatedApyMetricsType(
                symbol=row["symbol"],
                metrics=[ApyMetricApiType(
                    timestamp=m["timestamp"],
                    apy=m["apy"]
                ) for m in row["metrics"]]
            ))
        return aggregated_data

    def resolve_funding_rate_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = FundingRateMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(timestamp__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(timestamp__lte=datetime.fromtimestamp(end_time))

        queryset = (
            queryset
            .values('symbol', 'exchange')
            .annotate(
                metrics=ArrayAgg(
                    JSONObject(timestamp=F('timestamp'), rate=F('rate')),
                    ordering=sort_by
                )
            )
        )

        aggregated_data = []
        for row in queryset:
            aggregated_data.append(FundingRateMetricsType(
                symbol=row["symbol"],
                exchange=row["exchange"],
                metrics=[FundingMetricsApyType(
                    timestamp=m["timestamp"],
                    rate=m["rate"]
                ) for m in row["metrics"]]
            ))

        return queryset

    def resolve_ustb_yield_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = UstbYieldMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(date__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(date__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('date')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_buidl_yield_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = BuidlYieldMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(date__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(date__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('date')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_buidl_redemption_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = BuidlRedemptionMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(date__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(date__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('date')
        if limit:
            queryset = queryset[:limit]
        return queryset

    def resolve_usdm_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
        queryset = UsdmMetrics.objects.all()
        if start_time:
            queryset = queryset.filter(date__gte=datetime.fromtimestamp(start_time))
        if end_time:
            queryset = queryset.filter(date__lte=datetime.fromtimestamp(end_time))
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('date')
        if limit:
            queryset = queryset[:limit]
        return queryset


schema = graphene.Schema(query=Query)
