from graphene import ObjectType, JSONString, String, List, Int
from graphene_django import DjangoObjectType

from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics, CurveLlammaTrades, CurveLlammaEvents, CurveCr, \
    CurveMarkets, CurveScores, CurveDebtCeilingScore


class CurveMarketsType(DjangoObjectType):
    class Meta:
        model = CurveMarkets


class DebtCeilingType(DjangoObjectType):
    class Meta:
        model = DebtCeiling


class ControllerMetadataType(DjangoObjectType):
    class Meta:
        model = ControllerMetadata


class CurveMetricsType(DjangoObjectType):
    class Meta:
        model = CurveMetrics


class SnapshotType(ObjectType):
    data = JSONString()
    timestamp = String()


class AggregatedSnapshotsType(ObjectType):
    chain = String()
    controller = String()
    snapshots = List(SnapshotType)


class CurveLlammaTradesType(DjangoObjectType):
    class Meta:
        model = CurveLlammaTrades


class CurveLlammaEventsType(DjangoObjectType):
    class Meta:
        model = CurveLlammaEvents


class CurveCrType(DjangoObjectType):
    class Meta:
        model = CurveCr


class CurveScoresType(DjangoObjectType):
    class Meta:
        model = CurveScores


class CurveDebtCeilingScoresType(ObjectType):
    chain = String()
    controller = String()
    createdAt = Int()
    score = String()
