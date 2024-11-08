from django.db.models import JSONField, TextField, ForeignKey, CASCADE, DateTimeField, Index, IntegerField

from core.models import BaseModel, Chain


class DebtCeiling(BaseModel):
    chain = ForeignKey(Chain, on_delete=CASCADE)
    controller = TextField()
    timestamp = DateTimeField()
    data = JSONField()

    class Meta(BaseModel.Meta):
        indexes = [
            Index(fields=['chain', 'controller', 'timestamp'], name='debt_ceiling_cmt_idx'),
        ]


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
    total_supply = TextField()
    price = TextField()
