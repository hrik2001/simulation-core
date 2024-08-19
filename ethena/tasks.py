import logging
from datetime import datetime, timezone

import requests
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from moralis import evm_api
from web3 import Web3, HTTPProvider

from core.models import Chain
from core.utils import price_defillama, price_defillama_multi
from ethena.models import ChainMetrics, CollateralMetrics, ReserveFundMetrics, ReserveFundBreakdown
from sim_core.settings import MORALIS_KEY

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

RESERVE_FUND_ADDRESS = "0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"

logger = logging.getLogger(__name__)


def update_chain_metrics():
    eth_chain = Chain.objects.get(chain_name__iexact="ethereum")
    web3 = Web3(HTTPProvider(eth_chain.rpc))
    usde_contract = web3.eth.contract(address=USDE_ADDRESS, abi=USDE_ABI)
    susde_contract = web3.eth.contract(address=SUSDE_ADDRESS, abi=SUSDE_ABI)

    latest_block_number = web3.eth.get_block("latest")["number"]
    try:
        chain_metrics = ChainMetrics.objects.latest("created_at")
        last_block_number = chain_metrics.block_number
        last_block_number = max(last_block_number, latest_block_number - 64)
    except ObjectDoesNotExist:
        last_block_number = latest_block_number - 64

    for block_number in range(last_block_number + 1, latest_block_number + 1):
        try:
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
        except ValueError:
            print(f"block not found, skipping {block_number}")
            continue


def update_collateral_metrics():
    collateral = requests.get(ETHENA_COLLATERAL_API).json()
    collateral_metrics = CollateralMetrics(collateral=collateral)
    collateral_metrics.save()


def update_reserve_fund_metrics():
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


def update_reserve_fund_breakdown():
    wallet_tokens = evm_api.token.get_wallet_token_balances(
        api_key=MORALIS_KEY,
        params={
            "chain": "eth",
            "exclude_spam": True,
            "address": RESERVE_FUND_ADDRESS
        },
    )

    token_addresses = [token["token_address"] for token in wallet_tokens]
    token_addresses.append(WETH_ADDRESS)
    token_prices = price_defillama_multi("ethereum", token_addresses)

    refined_wallet_tokens = []
    for token in wallet_tokens:
        usd_value = (float(token['balance']) * token_prices[token["token_address"]]) / (10 ** token['decimals'])
        refined_wallet_tokens.append({
            "token_address": token["token_address"],
            "symbol": token["symbol"],
            "decimals": token["decimals"],
            "balance": token["balance"],
            "usd_value": usd_value
        })

    native_balance = evm_api.balance.get_native_balance(
        api_key=MORALIS_KEY,
        params={
            "chain": "eth",
            "address": RESERVE_FUND_ADDRESS
        },
    )
    eth_usd_value = (float(native_balance['balance']) * token_prices[WETH_ADDRESS]) / (10 ** 18)
    eth_asset = {
        "token_address": WETH_ADDRESS,
        "symbol": "WETH",
        "decimals": 18,
        "balance": native_balance["balance"],
        "usd_value": eth_usd_value
    }
    refined_wallet_tokens.append(eth_asset)

    maker_position = evm_api.wallets.get_defi_positions_by_protocol(
        api_key=MORALIS_KEY,
        params={
            "chain": "eth",
            "address": RESERVE_FUND_ADDRESS,
            "protocol": "makerdao"
        },
    )
    refined_wallet_tokens.append({
        "token_address": maker_position["positions"][0]["address"],
        "symbol": maker_position["positions"][0]["tokens"][0]["symbol"],
        "decimals": maker_position["positions"][0]["tokens"][0]["decimals"],
        "balance": maker_position["positions"][0]["tokens"][0]["balance"],
        "price": maker_position["positions"][0]["tokens"][0]["usd_price"],
        "usd_value": maker_position["positions"][0]["balance_usd"]
    })

    wallet_nfts = evm_api.wallets.get_defi_positions_by_protocol(
        api_key=MORALIS_KEY,
        params={
            "chain": "eth",
            "address": RESERVE_FUND_ADDRESS,
            "protocol": "uniswap-v3"
        },
    )

    refined_wallet_nfts = []
    for nft in wallet_nfts["positions"]:
        refined_wallet_nfts.append({
            "nft_address": "0x2B5AB59163a6e93b4486f6055D33CA4a115Dd4D5",
            "pool_address": nft["position_details"]["pool_address"],
            "position_key": nft["position_details"]["position_key"],
            "balance_usd": nft["balance_usd"],
            "total_unclaimed_usd_value": nft["total_unclaimed_usd_value"],
            "reserves": nft["position_details"]["reserves"],
            "liquidity": nft["position_details"]["liquidity"],
            "price_lower": nft["position_details"]["price_lower"],
            "price_upper": nft["position_details"]["price_upper"],
            "current_price": nft["position_details"]["current_price"],
            "token0": nft["tokens"][0]["contract_address"],
            "token0_symbol": nft["tokens"][0]["symbol"],
            "token0_decimals": nft["tokens"][0]["decimals"],
            "token0_price": nft["tokens"][0]["usd_price"],
            "token1": nft["tokens"][1]["contract_address"],
            "token1_symbol": nft["tokens"][1]["symbol"],
            "token1_decimals": nft["tokens"][1]["decimals"],
            "token1_price": nft["tokens"][1]["usd_price"]
        })

    reserve_funds_nft_usd = sum(nft['balance_usd'] for nft in refined_wallet_nfts)
    reserve_funds_tokens_usd = sum(token['usd_value'] for token in refined_wallet_tokens)
    reserve_funds_total_usd = reserve_funds_nft_usd + reserve_funds_tokens_usd

    breakdown = ReserveFundBreakdown(
        tokens=refined_wallet_tokens,
        positions=refined_wallet_nfts,
        tokens_usd_value=str(reserve_funds_tokens_usd),
        positions_usd_value=str(reserve_funds_nft_usd),
        total_usd_value=str(reserve_funds_total_usd)
    )
    breakdown.save()


@shared_task
def task__ethena__metric_snapshot():
    logger.info("running task to update ethena metrics")
    logger.info("updating chain metrics")
    update_chain_metrics()
    logger.info("updating collateral metrics")
    update_collateral_metrics()
    logger.info("updating reserve fund metrics")
    update_reserve_fund_metrics()
    logger.info("update reserve fund breakdown")
    update_reserve_fund_breakdown()
    logger.info("ethena metrics update task completed successfully")
