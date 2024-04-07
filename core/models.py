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

    class Meta:
        abstract = True