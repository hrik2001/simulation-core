import csv
import logging
import os
import traceback
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from string import Template

import numpy as np
import pandas as pd
import requests
from celery import shared_task
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from web3 import HTTPProvider, Web3
from scipy import stats
from scipy.stats import gaussian_kde

from arcadia.utils import weth_address
from core.models import Chain
from curve.models import Top5Debt, ControllerMetadata, CurveMetrics, CurveMarketSnapshot, CurveLlammaTrades, \
    CurveLlammaEvents, CurveCr, CurveMarkets, CurveMarketSoftLiquidations, CurveMarketLosses, CurveScores, \
    CurveScoresDetail, AaveUserData, CurveUserData
from curve.scoring import score_with_limits, score_bad_debt, analyze_price_drops, calculate_volatility_ratio, \
    calculate_recent_gk_beta, score_debt_ceiling
from curve.simuliq.models.aave_protocol import AaveProtocolDTO

logger = logging.getLogger(__name__)

BASE_URL = "https://prices.curve.fi"

retry_strategy = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[403, 429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("http://", adapter)
session.mount("https://", adapter)

CONTROLLER_ABI = [
    {
        "stateMutability": "view",
        "type": "function",
        "name": "amm",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}]
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "monetary_policy",
        "inputs": [],
        "outputs": [{"name": "", "type": "address"}]
    }
]
AMM_ABI = [
    {
        "stateMutability": "view",
        "type": "function",
        "name": "A",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}]
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "get_p",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}]
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "price_oracle",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}]
    },
]

CRV_USD_ADDRESS = Web3.to_checksum_address("0xf939e0a03fb07f59a73314e73794be0e57ac1b4e")
CRV_USD_AGG_ADDRESS = Web3.to_checksum_address("0x18672b1b0c623a30089A280Ed9256379fb0E4E62")
STABLECOIN_LENS_ADDRESS = Web3.to_checksum_address("0xe24e2dB9f6Bb40bBe7c1C025bc87104F5401eCd7")

controller_asset_map = {
    "sfrxETH": "0xEC0820EfafC41D8943EE8dE495fC9Ba8495B15cf",
    "wstETH": "0x100dAa78fC509Db39Ef7D04DE0c1ABD299f4C6CE",
    "WBTC": "0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67",
    "WETH": "0xA920De414eA4Ab66b97dA1bFE9e6EcA7d4219635",
    "tBTC": "0x1C91da0223c763d2e0173243eAdaA0A2ea47E704"
}

SCORING_WEIGHTS = {
    "bad_debt_score": 14,
    "debt_ceiling_score": 14,
    "aggregate_cr_score": 11,
    "aggregate_collateral_under_sl_score": 11,
    "aggregate_vol_ratio_score": 11,
    "aggregate_prob_drop_score": 9,
    "aggregate_borrower_distribution_score": 9,
    "sl_responsiveness_score": 9,
    "interdependency_volatility_score": 6,
    "interdependency_price_momentum_score": 6
}


def curve_batch_api_call(path, condition=None):
    url = f"{BASE_URL}{path}"
    items = []
    page = 1
    per_page = 100

    while True:
        response = session.get(url, params={"per_page": per_page, "page": page})
        response.raise_for_status()
        data = response.json()

        if condition is not None:
            for item in data["data"]:
                if condition(item):
                    items.append(item)
                else:
                    return items
        else:
            items.extend(data["data"])

        if per_page * page > data["count"]:
            break
        page += 1

    return items


def curve_api_call(path, params=None):
    url = f"{BASE_URL}{path}"
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()


@shared_task
def task_curve_update_top5debt_and_users():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()
    timestamp = datetime.now(tz=timezone.utc)
    cutoff_time = timestamp - timedelta(hours=6)

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    available_markets = [market for market in markets if market["borrowable"] > 0]

    all_user_data = []

    for market in available_markets:
        controller = market["address"]
        all_users = curve_batch_api_call(f"/v1/crvusd/users/{chain_name}/{controller}/users")

        active_users = []
        for user in all_users:
            last_time = datetime.fromisoformat(user["last"])
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)

            if last_time > cutoff_time:
                active_users.append(user)

        user_data = []
        for user in active_users:
            user_address = user["user"]
            try:
                response = curve_api_call(f"/v1/crvusd/users/{chain_name}/{user_address}/{controller}/stats")
                user_data.append(response)
                all_user_data.append(response)
            except Exception as e:
                logger.error("Failed to retrieve user positions: User: %s, Controller: %s, Error: %s",
                             user_address, controller, e, exc_info=True)

        user_data.sort(key=lambda x: x["debt"])
        top5_idx = int(len(user_data) * (1 - 0.05))
        top5_debt = sum([x["debt"] for x in user_data[top5_idx:]])

        Top5Debt(timestamp=timestamp, chain=chain, controller=controller, top5_debt=top5_debt).save()
        CurveUserData(chain=chain, controller=controller, data=user_data).save()

    all_user_data.sort(key=lambda x: x["debt"])
    top5_idx = int(len(all_user_data) * (1 - 0.05))
    top5_debt = sum([x["debt"] for x in all_user_data[top5_idx:]])
    Top5Debt(timestamp=timestamp, chain=chain, controller="overall", top5_debt=top5_debt).save()


@shared_task
def task_curve__update_controller_metadata():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    web3 = Web3(HTTPProvider(chain.rpc))
    block_number = web3.eth.get_block("latest")["number"]

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        controller = market["address"]
        controller_contract = web3.eth.contract(address=controller, abi=CONTROLLER_ABI)
        amm = controller_contract.functions.amm().call(block_identifier=block_number)
        monetary_policy = controller_contract.functions.monetary_policy().call(block_identifier=block_number)

        amm_address = Web3.to_checksum_address(amm)
        amm_contract = web3.eth.contract(address=amm_address, abi=AMM_ABI)
        A = amm_contract.functions.A().call(block_identifier=block_number)
        amm_price = amm_contract.functions.get_p().call(block_identifier=block_number)
        oracle_price = amm_contract.functions.price_oracle().call(block_identifier=block_number)

        ControllerMetadata(
            chain=chain,
            controller=controller,
            block_number=block_number,
            amm=amm,
            monetary_policy=monetary_policy,
            A=A,
            amm_price=amm_price,
            oracle_price=oracle_price,
        ).save()


@shared_task
def task_curve__update_curve_usd_metrics():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    web3 = Web3(HTTPProvider(chain.rpc))
    block_number = web3.eth.get_block("latest")["number"]

    stablecoin_lens_contract = web3.eth.contract(address=STABLECOIN_LENS_ADDRESS, abi=[
        {
            "inputs": [],
            "name": "circulating_supply",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        },
    ])
    circulating_supply = stablecoin_lens_contract.functions.circulating_supply().call(block_identifier=block_number)

    crv_usd_agg_contract = web3.eth.contract(address=CRV_USD_AGG_ADDRESS, abi=[
        {
            "stateMutability": "view",
            "type": "function",
            "name": "price",
            "inputs": [],
            "outputs": [{"name": "", "type": "uint256"}]
        }
    ])
    price = crv_usd_agg_contract.functions.price().call(block_identifier=block_number)

    CurveMetrics(chain=chain, block_number=block_number, circulating_supply=circulating_supply, price=price).save()


def get_llamma_url(chain, url_part, model):
    chain_name = chain.chain_name.lower()

    web3 = Web3(HTTPProvider(chain.rpc))
    block_number = web3.eth.get_block("latest")["number"]

    results = []

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        controller = market["address"]
        controller_contract = web3.eth.contract(address=controller, abi=CONTROLLER_ABI)
        amm = controller_contract.functions.amm().call(block_identifier=block_number)

        try:
            latest_date = model.objects.filter(controller=controller).latest("day").day
            condition = lambda x: datetime.fromtimestamp(x["timestamp"]).date() >= latest_date
        except CurveLlammaTrades.DoesNotExist:
            condition = None

        items = curve_batch_api_call(f"/v1/crvusd/{url_part}/{chain_name}/{amm}", condition=condition)
        grouped_items = defaultdict(list)
        for item in items:
            day = datetime.fromtimestamp(item["timestamp"]).date()
            grouped_items[day].append(item)

        results.append({
            "controller": controller,
            "amm": amm,
            "grouped_items": grouped_items,
        })

    return results


@shared_task
def task_curve__update_curve_llamma_trades():
    chain = Chain.objects.get(chain_name__iexact="ethereum")

    objects = []
    for result in get_llamma_url(chain, "llamma_trades", CurveLlammaTrades):
        for day, group in result["grouped_items"].items():
            sold, bought, fee_x, fee_y = 0, 0, 0, 0
            for trade in group:
                if trade["sold_id"] == 0:
                    sold += trade["amount_sold"]
                elif trade["sold_id"] == 1:
                    bought += trade["amount_bought"]
                else:
                    logger.error("Invalid trade: %s", trade)
                fee_x += trade["fee_x"]
                fee_y += trade["fee_y"]

            objects.append(CurveLlammaTrades(
                chain=chain, controller=result["controller"], day=day,
                sold=sold, bought=bought, fee_x=fee_x, fee_y=fee_y
            ))

    CurveLlammaTrades.objects.bulk_create(
        objects,
        update_conflicts=True,
        unique_fields=["chain", "controller", "day"],
        update_fields=["sold", "bought", "fee_x", "fee_y"]
    )


@shared_task
def task_curve__update_curve_llamma_events():
    chain = Chain.objects.get(chain_name__iexact="ethereum")

    objects = []
    for result in get_llamma_url(chain, "llamma_events", CurveLlammaTrades):
        for day, group in result["grouped_items"].items():
            deposit, withdrawal = 0, 0
            for trade in group:
                if trade["withdrawal"] is not None:
                    withdrawal += trade["withdrawal"]["amount_collateral"]
                if trade["deposit"] is not None:
                    deposit += trade["deposit"]["amount"]

            objects.append(CurveLlammaEvents(
                chain=chain, controller=result["controller"], day=day, deposit=deposit, withdrawal=withdrawal
            ))

    CurveLlammaEvents.objects.bulk_create(
        objects,
        update_conflicts=True,
        unique_fields=["chain", "controller", "day"],
        update_fields=["deposit", "withdrawal"]
    )


@shared_task
def task_curve__update_curve_markets():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    total_loans, agg_cr = 0, 0
    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    markets_to_keep = []
    for market in markets:
        controller = market["address"]
        if controller.lower() == "0x8472A9A7632b173c8Cf3a86D3afec50c35548e76".lower():
            continue
        markets_to_keep.append(market)

        try:
            data = curve_api_call(f"/v1/crvusd/liquidations/{chain_name}/{controller}/cr/distribution")
            CurveCr(chain=chain, controller=controller, mean=data["mean"], median=data["median"]).save()

            total_loans += market["n_loans"]
            agg_cr += market["n_loans"] * data["median"]
        except Exception:
            logger.error("Unable to retrieve cr:", exc_info=True)

    system_cr = agg_cr / total_loans
    CurveMarkets(chain=chain, markets=markets_to_keep, system_cr=system_cr).save()


def update_curve_usd_helper(model, url_template, timestamp_field):
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    objects = []
    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        controller = market["address"]
        snapshots = curve_api_call(url_template.substitute(chain_name=chain_name, controller=controller))
        for snapshot in snapshots["data"]:
            timestamp = datetime.fromisoformat(snapshot.pop(timestamp_field))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            objects.append(model(
                chain=chain,
                controller=controller,
                timestamp=timestamp,
                data=snapshot,
            ))

    model.objects.bulk_create(objects, ignore_conflicts=True)


@shared_task
def task_curve__update_curve_usd_snapshots():
    update_curve_usd_helper(
        CurveMarketSnapshot,
        Template("/v1/crvusd/markets/${chain_name}/${controller}/snapshots"),
        "dt"
    )


@shared_task
def task_curve__update_curve_usd_soft_liquidations():
    update_curve_usd_helper(
        CurveMarketSoftLiquidations,
        Template("/v1/crvusd/liquidations/${chain_name}/${controller}/soft_liquidation_ratio"),
        "timestamp"
    )


@shared_task
def task_curve__update_curve_usd_losses():
    update_curve_usd_helper(
        CurveMarketLosses,
        Template("/v1/crvusd/liquidations/${chain_name}/${controller}/losses/history"),
        "timestamp"
    )


def get_coin_price(address):
    start = int((datetime.now() - timedelta(days=180)).timestamp())
    # sfrxeth v2 price is not available through defillama
    if address == "0xac3E018457B222d93114458476f3E3416Abbe38F":
        weth_address = "ethereum:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        response = requests.get(f"https://coins.llama.fi/chart/{weth_address}?start={start}&span=1000&period=6h")
        weth_prices = response.json()["coins"][weth_address]["prices"]

        respones = requests.get("https://api.frax.finance/v2/frxeth/summary/history?range=180d")
        frxeth_prices = respones.json()["items"]
        for price in frxeth_prices:
            price["timestamp"] = int(datetime.fromisoformat(price["intervalTimestamp"][:-1]).timestamp())

        weth_timestamps = [x["timestamp"] for x in weth_prices]
        frxeth_timestamps = [x["timestamp"] for x in frxeth_prices]

        indices = np.searchsorted(weth_timestamps, frxeth_timestamps)
        sfrxeth_prices = [
            {
                "timestamp": x["timestamp"],
                "price": x["sfrxethFrxethPrice"] * x["frxethWethCurve"]["price"] * weth_prices[y]["price"]
            }
            for x, y in zip(frxeth_prices, indices)
        ]
        return sfrxeth_prices
    else:
        coin = f"ethereum:{address}"
        response = requests.get(f"https://coins.llama.fi/chart/{coin}?start={start}&span=1000&period=6h")
        return response.json()["coins"][coin]["prices"]


@shared_task
def task_curve_generate_ratios():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    all_data = []
    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        current = {}

        controller = market["address"]
        if controller.lower() == "0x8472A9A7632b173c8Cf3a86D3afec50c35548e76".lower():
            continue

        current["controller"] = controller

        today = datetime.today()
        now = int(datetime.now().timestamp())
        start = int((today - timedelta(days=30)).timestamp())

        all_snapshots = []
        while start < now:
            snapshots = curve_api_call(f"/v1/crvusd/markets/{chain_name}/{controller}/snapshots", params={
                "fetch_on_chain": False,
                "start": start,
                "agg": "none",
                "sort_by": "DATE_ASC"
            })
            if not snapshots["data"]:
                break

            snapshots_to_keep = []
            for snapshot in snapshots["data"]:
                snapshot["dt"] = datetime.fromisoformat(snapshot["dt"])
                snapshots_to_keep.append(snapshot)

            all_snapshots.extend(snapshots_to_keep)
            start = int(snapshots["data"][-1]["dt"].timestamp() + 1)

        snapshots_df = pd.DataFrame(all_snapshots)

        if not snapshots_df.empty:
            snapshots_df.set_index("dt", inplace=True)

            scientific_columns = ["loan_discount", "liquidation_discount"]
            for col in scientific_columns:
                if col in snapshots_df.columns:
                    snapshots_df[col] = snapshots_df[col].astype(float)

            snapshots_df.sort_index(inplace=True)

        snapshots_df["cr_ratio"] = snapshots_df["total_collateral_usd"] / snapshots_df["total_debt"]
        snapshots_df["hhi"] = snapshots_df["sum_debt_squared"]
        snapshots_df["hhi_ideal"] = (snapshots_df["total_debt"] ** 2) / snapshots_df["n_loans"]
        snapshots_df["hhi_ratio"] = snapshots_df["hhi"] / snapshots_df["hhi_ideal"]

        snapshots_7d_df = snapshots_df.tail(84)

        cr_ratio_30d = snapshots_df["cr_ratio"].mean()
        cr_ratio_7d = snapshots_7d_df["cr_ratio"].mean()
        cr_7d_30d_ratio = cr_ratio_7d / cr_ratio_30d

        hhi_30d = snapshots_df["hhi"].mean()
        hhi_7d = snapshots_7d_df["hhi"].mean()
        hhi_7d_30d_ratio = hhi_7d / hhi_30d

        current["snapshots"] = snapshots_df

        last_row = snapshots_df.iloc[-1]
        liquidation_discount = last_row["liquidation_discount"] / 10 ** 18
        A = float(ControllerMetadata.objects.filter(chain=chain, controller=controller).latest("created_at").A)

        min_ltv = 1 - liquidation_discount - (2 / A)
        max_ltv = 1 - liquidation_discount - (25 / A)

        current["borrowable"] = market["borrowable"]
        current["total_debt"] = market["total_debt"]

        health = curve_api_call(f"/v1/crvusd/liquidations/{chain_name}/{controller}/overview", params={
            "fetch_on_chain": False,
        })
        current["health"] = health

        relative_cr_score = score_with_limits(cr_7d_30d_ratio, 1.1, 0.9, True)
        absolute_cr_score = score_with_limits(1 / last_row["cr_ratio"], 0.75 * max_ltv, 0.75 * min_ltv, False)
        aggregate_cr_score = (0.4 * relative_cr_score + 0.6 * absolute_cr_score)

        bad_debt_score = score_bad_debt(health["bad_debt"], market["total_debt"])

        relative_borrower_distribution_score = score_with_limits(hhi_7d_30d_ratio, 1.1, 0.9, True)
        benchmark_borrower_distribution_score = score_with_limits(last_row["hhi_ratio"], 10, 30, True)
        aggregate_borrower_distribution_score = 0.5 * relative_borrower_distribution_score + 0.5 * benchmark_borrower_distribution_score

        current["scores"] = {
            "relative_cr_score": relative_cr_score,
            "absolute_cr_score": absolute_cr_score,
            "aggregate_cr_score": aggregate_cr_score,
            "bad_debt_score": bad_debt_score,
            "relative_borrower_distribution_score": relative_borrower_distribution_score,
            "benchmark_borrower_distribution_score": benchmark_borrower_distribution_score,
            "aggregate_borrower_distribution_score": aggregate_borrower_distribution_score
        }
        current["score_details"] = {
            "cr_ratio": last_row["cr_ratio"],
            "cr_ratio_7d": cr_ratio_7d,
            "cr_ratio_30d": cr_ratio_30d,
            "cr_7d_30d_ratio": cr_7d_30d_ratio,
            "min_ltv": min_ltv,
            "max_ltv": max_ltv,
            "hhi": last_row["hhi"],
            "hhi_ideal": last_row["hhi_ideal"],
            "hhi_ratio": last_row["hhi_ratio"],
            "hhi_7d": hhi_7d,
            "hhi_30d": hhi_30d,
            "hhi_7d_30d_ratio": hhi_7d_30d_ratio,
        }

        print(market["collateral_token"]["symbol"], controller, last_row["hhi"], last_row["hhi_ratio"], hhi_7d_30d_ratio)

        prices = get_coin_price(market["collateral_token"]["address"])
        prices_df = pd.DataFrame(prices)
        prices_df["timestamp"] = pd.to_datetime(prices_df["timestamp"], unit="s")
        prices_df.set_index("timestamp", inplace=True)
        prices_df.sort_index(inplace=True)
        current["prices"] = prices_df

        daily_ohlc = pd.DataFrame({
            "open": prices_df["price"].resample("D").first(),
            "high": prices_df["price"].resample("D").max(),
            "low": prices_df["price"].resample("D").min(),
            "close": prices_df["price"].resample("D").last()
        })
        current["daily_ohlc"] = daily_ohlc

        probabilities = analyze_price_drops(daily_ohlc, [0.075, 0.15])
        prob_drop1 = probabilities["drop1"]["parametric_probability"]
        prob_drop2 = probabilities["drop2"]["parametric_probability"]
        prob_drop1_score = score_with_limits(prob_drop1, 0.03, 0, False)
        prob_drop2_score = score_with_limits(prob_drop2, 0.0075, 0, False)
        aggregate_prob_drop_score = (0.5 * prob_drop1_score + 0.5 * prob_drop2_score)
        current["scores"]["prob_drop1_score"] = prob_drop1_score
        current["scores"]["prob_drop2_score"] = prob_drop2_score
        current["scores"]["aggregate_prob_drop_score"] = aggregate_prob_drop_score

        current["score_details"]["prob_drop1"] = prob_drop1
        current["score_details"]["prob_drop2"] = prob_drop2

        end = datetime.now()
        start = end - timedelta(days=180)
        data = curve_api_call(f"/v1/crvusd/liquidations/ethereum/{controller}/soft_liquidation_ratio", params={
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
        })

        sl_df = pd.DataFrame(data["data"])
        sl_df = sl_df.sort_values("timestamp")
        sl_df["timestamp"] = pd.to_datetime(sl_df["timestamp"], format="%Y-%m-%dT%H:%M:%S")
        sl_df["debt_under_sl_ratio_7d"] = sl_df["debt_under_sl_ratio"].rolling(7).mean()
        sl_df["debt_under_sl_ratio_30d"] = sl_df["debt_under_sl_ratio"].rolling(30).mean()
        sl_df["collateral_under_sl_ratio_7d"] = sl_df["collateral_under_sl_ratio"].rolling(7).mean()
        sl_df["collateral_under_sl_ratio_30d"] = sl_df["collateral_under_sl_ratio"].rolling(30).mean()
        sl_df.set_index("timestamp", inplace=True)

        current["sl"] = sl_df

        latest_row = sl_df.iloc[-1].to_dict()
        current_collateral_under_sl_ratio = latest_row["collateral_under_sl_ratio"]
        # Handle division by zero case
        if latest_row["collateral_under_sl_ratio_30d"] == 0:
            relative_collateral_under_sl_ratio = 1.0  # Default value when denominator is zero
        else:
            relative_collateral_under_sl_ratio = (latest_row["collateral_under_sl_ratio_7d"] /
                                                  latest_row["collateral_under_sl_ratio_30d"])

        collateral_under_sl_score = score_with_limits(current_collateral_under_sl_ratio, 2, 0, False)
        relative_collateral_under_sl_score = score_with_limits(relative_collateral_under_sl_ratio, 2.5, 0.5, False, 1)
        aggregate_collateral_under_sl_score = (
                    0.4 * collateral_under_sl_score + 0.6 * relative_collateral_under_sl_score)

        current["scores"]["collateral_under_sl_score"] = collateral_under_sl_score
        current["scores"]["relative_collateral_under_sl_score"] = relative_collateral_under_sl_score
        current["scores"]["aggregate_collateral_under_sl_score"] = aggregate_collateral_under_sl_score

        current["score_details"]["debt_under_sl_ratio"] = latest_row["debt_under_sl_ratio"]
        current["score_details"]["debt_under_sl_ratio_7d"] = latest_row["debt_under_sl_ratio_7d"]
        current["score_details"]["debt_under_sl_ratio_30d"] = latest_row["debt_under_sl_ratio_30d"]
        current["score_details"]["collateral_under_sl_ratio"] = latest_row["collateral_under_sl_ratio"]
        current["score_details"]["collateral_under_sl_ratio_7d"] = latest_row["collateral_under_sl_ratio_7d"]
        current["score_details"]["collateral_under_sl_ratio_30d"] = latest_row["collateral_under_sl_ratio_30d"]

        try:
            output = calculate_sl_score(controller)
            sl_score = output["overall_score"]
            spread_analysis_score = output["spread_analysis"]["score"]
            peak_analysis_score = output["peak_analysis"]["score"]
        except Exception:
            print(traceback.format_exc())
            sl_score, spread_analysis_score, peak_analysis_score = 0.0, 0.0, 0.0

        current["scores"]["sl_responsiveness_score"] = sl_score
        current["score_details"]["sl_spread_analysis_score"] = spread_analysis_score
        current["score_details"]["sl_peak_analysis_score"] = peak_analysis_score

        all_data.append(current)

    btc_ohlc = None
    for current in all_data:
        if current["controller"] == "0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67":
            btc_ohlc = current["daily_ohlc"]

    with open(os.path.join(os.path.dirname(__file__), "debt_ceiling_score.csv"), "r") as f:
        reader = csv.DictReader(f)
        rows: list[dict] = []
        for row in reader:
            rows.append(row)
        latest_debt_ceiling = max(rows, key=lambda x: int(x["timestamp"]))
        debt_ceiling_scores = {
            controller_asset_map[asset]: int(score)
            for asset, score in latest_debt_ceiling.items()
            if asset != "timestamp"
        }

    for current in all_data:
        vol_45d, vol_180d, vol_ratio = calculate_volatility_ratio(current["daily_ohlc"])
        vol_ratio_score = score_with_limits(vol_ratio, 1.5, 0.75, False)
        current["scores"]["vol_ratio_score"] = vol_ratio_score

        beta = calculate_recent_gk_beta(current["daily_ohlc"], btc_ohlc)
        beta_score = score_with_limits(beta, 2.5, 0.5, False, 1)
        current["scores"]["beta_score"] = beta_score

        aggregate_vol_ratio_score = (0.4 * vol_ratio_score + 0.6 * beta_score)
        current["scores"]["aggregate_vol_ratio_score"] = aggregate_vol_ratio_score

        recommended_debt_ceiling = debt_ceiling_scores[current["controller"]]
        current_debt_ceiling = current["borrowable"] + current["total_debt"]
        current["scores"]["debt_ceiling_score"] = score_debt_ceiling(
            recommended_debt_ceiling,
            current_debt_ceiling,
            current["total_debt"]
        )

        current["score_details"]["volatility_45d"] = vol_45d
        current["score_details"]["volatility_180d"] = vol_180d
        current["score_details"]["volatility_ratio"] = vol_ratio
        current["score_details"]["beta"] = beta
        current["score_details"]["total_debt"] = current["total_debt"]
        current["score_details"]["borrowable"] = current["borrowable"]
        current["score_details"]["bad_debt"] = current["health"]["bad_debt"]
        current["score_details"]["recommended_debt_ceiling"] = debt_ceiling_scores[current["controller"]]

        current["scores"]["interdependency_volatility_score"] = np.median([
            current["scores"]["aggregate_vol_ratio_score"],
            current["scores"]["aggregate_collateral_under_sl_score"],
            current["scores"]["aggregate_borrower_distribution_score"],
            current["scores"]["sl_responsiveness_score"],
        ])
        current["scores"]["interdependency_price_momentum_score"] = np.median([
            current["scores"]["aggregate_cr_score"],
            current["scores"]["aggregate_prob_drop_score"],
            current["scores"]["aggregate_borrower_distribution_score"],
            current["scores"]["debt_ceiling_score"],
        ])

        weighted_average_score = 0
        for score, weight in SCORING_WEIGHTS.items():
            weighted_average_score += current["scores"][score] * weight
        current["scores"]["weighted_average_score"] = weighted_average_score

        # Save detailed metrics
        CurveScoresDetail(chain=chain, controller=current["controller"], **current["score_details"]).save()
        CurveScores(controller=current["controller"], chain=chain, **current["scores"]).save()


@shared_task
def task_curve_finance():
    from curve.simuliq.scripts.main import main
    main()


def analyze_distributions_combined(reference_df, test_df, column='deviation_product', bins=100):
    """
    Analyzes distributions combining both spread analysis and peak location analysis.

    Parameters:
    reference_df: DataFrame with reference distribution
    test_df: DataFrame with test distribution
    column: column name to analyze
    bins: number of bins for histogram

    Returns:
    dict: Combined analysis results and scores
    """
    # Get data and handle extreme values
    ref_data = reference_df[column].values
    test_data = test_df[column].values

    # Handle infinities and NaNs
    def clean_extreme_values(data):
        # Get max value that's not inf
        max_val = np.nanmax(data[~np.isinf(data)])
        min_val = np.nanmin(data[~np.isinf(data)])

        # Replace positive infinities with max value
        data = np.where(data == np.inf, max_val, data)
        # Replace negative infinities with min value
        data = np.where(data == -np.inf, min_val, data)
        # Replace NaNs with 0
        data = np.nan_to_num(data, nan=0.0)

        return data

    ref_data = clean_extreme_values(ref_data)
    test_data = clean_extreme_values(test_data)

    # Calculate reference statistics
    ref_std = np.std(ref_data)

    # Spread Analysis
    spread_metrics = {
        'reference': {
            'std': np.std(ref_data),
            'iqr': stats.iqr(ref_data),
            'range': np.ptp(ref_data)
        },
        'test': {
            'std': np.std(test_data),
            'iqr': stats.iqr(test_data),
            'range': np.ptp(test_data)
        }
    }

    def spread_ratio_score(test_val, ref_val):
        ratio = test_val / ref_val if ref_val != 0 else float('inf')

        if ratio <= 1:  # Test spread is tighter than reference
            # Score from 50 to 100 as ratio goes from 1 to 0
            return 50 + (50 * (1 - ratio))
        else:  # Test spread is wider than reference
            # Score from 50 to 0 as ratio goes from 1 to 25
            return max(0, 50 * (25 - ratio) / 24)

    spread_score = np.mean([
        spread_ratio_score(spread_metrics['test']['std'], spread_metrics['reference']['std']),
        spread_ratio_score(spread_metrics['test']['iqr'], spread_metrics['reference']['iqr']),
        spread_ratio_score(spread_metrics['test']['range'], spread_metrics['reference']['range'])
    ])

    # Peak Analysis
    def find_distribution_peak(data):
        kde = gaussian_kde(data)
        x_range = np.linspace(np.min(data), np.max(data), 1000)
        density = kde(x_range)
        peak_idx = np.argmax(density)
        return x_range[peak_idx]

    ref_peak = find_distribution_peak(ref_data)
    test_peak = find_distribution_peak(test_data)

    # Calculate peak difference in terms of reference standard deviations
    peak_diff_in_stds = abs(test_peak - ref_peak) / ref_std
    peak_score = 100 * np.exp(-peak_diff_in_stds * 5)

    # Calculate overall score
    overall_score = (spread_score + peak_score) / 2

    output_dict = {
        'spread_analysis': {
            'score': spread_score,
            'metrics': spread_metrics
        },
        'peak_analysis': {
            'score': peak_score,
            'metrics': {
                'reference_peak': ref_peak,
                'test_peak': test_peak,
                'difference_in_std_units': peak_diff_in_stds,
                'reference_std': ref_std,
                'absolute_difference': abs(test_peak - ref_peak)
            }
        },
        'overall_score': overall_score
    }

    return output_dict


def calculate_sl_score(controller):
    url = f"https://api.curvemonitor.com/mintMarketRiskInfo/{controller}"
    response = requests.get(url)
    response.raise_for_status()

    data = []
    for x in response.json():
        data.append({
            "blockNumber": x["blockNumber"],
            "amountBorrowableToken": float(x["amountBorrowableToken"]),
            "amountCollatToken": float(x["amountCollatToken"]),
            "oraclePrice": float(x["oraclePrice"]),
            "get_p": float(x["get_p"]),
            "amountCollatTokenInUsd": float(x["amountCollatTokenInUsd"]),
            "amountFullInBandInUsd": float(x["amountFullInBandInUsd"]),
        })
    df = pd.DataFrame(data)

    df["diff"] = (df["get_p"] - df["oraclePrice"])
    df["crvUSD"] = df["amountBorrowableToken"]
    df["collateral"] = df["amountCollatTokenInUsd"]
    df["deviation_product"] = np.where(
        df["diff"] > 0,
        df["crvUSD"] * df["diff"],
        np.where(
            df["diff"] < 0,
            df["collateral"] * df["diff"],
            0
        )
    )
    test = df.head(len(df) // 3).copy(deep=True)

    count = len(test[test["deviation_product"] == 0])
    fraction = count / len(test)

    if fraction >= 0.85:
        return {
            "overall_score": 50.0,
            "spread_analysis": {
                "score": 50.0
            },
            "peak_analysis": {
                "score": 50.0
            }
        }

    output = analyze_distributions_combined(df, test)
    return output


@shared_task
def task_aave_user_data_indexing():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    protocol_dto = AaveProtocolDTO(
        chain=chain,
        protocol="aave",
        batch_data_provider_address="0x5c438e0e82607a3a07e6726b10e200739635895b",
        aave_pool_address="0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
        aave_data_provider_address="0x41393e5e337606dc3821075Af65AeE84D7688CBD",
        holder_query_id=4101003
    )
    pd.set_option('display.max_columns', None)
    df = protocol_dto.get_aave_supported_asset_data()
    user_df = protocol_dto.get_user_position_data(df)
    AaveUserData(chain=chain, data=user_df.to_json(orient='records')).save()
