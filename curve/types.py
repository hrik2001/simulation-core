from graphene_django import DjangoObjectType

from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics


class DebtCeilingType(DjangoObjectType):
    class Meta:
        model = DebtCeiling


class ControllerMetadataType(DjangoObjectType):
    class Meta:
        model = ControllerMetadata


class CurveMetricsType(DjangoObjectType):
    class Meta:
        model = CurveMetrics
