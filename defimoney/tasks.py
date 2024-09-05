from celery import shared_task
from .utils import collateral_debt_ceilings
from .models import DebtMetadataSnapshot
from datetime import datetime

@shared_task
def task__defimoney__debt_ceiling_snapshot():
    metadata = collateral_debt_ceilings()
    timestamp = datetime.now().timestamp()
    data = DebtMetadataSnapshot(metadata=metadata, timestamp=timestamp)
    data.save()
