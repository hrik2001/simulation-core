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

    total_dai_supply = models.TextField(null=False, default="0")
    sdai_price = models.TextField(null=False, default="0")
    total_sdai_supply = models.TextField(null=False, default="0")
    dsr_rate = models.TextField(null=False, default="0")
    total_dai_staked = models.TextField(null=False, default="0")

    usdt_balance = models.TextField(null=False, default="0")

    usdt_price = models.TextField(null=False, default="0")
    dai_price = models.TextField(null=False, default="0")



class CollateralMetrics(BaseModel):
    collateral = models.JSONField(null=False)


class ReserveFundMetrics(BaseModel):
    timestamp = models.DateTimeField(null=False)
    value = models.TextField(null=False)


class ReserveFundBreakdown(BaseModel):
    tokens = models.JSONField(null=False)
    positions = models.JSONField(null=False)

    tokens_usd_value = models.TextField(null=False)
    positions_usd_value = models.TextField(null=False)
    total_usd_value = models.TextField(null=False)


class UniswapPoolMetrics(BaseModel):
    metrics = models.JSONField(null=False)


class CurvePoolMetrics(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)
    metrics = models.JSONField(null=False)


class CurvePoolSnapshots(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)
    block_number = models.IntegerField(null=False)
    timestamp = models.DateTimeField(null=False)
    address = models.TextField(null=False, default="")
    snapshot = models.JSONField(null=False)
