from django.db import models

from core.models import BaseModel, Chain


class ChainMetrics(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)

    block_number = models.IntegerField(null=False)
    block_hash = models.TextField(null=False)
    block_timestamp = models.DateTimeField(null=False)

    total_usde_supply = models.TextField(null=False)
    total_usde_staked = models.TextField(null=False)
    total_susde_supply = models.TextField(null=False)

    usde_price = models.TextField(null=False)
    susde_price = models.TextField(null=False)


class CollateralMetrics(BaseModel):
    collateral = models.JSONField(null=False)


class ReserveFundMetrics(BaseModel):
    timestamp = models.DateTimeField(null=False)
    value = models.TextField(null=False)
