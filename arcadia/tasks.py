from sim_core.utils import parquet_files_to_process, update_timestamp
from .models import Borrow, AuctionStarted, AuctionFinished, Repay
from core.models import CryoLogsMetadata
from celery import shared_task
import os
from django.conf import settings
from django.db import transaction
import pandas as pd

# Arcadia events ingestion tasks:
# 1. Borrow(address indexed account, address indexed by, address to, uint256 amount, uint256 fee, bytes3 indexed referrer);
# 2. AuctionStarted(address indexed account, address indexed creditor, uint128 openDebt);
# 3. AuctionFinished(address indexed account, address indexed creditor, uint256 startDebt, uint256 initiationReward, uint256 terminationReward, uint256 penalty, uint256 badDebt, uint256 surplus);
# 4. Repay(address indexed account, address indexed from, uint256 amount);

### Labels: are used so that the task knows where the parquet files are stored.

@shared_task(name="task__arcadia__borrow_events")
def task__arcadia__borrow(label: str, pool_address:str):

    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        borrow_events = []
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                borrow_event = Borrow(
                    pool_address = pool_address,
                    account = "0x" + str(row["event__account"].hex()).lower(),
                    by = "0x" + str(row["event__by"].hex()).lower(),
                    to = "0x" + str(row["event__to"].hex()).lower(),
                    amount =  str(row["event__amount_string"]),
                    fee =  int(row["event__fee_string"]),
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
    
    update_timestamp(metadata.chain, Borrow.objects.filter(timestamp=None), Borrow)

@shared_task(name="task__arcadia__auction_started_events")
def task__arcadia__auction_started(label: str, pool_address:str):
    
        metadata = CryoLogsMetadata.objects.get(label=label)
        files, after_ingestion = parquet_files_to_process(metadata.ingested, label)
    
        with transaction.atomic():
            auction_started_events = []
            for i in files:
                file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
                df = pd.read_parquet(file_path)
                for index, row in df.iterrows():
    
                    auction_started_event = AuctionStarted(
                        pool_address = pool_address,
                        account = "0x" + str(row["event__account"].hex()).lower(),
                        creditor =  str(row["event__creditor"]),
                        open_debt =  str(row["event__open_debt"]),

                        transaction_hash = "0x" + str(row["transaction_hash"].hex()).lower(),
                        transaction_index = row["transaction_index"],
                        log_index = row["log_index"],
                        chain = metadata.chain,
                        block_number = row["block_number"]
                    )
                    auction_started_events.append(auction_started_event)
            
            AuctionStarted.objects.bulk_create(auction_started_events, ignore_conflicts=True)
            metadata.ingested = after_ingestion
            metadata.save()
    update_timestamp(metadata.chain, AuctionStarted.objects.filter(timestamp=None), AuctionStarted)

@shared_task(name="task__arcadia__auction_finished_events")
def task__arcadia__auction_finished(label: str, pool_address:str):
            metadata = CryoLogsMetadata.objects.get(label=label)
            files, after_ingestion = parquet_files_to_process(metadata.ingested, label)
        
            with transaction.atomic():
                auction_finished_events = []
                for i in files:
                    file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
                    df = pd.read_parquet(file_path)
                    for index, row in df.iterrows():
        
                        auction_finished_event = AuctionFinished(
                            pool_address = pool_address,
                            account = "0x" + str(row["event__account"].hex()).lower(),
                            creditor =  str(row["event__creditor"]),
                            start_debt =  str(row["event__start_debt"]),
                            initiation_reward =  str(row["event__initiation_reward"]),
                            termination_reward =  str(row["event__termination_reward"]),
                            penalty =  str(row["event__penalty"]),
                            bad_debt =  str(row["event__bad_debt"]),
                            surplus =  str(row["event__surplus"]),
                            
                            transaction_hash = "0x" + str(row["transaction_hash"].hex()).lower(),
                            transaction_index = row["transaction_index"],
                            log_index = row["log_index"],
                            chain = metadata.chain,
                            block_number = row["block_number"]
                        )
                        auction_finished_events.append(auction_finished_event)
                
                AuctionFinished.objects.bulk_create(auction_finished_events, ignore_conflicts=True)
                metadata.ingested = after_ingestion
                metadata.save()
    update_timestamp(metadata.chain, AuctionFinished.objects.filter(timestamp=None), AuctionFinished)

@shared_task(name="task__arcadia__repay_events")
def task__arcadia__repay(label: str, pool_address:str):
            metadata = CryoLogsMetadata.objects.get(label=label)
            files, after_ingestion = parquet_files_to_process(metadata.ingested, label)
        
            with transaction.atomic():
                repay_events = []
                for i in files:
                    file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
                    df = pd.read_parquet(file_path)
                    for index, row in df.iterrows():
        
                        repay_event = Repay(
                            pool_address = pool_address,
                            account = "0x" + str(row["event__account"].hex()).lower(),
                            from_address =  str(row["event__from"]),
                            amount =  str(row["event__amount"]),
                            
                            transaction_hash = "0x" + str(row["transaction_hash"].hex()).lower(),
                            transaction_index = row["transaction_index"],
                            log_index = row["log_index"],
                            chain = metadata.chain,
                            block_number = row["block_number"]
                        )
                        repay_events.append(repay_event)
                
                Repay.objects.bulk_create(repay_events, ignore_conflicts=True)
                metadata.ingested = after_ingestion
                metadata.save()
    update_timestamp(metadata.chain, Repay.objects.filter(timestamp=None), Repay)
 