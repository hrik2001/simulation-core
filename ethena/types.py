from graphene import ObjectType, JSONString, String, List
from graphene_django import DjangoObjectType
from .models import ChainMetrics, CollateralMetrics, ReserveFundMetrics, ReserveFundBreakdown, UniswapPoolSnapshots, \
    CurvePoolInfo, StakingMetrics


class SnapshotType(ObjectType):
    snapshot = JSONString()
    timestamp = String()

class AggregatedSnapshotsType(ObjectType):
    address = String()
    snapshots = List(SnapshotType)

class ChainMetricsType(DjangoObjectType):
    class Meta:
        model = ChainMetrics

class CollateralMetricsType(DjangoObjectType):
    class Meta:
        model = CollateralMetrics

class ReserveFundMetricsType(DjangoObjectType):
    class Meta:
        model = ReserveFundMetrics

class ReserveFundBreakdownType(DjangoObjectType):
    class Meta:
        model = ReserveFundBreakdown

class UniswapMetricsType(DjangoObjectType):
    class Meta:
        model = UniswapPoolSnapshots

class CurvePoolMetricsType(DjangoObjectType):
    class Meta:
        model = CurvePoolInfo

class StakingMetricsType(DjangoObjectType):
    class Meta:
        model = StakingMetrics
