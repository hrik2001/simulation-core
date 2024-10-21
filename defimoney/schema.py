from datetime import datetime

import graphene
from graphene import UUID, Int, ObjectType, String

from .models import DebtMetadataSnapshot
from .types import defimoney__debt_metadata_snapshot


class Query(ObjectType):
    all_debt_snapshot = graphene.List(
        defimoney__debt_metadata_snapshot, limit=Int(), sort_by=String()
    )

    def resolve_all_debt_snapshot(
        self,
        info,
        pool_address=None,
        account=None,
        by=None,
        to=None,
        limit=None,
        sort_by=None,
    ):
        queryset = DebtMetadataSnapshot.objects.all()
        if sort_by:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by("timestamp")
        if limit:
            queryset = queryset[:limit]
        return queryset


schema = graphene.Schema(query=Query)
