import json
import os
from django.conf import settings
from django.db import models
from core.models import Transaction, Chain
from typing import List
from web3 import Web3

def parquet_files_to_process(ingested, label):
    result = []
    if isinstance(ingested, str):
        ingested = json.loads(ingested)
    
    os.chdir(os.path.join(settings.MEDIA_ROOT, f"logs__{label}"))
    if not isinstance(ingested, list):
        raise Exception("ingested should be a list")
    try:
        result.append(sorted(ingested)[-1])
    except IndexError:
        pass

    for i in os.listdir():
        if i not in ingested:
            result.append(i)
    after_ingestion = list(set(result + ingested))
    return result, after_ingestion

def update_timestamp(chain: Chain, entries: List[Transaction], model: models.Model):
    w3 = Web3(Web3.HTTPProvider(chain.rpc))
    new_entries = []
    for entry in entries:
        block = w3.eth.get_block(int(entry.block_number))
        entry.timestamp = block.timestamp
        new_entries.append(entry)
    model.objects.bulk_update(new_entries, fields=["timestamp"])