from datetime import datetime

import graphene
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Max, F
from django.db.models.functions import JSONObject
from graphene import Int, String

from ethena.models import ReserveFundMetrics, CollateralMetrics, ChainMetrics, ReserveFundBreakdown, UniswapPoolSnapshots, \
    CurvePoolInfo, CurvePoolSnapshots
from ethena.types import ChainMetricsType, CollateralMetricsType, ReserveFundMetricsType, ReserveFundBreakdownType, \
    CurvePoolMetricsType, SnapshotType, AggregatedSnapshotsType


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


    def resolve_chain_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
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
        return queryset

    def resolve_collateral_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
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
        return queryset

    def resolve_reserve_fund_metrics(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
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
        return queryset

    def resolve_reserve_fund_breakdown(self, info, start_time=None, end_time=None, limit=None, sort_by=None):
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

schema = graphene.Schema(query=Query)
