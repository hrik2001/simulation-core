import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests
from celery import shared_task
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from web3 import HTTPProvider, Web3

from core.models import Chain
from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics, CurveMarketSnapshot, CurveLlammaTrades, \
    CurveLlammaEvents, CurveCr, CurveMarkets

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


def curve_api_call(path):
    url = f"{BASE_URL}{path}"
    response = session.get(url)
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
            except Exception as e:
                logger.error("Failed to retrieve user positions: User: %s, Controller: %s, Error: %s",
                             user_address, controller, e, exc_info=True)

        market["users"] = user_data

        DebtCeiling(timestamp=timestamp, chain=chain, controller=controller, data=market).save()


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


@shared_task
def task_curve__update_curve_usd_snapshots():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    objects = []
    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain_name}")
    for market in markets:
        controller = market["address"]
        snapshots = curve_api_call(f"/v1/crvusd/markets/{chain_name}/{controller}/snapshots")
        for snapshot in snapshots["data"]:
            timestamp = datetime.fromisoformat(snapshot.pop("dt"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            objects.append(CurveMarketSnapshot(
                chain=chain,
                controller=controller,
                timestamp=timestamp,
                data=snapshot,
            ))

    CurveMarketSnapshot.objects.bulk_create(objects, ignore_conflicts=True)


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
        try:
            controller = market["address"]
            if controller.lower() == "0x8472A9A7632b173c8Cf3a86D3afec50c35548e76".lower():
                continue
            markets_to_keep.append(market)

            data = curve_api_call(f"/v1/crvusd/liquidations/{chain_name}/{controller}/cr/distribution")
            CurveCr(chain=chain, controller=controller, mean=data["mean"], median=data["median"]).save()

            total_loans += market["n_loans"]
            agg_cr += market["n_loans"] * data["mean"]
        except Exception:
            logger.error("Unable to retrieve cr:", exc_info=True)

    system_cr = agg_cr / total_loans
    CurveMarkets(chain=chain, markets=markets_to_keep, system_cr=system_cr).save()
