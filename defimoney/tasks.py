from datetime import datetime

from celery import shared_task

from .models import DebtMetadataSnapshot
from .utils import collateral_debt_ceilings


@shared_task
def task__defimoney__debt_ceiling_snapshot():
    metadata = collateral_debt_ceilings()
    timestamp = datetime.now().timestamp()
    data = DebtMetadataSnapshot(metadata=metadata, timestamp=timestamp)
    data.save()
