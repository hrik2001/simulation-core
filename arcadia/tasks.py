from typing import Optional, Dict
from web3 import Web3
from sim_core.utils import parquet_files_to_process, update_timestamp
from .models import Borrow, AuctionStarted, AuctionFinished, Repay, AccountAssets, MetricSnapshot, SimSnapshot, OracleSnapshot
from core.models import CryoLogsMetadata, ERC20, UniswapLPPosition, Chain
from core.utils import get_or_create_erc20, get_or_create_uniswap_lp, get_oracle_lastround_price, price_defillama
from celery import shared_task
import os
from django.conf import settings
from django.db import transaction
import pandas as pd
from .utils import get_account_value, call_generate_asset_data, update_all_data, update_amounts, usdc_address, \
    weth_address, erc20_to_pydantic, get_total_supply, get_total_liquidity, usdc_lending_pool_address, weth_lending_pool_address
from django.db.models import Sum, F, FloatField, Q, Max, JSONField, Func
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
from collections import defaultdict
from datetime import datetime
from django.core.cache import cache

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
                    open_debt=str(row["event__openDebt_string"]),
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

            latest_borrow_time = Borrow.objects.filter(account=account).aggregate(Max('created_at'))[
                                     'created_at__max'] or 0
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
def task__arcadia__create_assets():# code for asset entries
    account_assets = AccountAssets.objects.filter(
        ~Q(debt_usd=0),
    )
    for asset_record in account_assets:
        base = Chain.objects.get(chain_id=8453)
        for index, value in enumerate(asset_record.asset_details[1]):
            # here value above is asset ID, if it's 0 then it's an ERC20
            if not value:
                # case when it's an ERC20 Asset
                asset = get_or_create_erc20(asset_record.asset_details[0][index], base)
            else:
                asset = get_or_create_uniswap_lp(asset_record.asset_details[0][index], base, asset_record.asset_details[1][index])

@shared_task
def task__arcadia__metric_snapshot():
    # Annotate and cast debt and collateral for all accounts in a single query
    annotated_assets = AccountAssets.objects.annotate(
        debt_float=Cast('debt_usd', FloatField()),
        collateral_float=Cast('collateral_value_usd', FloatField()),
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

    total_supply_weth = get_total_supply(weth_lending_pool_address)/1e18
    total_supply_usdc = get_total_supply(usdc_lending_pool_address)/1e6
    
    total_liquidity_weth = get_total_liquidity(weth_lending_pool_address)/1e18
    total_liquidity_usdc = get_total_liquidity(usdc_lending_pool_address)/1e6
    
    # Extract sums for USDC and WETH
    total_debt_usdc = usdc_aggregates['total_debt_usdc'] or 0.0
    total_collateral_usdc = usdc_aggregates['total_collateral_usdc'] or 0.0
    weighted_cr_usdc = (total_debt_usdc / total_collateral_usdc) if total_collateral_usdc else 0

    total_debt_weth = weth_aggregates['total_debt_weth'] or 0.0
    total_collateral_weth = weth_aggregates['total_collateral_weth'] or 0.0
    weighted_cr_weth = (total_debt_weth / total_collateral_weth) if total_collateral_weth else 0

    borrowers = AccountAssets.objects.filter(~Q(debt_usd=0))


    collateral_distribution = defaultdict(float)

    for account in borrowers:
        if account.asset_details_usd:
            for asset, value in account.asset_details_usd.items():
                collateral_distribution[asset] += value
            
    collateral_distribution2 = defaultdict(float)

    for account in borrowers:
        if account.position_distribution_usd:
            for asset, value in account.position_distribution_usd.items():
                collateral_distribution2[asset] += value

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
        collateral_distribution=collateral_distribution,
        collateral_distribution2=collateral_distribution2,
        total_supply_usdc=total_supply_usdc,
        total_supply_weth=total_supply_weth,
        total_liquidity_usdc=total_liquidity_usdc,
        total_liquidity_weth=total_liquidity_weth,
    )


def sim(
        start_timestamp,
        end_timestamp,
        numeraire_address,
        pool_address,
        description=None
):
    pool_address = Web3.to_checksum_address(pool_address)

    account_assets = AccountAssets.objects.filter(
        ~Q(debt_usd=0),
        numeraire__iexact=numeraire_address,
    )
    numeraire = ERC20.objects.get(contract_address__iexact=numeraire_address, chain__chain_name__iexact="base")
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
                    liquidation_factor = liquidation_factors[0] / 1e4
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
                            # liquidation_factor = 0.5,
                            liquidation_factor=liquidation_factor,
                            exposure=0,
                        ),
                    ),
                )
            else:
                asset = get_or_create_uniswap_lp(account.asset_details[0][index], base, account.asset_details[1][index])
                if asset is None:
                    include_account = False
                    break
                asset = erc20_to_pydantic(asset)
                if asset.contract_address.lower() not in liquidation_factors_dict:
                    _, liquidation_factors = get_risk_factors(w3, pool_address, [asset.contract_address],
                                                              [int(asset.token_id)])
                    liquidation_factor = liquidation_factors[0] / 1e4
                    liquidation_factors_dict[asset.contract_address.lower()] = liquidation_factor
                else:
                    liquidation_factor = liquidation_factors_dict[asset.contract_address.lower()]
                liquidation_factor = liquidation_factors[0] / 1e4
                asset_in_margin_account = AssetsInMarginAccount(
                    asset=asset,
                    metadata=AssetMetadata(
                        amount=1,
                        current_amount=1,
                        risk_metadata=AssetValueAndRiskFactors(
                            collateral_factor=0,
                            # liquidation_factor = 0.5,
                            liquidation_factor=liquidation_factor,
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
        liquidator_address="0xLiquidator"
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
        "description": description
    }
    result_metric["total_outstanding_debt"] = result_metric["total_outstanding_debt"] / (10 ** (numeraire.decimals))

    sim_snapshot = SimSnapshot(**result_metric)
    sim_snapshot.save()

    # Delete data from MongoDB
    db.PARAMS.delete_many({"orchestrator_id": str(unique_id)})
    db.ACCOUNTS.delete_many({"orchestrator_id": str(unique_id)})
    db.BID.delete_many({"orchestrator_id": str(unique_id)})
    db.STATE.delete_many({"orchestrator_id": str(unique_id)})
    db.METRICS.delete_many({"orchestrator_id": str(unique_id)})
    return str(unique_id)


# def test_sim():
# start_timestamp = 1716805523
# end_timestamp = 1716891923
# numeraire_address = "0x4200000000000000000000000000000000000006"
# pool_address = "0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2"
# return sim(start_timestamp, end_timestamp, numeraire_address, pool_address)

@shared_task
def task__arcadia__sim(
        start_timestamp: int,
        end_timestamp: int,
        numeraire_address: str,
        pool_address: str,
        description=None
):
    return sim(start_timestamp, end_timestamp, numeraire_address, pool_address, description)

def get_pool_risk_params(
        pool_address: str,
        numeraire_address: str
    ):

    pool_address = Web3.to_checksum_address(pool_address)
    numeraire_address = Web3.to_checksum_address(numeraire_address)
    account_assets = AccountAssets.objects.filter(
        ~Q(debt_usd=0),
        numeraire__iexact=numeraire_address,
    )

    numeraire = ERC20.objects.get(contract_address__iexact=numeraire_address, chain__chain_name__iexact="base")
    base = numeraire.chain
    w3 = Web3(Web3.HTTPProvider(base.rpc))
    numeraire = erc20_to_pydantic(numeraire)

    liquidation_factors_dict = dict()
    collateral_factors_dict = dict()

    all_erc20_assets = dict()

    for account in account_assets:
         for index, value in enumerate(account.asset_details[1]):
            if not value:
                asset = get_or_create_erc20(account.asset_details[0][index], base)
                asset = erc20_to_pydantic(asset)
                if asset.contract_address.lower() in all_erc20_assets:
                    asset = all_erc20_assets[asset.contract_address.lower()]
                else:
                    all_erc20_assets[asset.contract_address.lower()] = asset
                if asset.contract_address.lower() not in liquidation_factors_dict:
                    collateral_factors, liquidation_factors = get_risk_factors(w3, pool_address, [asset.contract_address], [0])
                    liquidation_factor = liquidation_factors[0] / 1e4
                    collateral_factor = collateral_factors[0] / 1e4
                    liquidation_factors_dict[asset.contract_address.lower()] = liquidation_factor
                    collateral_factors_dict[asset.contract_address.lower()] = collateral_factor
                else:
                    liquidation_factor = liquidation_factors_dict[asset.contract_address.lower()]
                    collateral_factor = collateral_factors_dict[asset.contract_address.lower()]
            else:
                asset = get_or_create_uniswap_lp(account.asset_details[0][index], base, account.asset_details[1][index])
                if asset is None:
                    break
                asset = erc20_to_pydantic(asset)
                if asset.contract_address.lower() not in liquidation_factors_dict:
                    collateral_factors, liquidation_factors = get_risk_factors(w3, pool_address, [asset.contract_address],
                                                              [int(asset.token_id)])
                    liquidation_factor = liquidation_factors[0] / 1e4
                    collateral_factor = collateral_factors[0] / 1e4
                    liquidation_factors_dict[asset.contract_address.lower()] = liquidation_factor
                    collateral_factors_dict[asset.contract_address.lower()] = collateral_factor
                else:
                    liquidation_factor = liquidation_factors_dict[asset.contract_address.lower()]
                    collateral_factor = collateral_factors_dict[asset.contract_address.lower()]

    # return collateral_factors_dict, liquidation_factors_dict
    result = dict()
    for address in collateral_factors_dict.keys():
        asset = ERC20.objects.filter(
            contract_address__iexact=address,
            chain=base
        ).first()
        
        chain_id = base.chain_id
        name = asset.name
        symbol = asset.symbol
        collateral_factor = collateral_factors_dict[address]
        liquidation_factor = liquidation_factors_dict[address]
        if address.lower() not in result:
            result[address.lower()] = {
                "contract_address": address,
                "chain_id": chain_id,
                "name": name,
                "symbol": symbol,
                "pool_address": pool_address,
                "risk_params": {
                    "collateral_factor": collateral_factor,
                    "liquidation_factor": liquidation_factor
                }

            }
    return list(result.values())

@shared_task
def task__arcadia__cache_risk_params(refresh=False):
    cache_key = f'risk_params'
    response = cache.get(cache_key)

    if (not response) or refresh:
        params = [
            {"pool_address": "0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2", "numeraire_address": "0x4200000000000000000000000000000000000006"},
            {"pool_address": "0x3ec4a293Fb906DD2Cd440c20dECB250DeF141dF1", "numeraire_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
        ]

        response = list()

        for param in params:
            response += get_pool_risk_params(**param)

        cache.set(cache_key, response, None)  # Cache for 1 day (86400 seconds)
        # cache.set(cache_key, response, 86400)  # Cache for 1 day (86400 seconds)

    return response


@shared_task
def task__arcadia__oracle_snapshot():
    ORACLE_DATA = [
    {'oracleId': 0,
    'oracleAddress': '0x9DDa783DE64A9d1A60c49ca761EbE528C35BA428',
    'oracleDesc': 'COMP / USD'},
    {'oracleId': 1,
    'oracleAddress': '0x591e79239a7d679378eC8c847e5038150364C78F',
    'oracleDesc': 'DAI / USD'},
    {'oracleId': 2,
    'oracleAddress': '0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70',
    'oracleDesc': 'ETH / USD'},
    {'oracleId': 3,
    'oracleAddress': '0x7e860098F58bBFC8648a4311b374B1D669a2bc6B',
    'oracleDesc': 'USDC / USD'},
    {'oracleId': 4,
    'oracleAddress': '0xd7818272B9e248357d13057AAb0B417aF31E817d',
    'oracleDesc': 'CBETH / USD'},
    {'oracleId': 5,
    'oracleAddress': '0xf397bF97280B488cA19ee3093E81C0a77F02e9a5',
    'oracleDesc': 'RETH / ETH'},
    {'oracleId': 6,
    'oracleAddress': '0x63Af8341b62E683B87bB540896bF283D96B4D385',
    'oracleDesc': 'STG / USD'},
    {'oracleId': 7,
    'oracleAddress': '0xa669E5272E60f78299F4824495cE01a3923f4380',
    'oracleDesc': 'wstETH-ETH Exchange Rate'},
    {'oracleId': 8,
    'oracleAddress': '0x4EC5970fC728C5f65ba413992CD5fF6FD70fcfF0',
    'oracleDesc': 'AERO / USD'}
    ]

    base_chain = Chain.objects.get(chain_name__iexact='base')

    w3 = Web3(Web3.HTTPProvider(base_chain.rpc))
    
    all_assets = ERC20.objects.filter(uniswaplpposition__isnull=True)

    feed_mapping = {
        "0x4200000000000000000000000000000000000006".lower() : "0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70", #Ethereum
        "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22".lower() : "0xd7818272B9e248357d13057AAb0B417aF31E817d", #cbETH
        "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c".lower() : "0xf397bF97280B488cA19ee3093E81C0a77F02e9a5", #rocketpool eth
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913".lower() : "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B", #USDC
        "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA".lower() : "0x7e860098F58bBFC8648a4311b374B1D669a2bc6B", #USDbC
        "0x940181a94A35A4569E4529A3CDfB74e38FD98631".lower() : "0x4EC5970fC728C5f65ba413992CD5fF6FD70fcfF0", #AERO
        "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452".lower() : None # custom strategy for wstETH
    }

    chainlink_prices = {}
    spot_prices = {}
    missed_assets = []
    for asset in all_assets:
        if asset.contract_address.lower() in feed_mapping:
            if feed_mapping[asset.contract_address.lower()] is not None:
                chainlink_prices[asset.contract_address.lower()] = {
                    "price": get_oracle_lastround_price(feed_mapping[asset.contract_address.lower()], w3),
                    "name": asset.name,
                    "symbol": asset.symbol,
                }
            elif asset.contract_address.lower() == "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452".lower():
                # wstETH/WETH price
                price = get_oracle_lastround_price("0xa669E5272E60f78299F4824495cE01a3923f4380", w3) * get_oracle_lastround_price("0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70", w3)
                chainlink_prices[asset.contract_address.lower()] = {
                    "price": price,
                    "name": asset.name,
                    "symbol": asset.symbol,
                }
            # spot price
            timestamp = datetime.now().timestamp()
            price = price_defillama("base", asset.contract_address, str(int(timestamp)))
            spot_prices[asset.contract_address.lower()] = {
                "price": price,
                "name": asset.name,
                "symbol": asset.symbol
            }
        else:
            missed_assets.append({
                "name": asset.name,
                "symbol": asset.symbol
            })
        
    # print(f"{chainlink_prices=} {spot_prices=} {missed_assets=}")
    oracle_snapshot = OracleSnapshot(
        chainlink_prices=chainlink_prices,
        spot_prices=spot_prices,
        missed_assets=missed_assets
    )

    oracle_snapshot.save()


    # price_list = []

    # for oracle in ORACLE_DATA:
        # price_list = price_list.append(get_oracle_lastround_price(oracle['oracleAddress'],w3))

    # # Create and save the metric snapshot    
    # OracleSnapshot.objects.create(
        # comp_in_usd = price_list[0],
        # dai_in_usd = price_list[1],
        # eth_in_usd = price_list[2],
        # usdc_in_usd = price_list[3],
        # cbeth_in_usd = price_list[4],
        # reth_in_eth = price_list[5],
        # stg_in_usd = price_list[6],
        # wsteth_in_eth = price_list[7],
    # )

    # TODO: Complete this function
