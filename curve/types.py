from graphene_django import DjangoObjectType

from curve.models import DebtCeiling


class DebtCeilingType(DjangoObjectType):
    class Meta:
        model = DebtCeiling
