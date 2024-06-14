from django.db import models

# Create your models here.
from django.utils import timezone
import uuid 

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class Chain(BaseModel):
    chain_id = models.IntegerField(null=False, unique=True)
    chain_name = models.TextField(null=False)
    rpc = models.TextField(null=False)
    explorer = models.TextField(null=True, blank=True)
    misc_info = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.chain_name

class CryoLogsMetadata(BaseModel):
    label = models.CharField(max_length=255, unique=True, db_index=True)
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)
    ingested = models.JSONField(null=True, blank=True, default=list())

class Transaction(BaseModel):
    transaction_hash = models.CharField(max_length=255, db_index=True, unique=True)
    block_number = models.IntegerField(null=False)
    timestamp = models.IntegerField(null=True)
    transaction_index = models.IntegerField(null=True)
    log_index = models.IntegerField(null=True)
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE)

    class Meta:
        abstract = True

class ERC20(BaseModel):
    chain = models.ForeignKey(Chain, on_delete=models.CASCADE, null=False)
    symbol = models.CharField(null=True, max_length=59, blank=True)
    name = models.CharField(null=True, max_length=50, blank=True)
    decimals = models.IntegerField(default=0)
    contract_address = models.CharField(null=False, max_length=50)
    pricing_metadata = models.JSONField(null=False, blank=True, default=dict())

    def __str__(self):
        return f"{self.name}-{self.chain}"

class UniswapLPPosition(ERC20):
    token0 = models.ForeignKey(ERC20, on_delete=models.CASCADE, null=True, related_name="erc_token0", blank=True)
    token1 = models.ForeignKey(ERC20, on_delete=models.CASCADE, null=True, related_name="erc_token1", blank=True)
    # large numbers hence it's charfield
    tickLower = models.CharField(max_length=50, null=True, blank=True)
    tickUpper = models.CharField(max_length=50, null=True, blank=True)
    liquidity = models.CharField(max_length=50, null=True, blank=True)
    token_id = models.CharField(max_length=50, null=True)


    def __str__(self):
        return f"{self.token0}-{self.token1}-{self.token_id}"