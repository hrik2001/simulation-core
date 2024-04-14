from sim_core.utils import parquet_files_to_process
from .models import Borrow
from core.models import CryoLogsMetadata
from celery import shared_task
# import json
import os
from django.conf import settings
from django.db import transaction
import pandas as pd

@shared_task(name="task__arcadia__borrow_events")
def task__arcadia__borrow():
    label = "arcadia_borrow"
    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        borrow_events = []
        
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                borrow_event = Borrow(
                    account = "0x" + str(row["event__account"].hex()).lower(),
                    by = "0x" + str(row["event__by"].hex()).lower(),
                    to = "0x" + str(row["event__to"].hex()).lower(),
                    amount =  str(row["event__amount"]),
                    fee =  int(row["event__fee"]),
                    referrer = "0x" + str(row["event__referrer"].hex()).lower(),

                    transaction_hash = "0x" + str(row["transaction_hash"].hex()).lower(),
                    transaction_index = row["transaction_index"],
                    log_index = row["log_index"],
                    chain = metadata.chain,
                    block_number = row["block_number"]
                )
                borrow_events.append(borrow_event)
        
        Borrow.objects.bulk_create(borrow_events, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()