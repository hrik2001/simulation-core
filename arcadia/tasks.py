from sim_core.utils import parquet_files_to_process, update_timestamp
from .models import Borrow, AuctionStarted, AuctionFinished, Repay, AccountAssets, MetricSnapshot
from core.models import CryoLogsMetadata
from celery import shared_task
import os
from django.conf import settings
from django.db import transaction
import pandas as pd
from .utils import get_account_value, call_generate_asset_data, update_all_data, update_amounts, usdc_address, weth_address
from django.db.models import Max
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Cast

# Hex cleaner function
def hex_cleaner(param):
    if isinstance(param, bytes):
        return "0x" + str(param.hex()).lower()
    elif isinstance(param, str):
        return param.lower()

# Arcadia events ingestion tasks:
@shared_task(name="task__arcadia__borrow_events")
def task__arcadia__borrow(label: str, pool_address: str):

    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        borrow_events = []
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                borrow_event = Borrow(
                    pool_address=pool_address,
                    account=hex_cleaner(row["event__account"]),
                    by=hex_cleaner(row["event__by"]),
                    to=hex_cleaner(row["event__to"]),
                    amount=str(row["event__amount_string"]),
                    fee=int(row["event__fee_string"]),
                    referrer=hex_cleaner(row["event__referrer"]),
                    transaction_hash=hex_cleaner(row["transaction_hash"]),
                    transaction_index=row["transaction_index"],
                    log_index=row["log_index"],
                    chain=metadata.chain,
                    block_number=row["block_number"]
                )
                borrow_events.append(borrow_event)

        Borrow.objects.bulk_create(borrow_events, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()

    update_timestamp(metadata.chain, Borrow.objects.filter(timestamp=None), Borrow)

@shared_task(name="task__arcadia__auction_started_events")
def task__arcadia__auction_started(label: str, pool_address: str):

    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        auction_started_events = []
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                auction_started_event = AuctionStarted(
                    pool_address=pool_address,
                    account=hex_cleaner(row["event__account"]),
                    creditor=str(row["event__creditor"]),
                    open_debt=str(row["event__open_debt"]),
                    transaction_hash=hex_cleaner(row["transaction_hash"]),
                    transaction_index=row["transaction_index"],
                    log_index=row["log_index"],
                    chain=metadata.chain,
                    block_number=row["block_number"]
                )
                auction_started_events.append(auction_started_event)

        AuctionStarted.objects.bulk_create(auction_started_events, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()

    update_timestamp(metadata.chain, AuctionStarted.objects.filter(timestamp=None), AuctionStarted)

@shared_task(name="task__arcadia__auction_finished_events")
def task__arcadia__auction_finished(label: str, pool_address: str):
    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        auction_finished_events = []
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                auction_finished_event = AuctionFinished(
                    pool_address=pool_address,
                    account=hex_cleaner(row["event__account"]),
                    creditor=str(row["event__creditor"]),
                    start_debt=str(row["event__start_debt"]),
                    initiation_reward=str(row["event__initiation_reward"]),
                    termination_reward=str(row["event__termination_reward"]),
                    penalty=str(row["event__penalty"]),
                    bad_debt=str(row["event__bad_debt"]),
                    surplus=str(row["event__surplus"]),
                    transaction_hash=hex_cleaner(row["transaction_hash"]),
                    transaction_index=row["transaction_index"],
                    log_index=row["log_index"],
                    chain=metadata.chain,
                    block_number=row["block_number"]
                )
                auction_finished_events.append(auction_finished_event)

        AuctionFinished.objects.bulk_create(auction_finished_events, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()

    update_timestamp(metadata.chain, AuctionFinished.objects.filter(timestamp=None), AuctionFinished)

@shared_task(name="task__arcadia__repay_events")
def task__arcadia__repay(label: str, pool_address: str):
    metadata = CryoLogsMetadata.objects.get(label=label)
    files, after_ingestion = parquet_files_to_process(metadata.ingested, label)

    with transaction.atomic():
        repay_events = []
        for i in files:
            file_path = os.path.join(settings.MEDIA_ROOT, f"logs__{label}", i)
            df = pd.read_parquet(file_path)
            for index, row in df.iterrows():

                repay_event = Repay(
                    pool_address=pool_address,
                    account=hex_cleaner(row["event__account"]),
                    from_address=str(row["event__from"]),
                    amount=str(row["event__amount"]),
                    transaction_hash=hex_cleaner(row["transaction_hash"]),
                    transaction_index=row["transaction_index"],
                    log_index=row["log_index"],
                    chain=metadata.chain,
                    block_number=row["block_number"]
                )
                repay_events.append(repay_event)

        Repay.objects.bulk_create(repay_events, ignore_conflicts=True)
        metadata.ingested = after_ingestion
        metadata.save()

    update_timestamp(metadata.chain, Repay.objects.filter(timestamp=None), Repay)

@shared_task
def task__arcadia__update_account_assets():

    accounts = Borrow.objects.values_list('account', flat=True).distinct()
    with transaction.atomic():
        for account in accounts:
            try:
                asset_record = AccountAssets.objects.get(account=account)
                created = False
            except AccountAssets.DoesNotExist:
                asset_record = AccountAssets(
                    account=account
                )
                created = True
            usdc_is_zero = asset_record.usdc_value == '0' if asset_record.usdc_value else True

            latest_borrow_time = Borrow.objects.filter(account=account).aggregate(Max('created_at'))['created_at__max'] or 0
            needs_update = created or (asset_record.updated_at < latest_borrow_time)

            if usdc_is_zero:
                if needs_update:
                    update_all_data(account)
            else:
                if needs_update:
                    update_all_data(account)
                else:
                    update_amounts(account, asset_record)

@shared_task
def task__arcadia__metric_snapshot():
    # Annotate and cast debt and collateral for all accounts in a single query
    annotated_assets = AccountAssets.objects.annotate(
        debt_float=Cast('debt_usd', FloatField()),
        collateral_float=Cast('collateral_value_usd', FloatField())
    )

    # Calculate total debt and collateral
    total_aggregates = annotated_assets.aggregate(
        total_debt=Sum('debt_float'),
        total_collateral=Sum('collateral_float')
    )
    total_debt = total_aggregates['total_debt'] or 0.0
    total_collateral = total_aggregates['total_collateral'] or 0.0
    weighted_cr = (total_debt / total_collateral) if total_collateral else 0

    # Filter for USDC and WETH while aggregating
    usdc_aggregates = annotated_assets.filter(numeraire__iexact=usdc_address).aggregate(
        total_debt_usdc=Sum('debt_float'),
        total_collateral_usdc=Sum('collateral_float')
    )
    weth_aggregates = annotated_assets.filter(numeraire__iexact=weth_address).aggregate(
        total_debt_weth=Sum('debt_float'),
        total_collateral_weth=Sum('collateral_float')
    )

    # Extract sums for USDC and WETH
    total_debt_usdc = usdc_aggregates['total_debt_usdc'] or 0.0
    total_collateral_usdc = usdc_aggregates['total_collateral_usdc'] or 0.0
    weighted_cr_usdc = (total_debt_usdc / total_collateral_usdc) if total_collateral_usdc else 0

    total_debt_weth = weth_aggregates['total_debt_weth'] or 0.0
    total_collateral_weth = weth_aggregates['total_collateral_weth'] or 0.0
    weighted_cr_weth = (total_debt_weth / total_collateral_weth) if total_collateral_weth else 0

    # Create and save the metric snapshot
    MetricSnapshot.objects.create(
        weighted_cr=weighted_cr,
        weighted_cr_usdc=weighted_cr_usdc,
        weighted_cr_weth=weighted_cr_weth,
        active_auctions=0,  # Assuming you will update this if needed
        active_auctions_usd=0,  # Assuming you will update this if needed
        active_auctions_weth=0,  # Assuming you will update this if needed
        total_debt=str(total_debt),
        total_debt_usdc=str(total_debt_usdc),
        total_debt_weth=str(total_debt_weth),
        total_collateral=str(total_collateral),
        total_collateral_usdc=str(total_collateral_usdc),
        total_collateral_weth=str(total_collateral_weth),
    )
