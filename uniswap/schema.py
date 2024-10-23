import graphene
from graphene import ObjectType, String
from graphene_django.types import DjangoObjectType
from .models import PairCreated
from .types import uniswap__PairCreated


class Query(ObjectType):
    search_pairs = graphene.List(uniswap__PairCreated, token0=String(), token1=String())

    def resolve_search_pairs(self, info, token0=None, token1=None):
        queryset = PairCreated.objects.all()

        if token0:
            queryset = queryset.filter(token0=token0)

        if token1:
            queryset = queryset.filter(token1=token1)

        return queryset

schema = graphene.Schema(query=Query)
