from graphene_django.types import DjangoObjectType

from .models import DebtMetadataSnapshot


class defimoney__debt_metadata_snapshot(DjangoObjectType):
    class Meta:
        model = DebtMetadataSnapshot
        fields = "__all__"
