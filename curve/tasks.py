import logging
from datetime import datetime, timedelta, timezone

import requests
from celery import shared_task
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from web3 import HTTPProvider, Web3

from core.models import Chain
from curve.models import DebtCeiling, ControllerMetadata, CurveMetrics

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

def curve_batch_api_call(path):
    url = f"{BASE_URL}{path}"
    items = []
    page = 1
    per_page = 100

    while True:
        response = session.get(url, params={"per_page": per_page, "page": page})
        response.raise_for_status()
        data = response.json()
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
    timestamp = datetime.now(tz=timezone.utc)
    cutoff_time = timestamp - timedelta(hours=6)

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain}")
    available_markets = [market for market in markets if market["borrowable"] > 0]

    for market in available_markets:
        controller = market["address"]
        all_users = curve_batch_api_call(f"/v1/crvusd/users/{chain}/{controller}/users")

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
                response = curve_api_call(f"/v1/crvusd/users/{chain}/{user_address}/{controller}/stats")
                user_data.append(response)
            except Exception as e:
                logger.error("Failed to retrieve user positions: User: %s, Controller: %s, Error: %s",
                             user_address, controller, e, exc_info=True)

        market["users"] = user_data

        DebtCeiling(timestamp=timestamp, chain=chain, controller=controller, data=market).save()


@shared_task
def task_curve__update_controller_metadata():
    chain = Chain.objects.get(chain_name__iexact="ethereum")

    web3 = Web3(HTTPProvider(chain.rpc))
    block_number = web3.eth.get_block("latest")["number"]

    markets = curve_batch_api_call(f"/v1/crvusd/markets/{chain}")
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
