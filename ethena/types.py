from graphene_django import DjangoObjectType
from .models import ChainMetrics, CollateralMetrics, ReserveFundMetrics, ReserveFundBreakdown, UniswapMetrics, \
    CurvePoolMetrics, CurvePoolSnapshots


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
        model = UniswapMetrics

class CurvePoolMetricsType(DjangoObjectType):
    class Meta:
        model = CurvePoolMetrics

class CurvePoolSnapshotsType(DjangoObjectType):
    class Meta:
        model = CurvePoolSnapshots
