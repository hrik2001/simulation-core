from django.db import models
from core.models import Transaction, BaseModel

class Borrow(Transaction):
    pool_address = models.TextField(null=False)
    account = models.TextField(null=False)
    by = models.TextField(null=False)
    to = models.TextField(null=False)
    amount = models.TextField(null=False)
    fee = models.BigIntegerField(null=False)
    referrer = models.TextField(null=False)

    def __str__(self):
        return f"{self.account=} {self.by=} {self.to=} {self.amount=} {self.fee=} {self.referrer=}"

class AuctionStarted(Transaction):
    pool_address = models.TextField(null=False)
    account = models.TextField(null=False)
    creditor = models.TextField(null=False)
    open_debt = models.TextField(null=False)

class AuctionFinished(Transaction):
    pool_address = models.TextField(null=False)
    account = models.TextField(null=False)
    creditor = models.TextField(null=False)
    start_debt = models.TextField(null=False)
    initiation_reward = models.TextField(null=False)
    termination_reward = models.TextField(null=False)
    penalty = models.TextField(null=False)
    bad_debt = models.TextField(null=False)
    surplus = models.TextField(null=False)

class Repay(Transaction):
    pool_address = models.TextField(null=False)
    account = models.TextField(null=False)
    from_address = models.TextField(null=False)
    amount = models.TextField(null=False)

class AccountAssets(BaseModel):
    account = models.TextField(unique=True)
    numeraire = models.TextField()
    debt_usd = models.TextField()
    usdc_value = models.TextField()
    weth_value = models.TextField()
    collateral_value = models.TextField()
    collateral_value_usd = models.TextField()
    asset_details = models.JSONField()
    asset_details_usd = models.JSONField()
    liquidation_value = models.TextField(null=True)
    used_margin = models.TextField(null=True)
    healthy = models.BooleanField(null=True)

    def __str__(self):
        return f"Account={self.account} Debt={self.debt_usd} Collateral={self.collateral_value_usd}"

class MetricSnapshot(BaseModel):
    weighted_cr = models.FloatField()
    weighted_cr_usdc = models.FloatField()
    weighted_cr_weth = models.FloatField()
    active_auctions = models.IntegerField()
    active_auctions_usd = models.IntegerField()
    active_auctions_weth = models.IntegerField()
    total_debt = models.TextField()
    total_debt_usdc = models.TextField()
    total_debt_weth = models.TextField()
    total_collateral = models.TextField()
    total_collateral_usdc = models.TextField()
    total_collateral_weth = models.TextField()
    collateral_distribution = models.JSONField(null=True)
    total_supply_weth = models.DecimalField(max_digits=30, decimal_places=5, null=True)
    total_supply_usdc = models.DecimalField(max_digits=30, decimal_places=5, null=True)

    def __str__(self):
        return f"Snapshot @ {self.created_at}"

class SimSnapshot(BaseModel):
    sim_id = models.TextField(unique=True)
    prices = models.JSONField()
    timestamp = models.IntegerField()
    total_non_liquidated_accounts = models.IntegerField()
    total_active_auctions = models.IntegerField()
    total_fully_liquidated_accounts = models.IntegerField()
    total_outstanding_debt = models.TextField()
    bad_debt_per_asset = models.JSONField()
    total_exposure_per_asset = models.JSONField()
    total_insolvent_value = models.TextField()
    total_protocol_revenue = models.TextField()
    position_weighted_collateral_ratio = models.TextField()
    protocol_revenue_per_asset = models.JSONField()
    start_timestamp = models.IntegerField()
    end_timestamp = models.IntegerField()
    pool_address = models.TextField()
    numeraire = models.TextField()
    liquidation_factors = models.JSONField()
    description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'sim_snapshot'
        indexes = [
            models.Index(fields=['sim_id']),
        ]

    def __str__(self):
        return f'SimSnapshot {self.sim_id}'

class OracleSnapshot(BaseModel):
    # Both are JSON fields and not hardcoded assets so that we can index new assets
    # That arcadia might add
    spot_prices = models.JSONField(null=False)
    chainlink_prices = models.JSONField(null=False)
    missed_assets = models.JSONField(null=True)
