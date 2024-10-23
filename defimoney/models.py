from django.db import models
from core.models import BaseModel
from datetime import datetime

class DebtMetadataSnapshot(BaseModel):
    metadata = models.JSONField()
    timestamp = models.IntegerField()

    def __str__(self):
        return f'DebtMetadataSnapshot {datetime.fromtimestamp(self.timestamp)}'
