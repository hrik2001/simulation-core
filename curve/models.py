from django.db.models import JSONField, TextField, ForeignKey, CASCADE, DateTimeField, Index

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
