from graphene import ObjectType, JSONString, String, List, Int
from graphene_django import DjangoObjectType

from curve.models import Top5Debt, ControllerMetadata, CurveMetrics, CurveLlammaTrades, CurveLlammaEvents, CurveCr, \
    CurveMarkets, CurveScores, Simuliq, CurveScoresDetail, AaveUserData, CurveUserData


class CurveMarketsType(DjangoObjectType):
    class Meta:
        model = CurveMarkets


class Top5DebtType(DjangoObjectType):
    class Meta:
        model = Top5Debt


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


class CurveScoresDetailType(DjangoObjectType):
    class Meta:
        model = CurveScoresDetail


class CurveDebtCeilingScoresType(ObjectType):
    chain = String()
    controller = String()
    createdAt = Int()
    score = String()


class SimuliqType(DjangoObjectType):
    class Meta:
        model = Simuliq


class AaveUserDataType(DjangoObjectType):
    class Meta:
        model = AaveUserData


class CurveUserDataType(DjangoObjectType):
    class Meta:
        model = CurveUserData
