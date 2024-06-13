from typing import Optional, Dict
from web3 import Web3
from sim_core.utils import parquet_files_to_process, update_timestamp
from .models import Borrow, AuctionStarted, AuctionFinished, Repay, AccountAssets, MetricSnapshot, SimSnapshot
from core.models import CryoLogsMetadata, ERC20, UniswapLPPosition
from core.utils import get_or_create_erc20, get_or_create_uniswap_lp
from celery import shared_task
import os
from django.conf import settings
from django.db import transaction
import pandas as pd
from .utils import get_account_value, call_generate_asset_data, update_all_data, update_amounts, usdc_address, weth_address, erc20_to_pydantic
from django.db.models import Sum, F, FloatField, Q, Max
from django.db.models.functions import Cast
from .arcadiasim.models.arcadia import (
    LiquidationConfig,
    LendingPoolLiquidationConfig,
    MarginAccount,
    AssetsInMarginAccount,
    AssetMetadata,
    AssetValueAndRiskFactors,
)
from .arcadiasim.models.asset import Asset
from .arcadiasim.pipeline.pipeline import Pipeline
from .arcadiasim.models.time import SimulationTime
from .arcadiasim.arcadia.liquidation_engine import LiquidationEngine
from .arcadiasim.arcadia.liquidator import Liquidator
from .arcadiasim.pipeline.utils import create_market_price_feed
from .arcadiasim.utils import get_mongodb_db
from .utils import chain_to_pydantic, get_risk_factors
from uuid import uuid4
# from .arcadiasim.entities.asset import weth

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

def sim(
        start_timestamp,
        end_timestamp,
        numeraire_address,
        pool_address,
    ):

    pool_address = Web3.to_checksum_address(pool_address)

    account_assets = AccountAssets.objects.filter(
        ~Q(debt_usd=0),
        numeraire__iexact=numeraire_address,
    )
    numeraire = ERC20.objects.get(contract_address__iexact=numeraire_address)
    base = numeraire.chain
    w3 = Web3(Web3.HTTPProvider(base.rpc))
    numeraire = erc20_to_pydantic(numeraire)

    sim_accounts = []
    all_erc20_assets = dict()
    all_lp_assets = list()
    liquidation_factors_dict = dict()
    for account in account_assets:
        price_weth = (int(account.weth_value) / 1e18) / (int(account.usdc_value) / 1e6)
        debt_amount_numeraire = price_weth * float(account.debt_usd) * 1e18
        debt_amount_numeraire = int(debt_amount_numeraire)
        if debt_amount_numeraire == 0:
            continue
        sim_account = MarginAccount(
            address=account.account,
            debt=debt_amount_numeraire,
            numeraire=numeraire,
            assets=[],
        )
        include_account = True
        for index, value in enumerate(account.asset_details[1]):
            # here value above is asset ID, if it's 0 then it's an ERC20
            if not value:
                # case when it's an ERC20 Asset
                asset = get_or_create_erc20(account.asset_details[0][index], base)
                asset = erc20_to_pydantic(asset)
                # asset = Asset(**asset)
                if asset.contract_address.lower() in all_erc20_assets:
                    asset = all_erc20_assets[asset.contract_address.lower()]
                else:
                    all_erc20_assets[asset.contract_address.lower()] = asset
                amount = account.asset_details[2][index]
                if asset.contract_address.lower() not in liquidation_factors_dict:
                    _, liquidation_factors = get_risk_factors(w3, pool_address, [asset.contract_address], [0])
                    liquidation_factor = liquidation_factors[0]/1e4
                    liquidation_factors_dict[asset.contract_address.lower()] = liquidation_factor
                else:
                    liquidation_factor = liquidation_factors_dict[asset.contract_address.lower()]
                asset_in_margin_account = AssetsInMarginAccount(
                    asset=asset,
                    metadata=AssetMetadata(
                        amount=amount,
                        current_amount=amount,
                        risk_metadata=AssetValueAndRiskFactors(
                            collateral_factor=0,
                            liquidation_factor = 0.5,
                            # liquidation_factor=liquidation_factor,
                            exposure=0,
                        ),
                    ),
                )
            else:
                asset = get_or_create_uniswap_lp(account.asset_details[0][index], base, account.asset_details[1][index])
                asset = erc20_to_pydantic(asset)
                if asset.contract_address.lower() not in liquidation_factors_dict:
                    _, liquidation_factors = get_risk_factors(w3, pool_address, [asset.contract_address], [int(asset.token_id)])
                    liquidation_factor = liquidation_factors[0]/1e4
                    liquidation_factors_dict[asset.contract_address.lower()] = liquidation_factor
                else:
                    liquidation_factor = liquidation_factors_dict[asset.contract_address.lower()]
                liquidation_factor = liquidation_factors[0]/1e4
                asset_in_margin_account = AssetsInMarginAccount(
                    asset=asset,
                    metadata=AssetMetadata(
                        amount=1,
                        current_amount=1,
                        risk_metadata=AssetValueAndRiskFactors(
                            collateral_factor=0,
                            liquidation_factor = 0.5,
                            # liquidation_factor=liquidation_factor,
                            exposure=0,
                        ),
                    ),
                )
                if int(asset.liquidity) == 0:
                    include_account = False
                    break
                all_lp_assets.append(asset)
            sim_account.assets.append(asset_in_margin_account)
        if include_account:
            # filter accounts for which we can price uniswap lp positions
            sim_accounts.append(sim_account)
    assets = list(all_erc20_assets.values()) + all_lp_assets
    pydantic_base = chain_to_pydantic(base)
    prices = create_market_price_feed(assets, numeraire, pydantic_base, start_timestamp, end_timestamp)

    sim_time = SimulationTime(
        timestamp=start_timestamp,
        prices=prices,
        chain=pydantic_base,
    )
    pool_config = LendingPoolLiquidationConfig(
        max_initiation_fee=1,
        max_termination_fee=1,
        initiation_weight=1,
        termination_weight=1,
        penalty_weight=1,
    )

    liquidation_config = LiquidationConfig(
        base=999_807_477_651_317_446,
        maximum_auction_duration=14_400,
        start_price_multiplier=15_000,
        min_price_multiplier=6000,
        lending_pool=pool_config,
    )

    liquidation_engine = LiquidationEngine(
        liquidation_config=liquidation_config,
        simulation_time=sim_time,
        auction_information={},
    )
    liquidator = Liquidator(
        liquidation_engine=liquidation_engine,
        balance=5000,  # balance in terms of USDT (numeraire)
        sim_time=sim_time,
        liquidator_address= "0xLiquidator"
    )

    unique_id = uuid4()
    pipeline = Pipeline(
        simulation_time=sim_time,
        liquidation_engine=liquidation_engine,
        liquidators=[liquidator],
        accounts=sim_accounts,
        numeraire=numeraire,
        orchestrator_id=unique_id,
        pipeline_id=unique_id
    )

    pipeline.event_loop()
    db = get_mongodb_db()
    print(f"{unique_id=}")
    cumulative_metric = db.METRICS.find_one({"orchestrator_id": str(unique_id)}, sort=[("data.timestamp", -1)])
    result_metric = {
        **cumulative_metric["data"],
        "sim_id": unique_id,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "pool_address": pool_address,
        "numeraire": numeraire.contract_address,
        "liquidation_factors": liquidation_factors_dict,
    }
    sim_snapshot = SimSnapshot(**result_metric)
    sim_snapshot.save()
    return str(unique_id)

def test_sim():
    start_timestamp = 1716805523
    end_timestamp = 1716891923
    numeraire_address = "0x4200000000000000000000000000000000000006"
    pool_address = "0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2"
    return sim(start_timestamp, end_timestamp, numeraire_address, pool_address)