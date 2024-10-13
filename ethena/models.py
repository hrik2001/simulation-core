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

    total_usdm_supply = models.TextField(null=False, default="0")
    total_superstate_ustb_supply = models.TextField(null=False, default="0")
    total_buidl_supply = models.TextField(null=False, default="0")

    usdm_price = models.TextField(null=False, default="0")
    superstate_ustb_price = models.TextField(null=False, default="0")
    buidl_price = models.TextField(null=False, default="0")

    total_buidl_issued = models.TextField(null=False, default="0")
    total_usdm_shares = models.TextField(null=False, default="0")
    total_superstate_ustb_balance = models.TextField(null=False, default="0")

    buidl_wallet_count = models.TextField(null=False, default="0")

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=['block_timestamp'], name='block_timestamp_idx'),
        ]


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


class UniswapPoolSnapshots(BaseModel):
    timestamp = models.DateTimeField(null=False)
    address = models.TextField(null=False)
    snapshot = models.JSONField(null=False)


class CurvePoolInfo(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(null=False)
    address = models.TextField(null=False)
    info = models.JSONField(null=False)


class CurvePoolSnapshots(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)
    block_number = models.IntegerField(null=False)
    timestamp = models.DateTimeField(null=False)
    address = models.TextField(null=False)
    snapshot = models.JSONField(null=False)


class StakingMetrics(BaseModel):
    day = models.DateTimeField(unique=True, null=False)
    usde_mint = models.TextField(null=False)
    usde_burn = models.TextField(null=False)
    supply_usde = models.TextField(null=False)
    staked_usde = models.TextField(null=False)
    unstake_usde = models.TextField(null=False)
    unstake_susde = models.TextField(null=False)


class ExitQueueMetrics(BaseModel):
    withdraw_day = models.DateTimeField(null=False)
    unlock_day = models.DateTimeField(unique=True, null=False)
    usde = models.TextField(null=False)
    susde = models.TextField(null=False)
    total_usde = models.TextField(null=False)
    total_susde = models.TextField(null=False)


class ApyMetrics(BaseModel):
    timestamp = models.DateTimeField(null=False)
    pool_id = models.TextField(null=False)
    symbol = models.TextField(null=False)
    tvl_usd = models.TextField(null=True)
    apy = models.TextField(null=True)
    apy_base = models.TextField(null=True)
    apy_reward = models.TextField(null=True)
    il7d = models.TextField(null=True)
    apy_base_7d = models.TextField(null=True)

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=['pool_id', 'timestamp'], name='pool_id_timestamp_idx'),
        ]


class FundingRateMetrics(BaseModel):
    timestamp = models.DateTimeField(null=False)
    symbol = models.TextField(null=False)
    exchange = models.TextField(null=False)
    rate = models.TextField(null=False)

    class Meta(BaseModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=['timestamp', 'symbol', 'exchange'], name='timestamp_asset_cex_rate_idx'),
        ]


class UstbYieldMetrics(BaseModel):
    date = models.DateTimeField(null=False, unique=True)
    one_day = models.TextField(null=False)
    seven_day = models.TextField(null=False)
    thirty_day = models.TextField(null=False)


class BuidlYieldMetrics(BaseModel):
    date = models.DateTimeField(null=False, unique=True)
    amount = models.TextField(null=False)
    apy_7d = models.TextField(null=False)
    apy_30d = models.TextField(null=False)


class BuidlRedemptionMetrics(BaseModel):
    date = models.DateTimeField(null=False, unique=True)
    balance = models.TextField(null=False)


class UsdmMetrics(BaseModel):
    date = models.DateTimeField(null=False, unique=True)
    holders = models.TextField(null=False)
    index = models.TextField(null=False)
    apy = models.TextField(null=False)
