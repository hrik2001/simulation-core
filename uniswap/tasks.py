import json
import os

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.db import transaction

from core.models import CryoLogsMetadata, Transaction
from sim_core.utils import parquet_files_to_process

from .models import PairCreated


@shared_task(name="task__uniswap__pair_created")
def task__uniswap__pair_created():
    label = "uniswap_v2_pools"
    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        pairs_created = []

        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():
                pair_created = PairCreated(
                    token0="0x" + str(row["event__token0"].hex()).lower(),
                    token1="0x" + str(row["event__token1"].hex()).lower(),
                    transaction_hash="0x" + str(row["transaction_hash"].hex()).lower(),
                    transaction_index=row["transaction_index"],
                    log_index=row["log_index"],
                    chain=metadata.chain,
                    block_number=row["block_number"],
                )
                pairs_created.append(pair_created)

        PairCreated.objects.bulk_create(pairs_created, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()
