from datetime import datetime, timezone

import requests
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from web3 import Web3, HTTPProvider

from core.models import Chain
from core.utils import price_defillama
from ethena.models import ChainMetrics, CollateralMetrics, ReserveFundMetrics

USDE_ADDRESS = Web3.to_checksum_address("0x4c9edd5852cd905f086c759e8383e09bff1e68b3")
USDE_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

SUSDE_ADDRESS = Web3.to_checksum_address("0x9d39a5de30e57443bff2a8307a4256c8797a3497")
SUSDE_ABI = [
    {
        "inputs": [],
        "name": "totalAssets",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

ETHENA_COLLATERAL_API = "https://app.ethena.fi/api/positions/current/collateral"
ETHENA_RESERVE_FUND_API = "https://app.ethena.fi/api/solvency/reserve-fund"


@shared_task
def task__ethena__metric_snapshot():
    eth_chain = Chain.objects.get(chain_name__iexact="ethereum")
    web3 = Web3(HTTPProvider(eth_chain.rpc))
    usde_contract = web3.eth.contract(address=USDE_ADDRESS, abi=USDE_ABI)
    susde_contract = web3.eth.contract(address=SUSDE_ADDRESS, abi=SUSDE_ABI)

    latest_block_number = web3.eth.get_block("latest")["number"]
    try:
        chain_metrics = ChainMetrics.objects.latest("created_at")
        last_block_number = chain_metrics.block_number
    except ObjectDoesNotExist:
        last_block_number = latest_block_number - 64

    for block_number in range(last_block_number + 1, latest_block_number + 1):
        block = web3.eth.get_block(block_number)
        timestamp = block["timestamp"]

        usde_supply = usde_contract.functions.totalSupply().call(block_identifier=block_number)
        susde_supply = susde_contract.functions.totalSupply().call(block_identifier=block_number)
        susde_staked = susde_contract.functions.totalAssets().call(block_identifier=block_number)

        usde_price = price_defillama("ethereum", USDE_ADDRESS, timestamp)
        susde_price = price_defillama("ethereum", SUSDE_ADDRESS, timestamp)

        chain_metrics = ChainMetrics(
            block_hash=block["hash"].hex(),
            block_number=block_number,
            block_timestamp=datetime.fromtimestamp(timestamp, tz=timezone.utc),
            chain=eth_chain,
            total_usde_supply=str(usde_supply),
            total_usde_staked=str(susde_staked),
            total_susde_supply=str(susde_supply),
            usde_price=str(usde_price),
            susde_price=str(susde_price),
        )
        chain_metrics.save()

    collateral = requests.get(ETHENA_COLLATERAL_API).json()
    collateral_metrics = CollateralMetrics(collateral=collateral)
    collateral_metrics.save()

    try:
        last_reserve_fund = ReserveFundMetrics.objects.latest("timestamp")
        last_reserve_fund_timestamp = last_reserve_fund.timestamp
    except ObjectDoesNotExist:
        last_reserve_fund_timestamp = datetime.fromtimestamp(0, tz=timezone.utc)

    reserve_fund = requests.get(ETHENA_RESERVE_FUND_API).json()
    for datum in reserve_fund["queryIndex"][0]["yields"]:
        try:
            if datum["timestamp"].endswith("Z"):
                format_str = datum["timestamp"][:-1]
            else:
                format_str = datum["timestamp"]
            timestamp = datetime.fromisoformat(format_str + "+00:00")
        except ValueError:
            continue

        if timestamp >= last_reserve_fund_timestamp:
            value = str(datum["value"])
            reserve_fund_metrics = ReserveFundMetrics(timestamp=timestamp, value=value)
            reserve_fund_metrics.save()
