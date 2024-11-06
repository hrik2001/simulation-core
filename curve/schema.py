from datetime import datetime

import graphene
from graphene import Int, String

from core.models import Chain
from curve.models import DebtCeiling
from curve.types import DebtCeilingType


class Query(graphene.ObjectType):
    debt_ceiling = graphene.List(DebtCeilingType, start_time=Int(), end_time=Int(), limit=Int(), sort_by=String(),
                                 chain=String(), controller=String())

    def resolve_debt_ceiling(self, info, start_time=None, end_time=None, limit=None, sort_by=None, chain=None, controller=None):
        queryset = DebtCeiling.objects.all()

        if chain is None:
            chain = "ethereum"
        chain_obj = Chain.objects.get(chain_name__iexact=chain)
        queryset = queryset.filter(chain=chain_obj)

        if controller:
            queryset = queryset.filter(controller=controller)
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


schema = graphene.Schema(query=Query)

