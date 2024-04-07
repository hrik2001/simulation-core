from typing import Optional
import os
import subprocess
from django.conf import settings
from celery import shared_task
from .models import Chain, CryoLogsMetadata
import json

def cryo_ingest_logs(
    contract_address: str,
    rpc: str,
    event_signature: str,
    label: str,
    start_block: int,
    end_block: Optional[int] = None,
    reorg_buffer: int = 1000,
    subdirs: str = "datatype"
):
    if os.path.exists(settings.MEDIA_ROOT):
        os.chdir(settings.MEDIA_ROOT)
        start_block_str = f"{int(start_block)/1e6}M"
        if end_block is None:
            end_block_str = ""
        else:
            end_block_str = f"{int(end_block)/1e6}M"
        block_str = f"{start_block_str}:{end_block_str}"
        print(f"{block_str=}")
        command = [
            'cryo', 'logs',
            '--label', label,
            '--blocks', block_str,
            '--reorg-buffer', str(reorg_buffer),
            '--rpc', str(rpc),
            '--subdirs', str(subdirs),
            '--contract', str(contract_address),
            '--event-signature', event_signature
        ]
        subprocess.run(command)
    else:
        raise Exception("Media directory doesn't exist")

@shared_task(name="task_cryo_logs")
def task_cryo_logs(
    contract_address: str,
    # rpc: str,
    chain_id: int,
    event_signature: str,
    label: str,
    start_block: int,
    end_block: Optional[int] = None,
    reorg_buffer: int = 1000,
    subdirs: str = "datatype"   
):
    chain = Chain.objects.get(chain_id=chain_id)
    cryo_ingest_logs(
        contract_address,
        chain.rpc,
        event_signature,
        label,
        start_block,
        end_block,
        reorg_buffer,
        subdirs
    )

    try:
        metadata = CryoLogsMetadata.objects.get(label=label)
    except CryoLogsMetadata.DoesNotExist:
        metadata = CryoLogsMetadata(
            label=label,
            chain=chain
        )
        metadata.save()

    os.chdir(os.path.join(settings.MEDIA_ROOT, f"logs__{label}"))
    # extracted = list(sorted(os.listdir()))[:-1]
    # extracted = json.dumps(extracted)
    # metadata.extracted = extracted
    metadata.save()
