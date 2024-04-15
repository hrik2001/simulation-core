from django.db import models
from core.models import Transaction

# Borrow (index_topic_1 address account, index_topic_2 address by, address to, uint256 amount, uint256 fee, index_topic_3 bytes3 referrer)
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


