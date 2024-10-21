import graphene
from graphene_django.types import DjangoObjectType

from .models import PairCreated


class uniswap__PairCreated(DjangoObjectType):
    class Meta:
        model = PairCreated
        fields = "__all__"
