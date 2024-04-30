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

    def __str__(self):
        return f"Account={self.account} Debt={self.debt_usd}"