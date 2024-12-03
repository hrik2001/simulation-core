import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from string import Template

import pandas as pd
import requests
from celery import shared_task
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from web3 import HTTPProvider, Web3

from core.models import Chain
from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics, CurveMarketSnapshot, CurveLlammaTrades, \
    CurveLlammaEvents, CurveCr, CurveMarkets, CurveMarketSoftLiquidations, CurveMarketLosses, CurveScores
from curve.scoring import score_with_limits, score_bad_debt, analyze_price_drops, calculate_volatility_ratio, \
    calculate_recent_gk_beta

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
def task_curve__update_debt_ceiling():
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
        market["users"] = user_data

        DebtCeiling(timestamp=timestamp, chain=chain, controller=controller, data=market, top5_debt=top5_debt).save()

    all_user_data.sort(key=lambda x: x["debt"])
    top5_idx = int(len(all_user_data) * (1 - 0.05))
    top5_debt = sum([x["debt"] for x in all_user_data[top5_idx:]])
    DebtCeiling(timestamp=timestamp, chain=chain, controller="overall", data={}, top5_debt=top5_debt).save()


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

    crv_usd_contract = web3.eth.contract(address=CRV_USD_ADDRESS, abi=[
        {
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ])
    total_supply = crv_usd_contract.functions.totalSupply().call(block_identifier=block_number)

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

    CurveMetrics(chain=chain, block_number=block_number, total_supply=total_supply, price=price).save()


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


@shared_task
def task_curve_generate_ratios():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    all_data = []
    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        current = {}

        controller = market["address"]
        snapshots = curve_api_call(f"/v1/crvusd/markets/{chain_name}/{controller}/snapshots", params={
            "fetch_on_chain": False,
            "agg": "day"
        })

        current["controller"] = controller

        snapshots_df = pd.DataFrame(snapshots["data"])
        if not snapshots_df.empty:
            snapshots_df["dt"] = pd.to_datetime(snapshots_df["dt"])
            snapshots_df.set_index("dt", inplace=True)
    
            scientific_columns = ["loan_discount", "liquidation_discount"]
            for col in scientific_columns:
                if col in snapshots_df.columns:
                    snapshots_df[col] = snapshots_df[col].astype(float)
    
            snapshots_df.sort_index(inplace=True)
    
        snapshots_df["cr_ratio"] = snapshots_df["total_collateral_usd"] / snapshots_df["total_debt"]
        snapshots_df["cr_ratio_30d"] = snapshots_df["cr_ratio"].rolling(30).mean()
        snapshots_df["cr_ratio_7d"] = snapshots_df["cr_ratio"].rolling(7).mean()
        snapshots_df["cr_7d/30d"] = snapshots_df["cr_ratio_7d"] / snapshots_df["cr_ratio_30d"]

        current["snapshots"] = snapshots_df

        last_row = snapshots_df.iloc[-1]
        liquidation_discount = last_row["liquidation_discount"] / 10 ** 18
        A = float(ControllerMetadata.objects.filter(chain=chain, controller=controller).latest("created_at").A)

        min_ltv = 1 - liquidation_discount - (2 / A)
        max_ltv = 1 - liquidation_discount - (25 / A)

        current["min_ltv"] = min_ltv
        current["max_ltv"] = max_ltv

        health = curve_api_call(f"/v1/crvusd/liquidations/{chain_name}/{controller}/overview", params={
            "fetch_on_chain": False,
        })
        current["health"] = health

        relative_cr_score = score_with_limits(last_row["cr_7d/30d"], 1.1, 0.9, True)
        absolute_cr_score = score_with_limits(1 / last_row["cr_ratio"], 0.75 * max_ltv, 0.75 * min_ltv, False)
        aggregate_cr_score = (0.4 * relative_cr_score + 0.6 * absolute_cr_score)

        bad_debt_score = score_bad_debt(health["bad_debt"], market["total_debt"])

        current["scores"] = {
            "relative_cr_score": relative_cr_score,
            "absolute_cr_score": absolute_cr_score,
            "aggregate_cr_score": aggregate_cr_score,
            "bad_debt_score": bad_debt_score,
        }

        start = int((datetime.now() - timedelta(days=100)).timestamp())
        coin = f"ethereum:{market['collateral_token']['address']}"
        response = requests.get(f"https://coins.llama.fi/chart/{coin}?start={start}&span=400&period=6h").json()

        prices_df = pd.DataFrame(response["coins"][coin]["prices"])
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
        aggregate_collateral_under_sl_score = (0.4 * collateral_under_sl_score + 0.6 * relative_collateral_under_sl_score)

        current["scores"]["collateral_under_sl_score"] = collateral_under_sl_score
        current["scores"]["relative_collateral_under_sl_score"] = relative_collateral_under_sl_score
        current["scores"]["aggregate_collateral_under_sl_score"] = aggregate_collateral_under_sl_score

        all_data.append(current)

    btc_ohlc = None
    for current in all_data:
        if current["controller"] == "0x4e59541306910aD6dC1daC0AC9dFB29bD9F15c67":
            btc_ohlc = current["daily_ohlc"]

    for current in all_data:
        vol_45d, vol_180d, vol_ratio = calculate_volatility_ratio(current["daily_ohlc"])
        vol_ratio_score = score_with_limits(vol_ratio, 1.5, 0.75, False)
        current["scores"]["vol_ratio_score"] = vol_ratio_score

        beta = calculate_recent_gk_beta(current["daily_ohlc"], btc_ohlc)
        beta_score = score_with_limits(beta, 2.5, 0.5, False, 1)
        current["scores"]["beta_score"] = beta_score

        aggregate_vol_ratio_score = (0.4 * vol_ratio_score + 0.6 * beta_score)
        current["scores"]["aggregate_vol_ratio_score"] = aggregate_vol_ratio_score

        CurveScores(controller=current["controller"], chain=chain, **current["scores"]).save()
