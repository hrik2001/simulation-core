from django.db import models
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
    tickLower = models.CharField(max_length=50, null=True, blank=True)  # large numbers hence it's CharField
    tickUpper = models.CharField(max_length=50, null=True, blank=True)
    liquidity = models.CharField(max_length=50, null=True, blank=True)
    token_id = models.CharField(max_length=50, null=True)

    def __str__(self):
        return f"{self.token0}-{self.token1}-{self.token_id}"

class DexQuotePair(BaseModel):
    src_asset = models.ForeignKey(ERC20, on_delete=models.CASCADE, related_name="src_asset_pairs")
    dst_asset = models.ForeignKey(ERC20, on_delete=models.CASCADE, related_name="dst_asset_pairs")
    ingest = models.BooleanField(default=True)

    class Meta:
        unique_together = ('src_asset', 'dst_asset')

    def __str__(self):
        status = "[Active]" if self.ingest else "[Inactive]"
        return f"Pair: {self.src_asset.symbol} -> {self.dst_asset.symbol} {status}"

class DexQuote(BaseModel):
    network = models.IntegerField()
    dex_aggregator = models.CharField(max_length=50)
    src = models.CharField(max_length=42)  # Ethereum addresses
    src_decimals = models.IntegerField()
    dst = models.CharField(max_length=42)  # Ethereum addresses
    dest_decimals = models.IntegerField()
    in_amount_usd = models.FloatField()
    in_amount = models.TextField()  # Storing large fixed-point number as text
    out_amount = models.TextField()  # Storing large fixed-point number as text
    market_price = models.FloatField()
    price = models.FloatField()
    price_impact = models.FloatField()
    timestamp = models.IntegerField()
    pair = models.ForeignKey(DexQuotePair, on_delete=models.CASCADE, null=True, blank=True)

    class Meta(BaseModel.Meta):
        indexes = [
            models.Index(fields=['src', 'dst'], name='src_dst_idx'),
            models.Index(fields=['src'], name='src_idx'),
            models.Index(fields=['dst'], name='dst_idx'),
        ]

    def __str__(self):
        return f"{self.dex_aggregator} quote on network {self.network}"
