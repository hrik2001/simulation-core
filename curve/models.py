from django.db.models import JSONField, TextField, ForeignKey, CASCADE, DateTimeField, Index, IntegerField, \
    UniqueConstraint, DateField, Model

from core.models import BaseModel, Chain


class Top5Debt(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    timestamp = DateTimeField()
    top5_debt = TextField(default="0")

    class Meta(BaseModel.Meta):
        indexes = [
            Index(fields=['chain', 'controller', 'timestamp'], name='top5debt_cmt_idx'),
        ]


class CurveUserData(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    data = JSONField()


class ControllerMetadata(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    block_number = IntegerField()

    amm = TextField()
    monetary_policy = TextField()
    A = TextField()
    amm_price = TextField()
    oracle_price = TextField()

    class Meta(BaseModel.Meta):
        indexes = [
            Index(fields=['chain', 'controller', 'created_at'], name='controller_cmt_idx'),
        ]


class CurveMetrics(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    block_number = IntegerField()
    circulating_supply = TextField()
    price = TextField()


class CurveMarketSnapshot(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    timestamp = DateTimeField(null=True)
    data = JSONField()

    class Meta(BaseModel.Meta):
        constraints = [
            UniqueConstraint(fields=['chain', 'controller', 'timestamp'], name='snapshot_asset_chain_day_idx'),
        ]


class CurveLlammaTrades(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    day = DateField()
    sold = TextField()
    bought = TextField()
    fee_x = TextField()
    fee_y = TextField()

    class Meta(BaseModel.Meta):
        constraints = [
            UniqueConstraint(fields=['chain', 'controller', 'day'], name='llamma_trades_asset_chain_day_idx'),
        ]


class CurveLlammaEvents(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    day = DateField()
    deposit = TextField()
    withdrawal = TextField()

    class Meta(BaseModel.Meta):
        constraints = [
            UniqueConstraint(fields=['chain', 'controller', 'day'], name='llamma_events_asset_chain_day_idx'),
        ]


class CurveCr(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    mean = TextField()
    median = TextField()


class CurveMarkets(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    markets = JSONField()
    system_cr = TextField()


class CurveMarketSoftLiquidations(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    timestamp = DateTimeField(null=True)
    data = JSONField()

    class Meta(BaseModel.Meta):
        constraints = [
            UniqueConstraint(fields=['chain', 'controller', 'timestamp'], name='soft_liquidation_asset_chain_ts_idx'),
        ]


class CurveMarketLosses(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    timestamp = DateTimeField(null=True)
    data = JSONField()

    class Meta(BaseModel.Meta):
        constraints = [
            UniqueConstraint(fields=['chain', 'controller', 'timestamp'], name='losses_asset_chain_ts_idx'),
        ]


class CurveScores(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()

    relative_cr_score = TextField()
    absolute_cr_score = TextField()
    aggregate_cr_score = TextField()
    bad_debt_score = TextField()
    prob_drop1_score = TextField()
    prob_drop2_score = TextField()
    aggregate_prob_drop_score = TextField()
    collateral_under_sl_score = TextField()
    relative_collateral_under_sl_score = TextField()
    aggregate_collateral_under_sl_score = TextField()
    vol_ratio_score = TextField()
    beta_score = TextField()
    aggregate_vol_ratio_score = TextField()
    relative_borrower_distribution_score = TextField(default="0")
    benchmark_borrower_distribution_score = TextField(default="0")
    aggregate_borrower_distribution_score = TextField(default="0")
    debt_ceiling_score = TextField(default="0")
    sl_responsiveness_score = TextField(default="0")
    interdependency_volatility_score = TextField(default="0")
    interdependency_price_momentum_score = TextField(default="0")
    weighted_average_score = TextField(default="0")


class CurveScoresDetail(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    
    # CR (Collateral Ratio) details
    cr_ratio = TextField(default="0")
    cr_ratio_7d = TextField(default="0")
    cr_ratio_30d = TextField(default="0")
    cr_7d_30d_ratio = TextField(default="0")
    min_ltv = TextField(default="0")
    max_ltv = TextField(default="0")
    
    # HHI (Borrower Distribution) details
    hhi = TextField(default="0")
    hhi_ideal = TextField(default="0")
    hhi_ratio = TextField(default="0")
    hhi_7d = TextField(default="0")
    hhi_30d = TextField(default="0")
    hhi_7d_30d_ratio = TextField(default="0")
    
    # Price drop probabilities
    prob_drop1 = TextField(default="0")  # 7.5% drop probability
    prob_drop2 = TextField(default="0")  # 15% drop probability
    
    # Soft liquidation details
    debt_under_sl_ratio = TextField(default="0")
    debt_under_sl_ratio_7d = TextField(default="0")
    debt_under_sl_ratio_30d = TextField(default="0")
    collateral_under_sl_ratio = TextField(default="0")
    collateral_under_sl_ratio_7d = TextField(default="0")
    collateral_under_sl_ratio_30d = TextField(default="0")
    
    # Volatility details
    volatility_45d = TextField(default="0")
    volatility_180d = TextField(default="0")
    volatility_ratio = TextField(default="0")
    beta = TextField(default="0")
    
    # Market details
    total_debt = TextField(default="0")
    borrowable = TextField(default="0")
    bad_debt = TextField(default="0")
    recommended_debt_ceiling = TextField(default="0")

    # SL Score
    sl_spread_analysis_score = TextField(default="0")
    sl_peak_analysis_score = TextField(default="0")
    

class CurveDebtCeilingScore(Model):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    created_at = DateTimeField()
    debt_ceiling_score = TextField()


class Simuliq(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    buy_token = TextField()
    sell_token = TextField()
    exchange_price = TextField()
    k = TextField()
    c = TextField()


class AaveUserData(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    data = JSONField()
