import logging
import time
from datetime import datetime, timezone, timedelta, tzinfo
from string import Template

import dateutil.parser
import requests
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from django.db.models.functions import Abs, Extract
from dune_client.client import DuneClient
from moralis import evm_api
from web3 import Web3, HTTPProvider

from core.models import Chain
from core.utils import price_defillama, price_defillama_multi
from ethena.models import ChainMetrics, CollateralMetrics, ReserveFundMetrics, ReserveFundBreakdown, \
    UniswapPoolSnapshots, CurvePoolInfo, CurvePoolSnapshots, StakingMetrics, ExitQueueMetrics, ApyMetrics, \
    FundingRateMetrics, UstbYieldMetrics, BuidlYieldMetrics, UsdmMetrics, BuidlRedemptionMetrics
from sim_core.settings import MORALIS_KEY, SUBGRAPH_KEY, DUNE_KEY, COINANALYZE_KEY

RAY = 10 ** 27
SECONDS_IN_YEAR = 365 * 24 * 60 * 60

supply_function = {
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
assets_function = {
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
}

USDE_ADDRESS = Web3.to_checksum_address("0x4c9edd5852cd905f086c759e8383e09bff1e68b3")
USDE_ABI = [supply_function]

SUSDE_ADDRESS = Web3.to_checksum_address("0x9d39a5de30e57443bff2a8307a4256c8797a3497")
SUSDE_ABI = [supply_function, assets_function]

POT_ADDRESS = Web3.to_checksum_address("0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7")
POT_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "dsr",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

SDAI_ADDRESS = Web3.to_checksum_address("0x83f20f44975d03b1b09e64809b757c47f942beea")
SDAI_ABI = [supply_function, assets_function]

DAI_ADDRESS = Web3.to_checksum_address("0x6b175474e89094c44da98b954eedeac495271d0f")
DAI_ABI = [supply_function]

BUIDL_ADDRESS = Web3.to_checksum_address(
    "0x7712c34205737192402172409a8f7ccef8aa2aec")  # address of implementation contract of proxy BUIDL
BUIDL_ABI = [
    {
        "inputs": [],
        "name": "totalIssued",
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
        "name": "walletCount",
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
    supply_function
]

USDM_ADDRESS = Web3.to_checksum_address("0x59d9356e565ab3a36dd77763fc0d87feaf85508c")
USDM_ABI = [
    {
        "inputs": [],
        "name": "totalShares",
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
    supply_function
]

SUPERSTATE_USTB_ADDRESS = Web3.to_checksum_address(
    "0x43415eB6ff9DB7E26A15b704e7A3eDCe97d31C4e")  # address of implementation contract of proxy Superstate USTB
SUPERSTATE_USTB_ABI = [
    {
        "inputs": [],
        "name": "entityMaxBalance",
        "outputs": [
            {
                "internalType":
                    "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    supply_function
]

USDT_ADDRESS = Web3.to_checksum_address("0xdac17f958d2ee523a2206206994597c13d831ec7")
USDT_ABI = [
    {
        "inputs": [
            {
                "name": "",
                "type": "address"
            }
        ],
        "name": "balances",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
ETHENA_USDT_ADDRESS = Web3.to_checksum_address("0xe3490297a08d6fC8Da46Edb7B6142E4F461b62D3")

UNISWAP_POOL_ADDRESSES = [
    "0x435664008f38b0650fbc1c9fc971d0a3bc2f1e47",
    "0x867b321132b18b5bf3775c0d9040d1872979422e",
    "0xe6d7ebb9f1a9519dc06d557e03c522d53520e76a"
]
UNISWAP_QUERY = Template("""\
{
  poolDayDatas(
    first: 1
    orderBy: date
    where: {pool: "$poolAddress"}
    orderDirection: desc
  ) {
    sqrtPrice
    token0Price
    token1Price
    tvlUSD
    volumeUSD
    txCount
    pool {
      totalValueLockedToken0
      token0 {
        id
        symbol
      }
      token0Price
      totalValueLockedToken1
      token1 {
        id
        symbol
      }
      token1Price
    }
    id
    close
    feesUSD
  }
}
""")

ETHENA_COLLATERAL_API = "https://ethena.fi/api/positions/current/collateral"
ETHENA_RESERVE_FUND_API = "https://ethena.fi/api/solvency/reserve-fund"
CURVE_BASE_URL = "https://prices.curve.fi/v1"

RESERVE_FUND_ADDRESS = "0x2b5ab59163a6e93b4486f6055d33ca4a115dd4d5"
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
CURVE_POOL_ADDRESSES = [
    "0x5dc1bf6f1e983c0b21efb003c105133736fa0743",
    "0x167478921b907422f8e88b43c4af2b8bea278d3a",
    "0x02950460e2b9529d0e00284a5fa2d7bdf3fa4d72",
    "0xf36a4ba50c603204c3fc6d2da8b78a7b69cbc67d",
    "0xf55b0f6f2da5ffddb104b58a60f2862745960442",
    "0x670a72e6d22b0956c0d2573288f82dcc5d6e3a61",
    "0xf8db2accdef8e7a26b0e65c3980adc8ce11671a4",
    "0x1ab3d612ea7df26117554dddd379764ebce1a5ad",
    "0x964573b560da1ce5b10dd09a4723c5ccbe9f9688",
    "0x57064f49ad7123c92560882a45518374ad982e85"
]

YIELDS_BASE_URL = "https://yields.llama.fi"
YIELD_POOLS = [
    {"symbol": "DSR", "pool_id": "c8a24fee-ec00-4f38-86c0-9f6daebc4225"},
    {"symbol": "sUSDe", "pool_id": "66985a81-9c51-46ca-9977-42b4fe7bc6df"},
    {"symbol": "aaveUSDT", "pool_id": "f981a304-bb6c-45b8-b0c5-fd2f515ad23a"},
    {"symbol": "aaveUSDC", "pool_id": "aa70268e-4b52-42bf-a116-608b370f9501"},
    {"symbol": "USD3", "pool_id": "9c4e675e-7615-4d60-90ef-03d58c66b476"},
    {"symbol": "hyUSD", "pool_id": "3378bced-4bde-4ccf-b742-7d5c8ebb7720"}
]

FUNDING_RATE_URL = "https://api.coinalyze.net/v1/funding-rate-history"
FUNDING_RATE_DICT = [
    {
        "symbol": "BTCUSDT_PERP.A",
        "exchange": "binance"
    },
    {
        "symbol": "BTCUSDT.6",
        "exchange": "bybit"
    },
    {
        "symbol": "BTCUSDT_PERP.3",
        "exchange": "okx"
    },
    {
        "symbol": "BTC_USDC-PERPETUAL.2",
        "exchange": "deribit"
    },
    {
        "symbol": "ETHUSDT_PERP.A",
        "exchange": "binance"
    },
    {
        "symbol": "ETHUSDT.6",
        "exchange": "bybit"
    },
    {
        "symbol": "ETHUSDT_PERP.3",
        "exchange": "okx"
    },
    {
        "symbol": "ETH_USDC-PERPETUAL.2",
        "exchange": "deribit"
    }

]


logger = logging.getLogger(__name__)


def update_chain_metrics():
    eth_chain = Chain.objects.get(chain_name__iexact="ethereum")
    web3 = Web3(HTTPProvider(eth_chain.rpc))
    usde_contract = web3.eth.contract(address=USDE_ADDRESS, abi=USDE_ABI)
    susde_contract = web3.eth.contract(address=SUSDE_ADDRESS, abi=SUSDE_ABI)
    dai_contract = web3.eth.contract(address=DAI_ADDRESS, abi=DAI_ABI)
    sdai_contract = web3.eth.contract(address=SDAI_ADDRESS, abi=SDAI_ABI)
    pot_contract = web3.eth.contract(address=POT_ADDRESS, abi=POT_ABI)
    usdt_contract = web3.eth.contract(address=USDT_ADDRESS, abi=USDT_ABI)
    usdm_contract = web3.eth.contract(address=USDM_ADDRESS, abi=USDM_ABI)
    superstate_ustb_contract = web3.eth.contract(address=SUPERSTATE_USTB_ADDRESS, abi=SUPERSTATE_USTB_ABI)
    buidl_contract = web3.eth.contract(address=BUIDL_ADDRESS, abi=BUIDL_ABI)

    latest_block_number = web3.eth.get_block("latest")["number"]
    try:
        chain_metrics = ChainMetrics.objects.latest("created_at")
        last_block_number = chain_metrics.block_number
        last_block_number = max(last_block_number, latest_block_number - 2)
    except ObjectDoesNotExist:
        last_block_number = latest_block_number - 2

    for block_number in range(last_block_number + 1, latest_block_number + 1):
        try:
            block = web3.eth.get_block(block_number)

            timestamp = block["timestamp"]

            usde_supply = usde_contract.functions.totalSupply().call(block_identifier=block_number)
            susde_supply = susde_contract.functions.totalSupply().call(block_identifier=block_number)
            susde_staked = susde_contract.functions.totalAssets().call(block_identifier=block_number)
            dai_supply = dai_contract.functions.totalSupply().call(block_identifier=block_number)
            sdai_supply = sdai_contract.functions.totalSupply().call(block_identifier=block_number)
            sdai_staked = sdai_contract.functions.totalAssets().call(block_identifier=block_number)
            usdt_balance = usdt_contract.functions.balances(ETHENA_USDT_ADDRESS).call(block_identifier=block_number)
            buidl_supply = buidl_contract.functions.totalSupply().call(block_identifier=block_number)
            buidl_issued = buidl_contract.functions.totalIssued().call(block_identifier=block_number)
            buidl_wallet_count = buidl_contract.functions.walletCount().call(block_identifier=block_number)
            usdm_supply = usdm_contract.functions.totalSupply().call(block_identifier=block_number)
            usdm_shares = usdm_contract.functions.totalShares().call(block_identifier=block_number)
            superstate_ustb_supply = superstate_ustb_contract.functions.totalSupply().call(
                block_identifier=block_number)
            superstate_ustb_balance = superstate_ustb_contract.functions.entityMaxBalance().call(
                block_identifier=block_number)

            usde_price = price_defillama("ethereum", USDE_ADDRESS, timestamp)
            susde_price = price_defillama("ethereum", SUSDE_ADDRESS, timestamp)
            sdai_price = price_defillama("ethereum", SDAI_ADDRESS, timestamp)
            dai_price = price_defillama("ethereum", DAI_ADDRESS, timestamp)
            usdt_price = price_defillama("ethereum", USDT_ADDRESS, timestamp)
            usdm_price = price_defillama("ethereum", USDM_ADDRESS, timestamp)
            superstate_ustb_price = price_defillama("ethereum", SUPERSTATE_USTB_ADDRESS, timestamp)
            try:
                buidl_price = price_defillama("ethereum", BUIDL_ADDRESS, timestamp)
            except Exception:
                buidl_price = "0"

            dsr = pot_contract.functions.dsr().call(block_identifier=block_number)
            dsr_rate = 100 * ((dsr / RAY) ** SECONDS_IN_YEAR) - 100

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
                total_sdai_supply=str(sdai_supply),
                sdai_price=str(sdai_price),
                dsr_rate=str(dsr_rate),
                total_dai_supply=str(dai_supply),
                total_dai_staked=str(sdai_staked),
                usdt_balance=str(usdt_balance),
                dai_price=str(dai_price),
                usdt_price=str(usdt_price),
                total_usdm_supply=str(usdm_supply),
                total_superstate_ustb_supply=str(superstate_ustb_supply),
                total_buidl_supply=str(buidl_supply),
                usdm_price=str(usdm_price),
                superstate_ustb_price=str(superstate_ustb_price),
                buidl_price=str(buidl_price),
                total_buidl_issued=str(buidl_issued),
                total_usdm_shares=str(usdm_shares),
                total_superstate_ustb_balance=str(superstate_ustb_balance),
                buidl_wallet_count=str(buidl_wallet_count)
            )
            chain_metrics.save()
        except ValueError:
            print(f"block not found, skipping {block_number}")
            continue


def update_collateral_metrics():
    response = requests.get(ETHENA_COLLATERAL_API)
    response.raise_for_status()
    collateral = response.json()
    collateral_metrics = CollateralMetrics(collateral=collateral)
    collateral_metrics.save()


def update_reserve_fund_metrics():
    try:
        last_reserve_fund = ReserveFundMetrics.objects.latest("timestamp")
        last_reserve_fund_timestamp = last_reserve_fund.timestamp
    except ObjectDoesNotExist:
        last_reserve_fund_timestamp = datetime.fromtimestamp(0, tz=timezone.utc)

    response = requests.get(ETHENA_RESERVE_FUND_API)
    response.raise_for_status()
    reserve_fund = response.json()
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


def update_uniswap_pool_snapshots():
    uniswap_url = f"https://gateway.thegraph.com/api/{SUBGRAPH_KEY}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    pools = {}
    for poolAddress in UNISWAP_POOL_ADDRESSES:
        query = UNISWAP_QUERY.substitute({"poolAddress": poolAddress})
        response = requests.post(uniswap_url, json={"query": query})
        data = response.json()["data"]["poolDayDatas"][0]
        pools[poolAddress] = data
        uniswap_snapshot = UniswapPoolSnapshots(address=poolAddress, snapshot=data,
                                                timestamp=datetime.now(tz=timezone.utc))
        uniswap_snapshot.save()


def update_curve_pool_info():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()
    for address in CURVE_POOL_ADDRESSES:
        metrics_url = f"{CURVE_BASE_URL}/pools/{chain_name}/{address}"
        response = requests.get(metrics_url).json()
        response.pop("pool_methods", None)
        timestamp = datetime.now(tz=timezone.utc)
        curve_pool_info = CurvePoolInfo(chain=chain, address=address, timestamp=timestamp, info=response)
        curve_pool_info.save()


def update_curve_pool_snapshots():
    chain = Chain.objects.get(chain_name__iexact="ethereum")
    chain_name = chain.chain_name.lower()

    end = datetime.now(tz=timezone.utc)
    try:
        last_pool_snapshot = CurvePoolSnapshots.objects.latest("timestamp")
        last_reserve_fund_timestamp = last_pool_snapshot.timestamp
    except ObjectDoesNotExist:
        last_reserve_fund_timestamp = datetime.fromtimestamp(0, tz=timezone.utc)
    start = max(end - timedelta(hours=4), last_reserve_fund_timestamp)

    for address in CURVE_POOL_ADDRESSES:
        snapshots_url = f"{CURVE_BASE_URL}/snapshots/{chain_name}/{address}/tvl"
        response = requests.get(snapshots_url, params={
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "unit": "none"
        }).json()

        for snapshot in response["data"]:
            if snapshot["tvl_usd"] is None:
                continue
            timestamp = snapshot.pop("timestamp")
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            block_number = snapshot.pop("block_number")

            closest_curve_pool_info = (
                CurvePoolInfo
                .objects
                .filter(address=address)
                .annotate(time_diff=Abs(Extract(F('timestamp') - timestamp, 'epoch')))
                .order_by('time_diff')
                .first()
            )
            snapshot["info"] = closest_curve_pool_info.info

            pool_snapshot = CurvePoolSnapshots(
                chain=chain,
                block_number=block_number,
                timestamp=timestamp,
                address=address,
                snapshot=snapshot
            )
            pool_snapshot.save()


def query_dune(query_id):
    dune = DuneClient(
        api_key=DUNE_KEY,
        base_url="https://api.dune.com",
        request_timeout=5000
    )
    return dune.get_latest_result(query_id, batch_size=500, max_age_hours=8)


def update_apy_metrics():
    for pool in YIELD_POOLS:
        pool_url = f"{YIELDS_BASE_URL}/chart/{pool['pool_id']}"
        response = requests.get(pool_url).json()
        objects = []
        for metric in response["data"]:
            apy_metric = ApyMetrics(
                timestamp=datetime.fromisoformat(metric["timestamp"].replace("Z", "+00:00")),
                symbol=pool["symbol"],
                pool_id=pool["pool_id"],
                tvl_usd=str(metric["tvlUsd"]) if metric["tvlUsd"] is not None else None,
                apy=str(metric["apy"]) if metric["apy"] is not None else None,
                apy_base=str(metric["apyBase"]) if metric["apyBase"] is not None else None,
                apy_reward=str(metric["apyReward"]) if metric["apyReward"] is not None else None,
                il7d=str(metric["il7d"]) if metric["il7d"] is not None else None,
                apy_base_7d=str(metric["apyBase7d"]) if metric["apyBase7d"] is not None else None,
            )
            objects.append(apy_metric)
        ApyMetrics.objects.bulk_create(objects, ignore_conflicts=True)


def update_funding_rates():
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=1)
    to_ts = int(to_dt.timestamp())
    from_ts = int(from_dt.timestamp())

    objects = []

    for item in FUNDING_RATE_DICT:
        symbol = item["symbol"]
        exchange = item["exchange"]

        try:
            logger.info(f"Fetching data for {symbol} on {exchange}...")
            params = {
                "symbols": symbol,
                "interval": "4hour",
                "from": from_ts,
                "to": to_ts
            }

            headers = {"api_key": COINANALYZE_KEY}
            response = requests.get(FUNDING_RATE_URL, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            for point in data[0]["history"]:
                timestamp = datetime.fromtimestamp(point["t"], tz=timezone.utc)
                rate = str(float(point["c"]))

                objects.append(FundingRateMetrics(
                    symbol=symbol,
                    exchange=exchange,
                    timestamp=timestamp,
                    rate=rate,
                ))

            time.sleep(1)  # Add a small delay to avoid hitting rate limits
        except Exception:
            logger.exception(f"Failed to fetch data for {symbol} on {exchange}", exc_info=True)

    FundingRateMetrics.objects.bulk_create(objects, ignore_conflicts=True)


def update_ustb_yield_metrics():
    url = "https://api.superstate.co/v1/funds/1/yield"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    UstbYieldMetrics.objects.bulk_create([UstbYieldMetrics(
        date=dateutil.parser.parse(data["as_of_date"]).replace(tzinfo=timezone.utc),
        thirty_day=str(data["thirty_day"]) if data["thirty_day"] is not None else None,
        seven_day=str(data["seven_day"]) if data["seven_day"] is not None else None,
        one_day=str(data["one_day"]) if data["one_day"] is not None else None,
    )], ignore_conflicts=True)


def update_buidl_yield_metrics():
    query_result = query_dune(4150762)
    objects = []
    for row in query_result.result.rows:
        _row = {
            "date": dateutil.parser.parse(row["time"]).replace(tzinfo=timezone.utc),
            "amount": str(row["amount"]) if row["amount"] is not None else None,
            "apy_7d": str(row["APY_7d"]) if row["APY_7d"] is not None else None,
            "apy_30d": str(row["APY_30d"]) if row["APY_30d"] is not None else None,
        }
        objects.append(BuidlYieldMetrics(**_row))
    BuidlYieldMetrics.objects.bulk_create(objects, ignore_conflicts=True)


def update_usdm_metrics():
    query_result = query_dune(3050717)
    objects = []
    for row in query_result.result.rows:
        if row["apy"] is not None:
            _row = {
                "date": dateutil.parser.parse(row["period"]).replace(tzinfo=timezone.utc),
                "holders": str(row["holders"]) if row["holders"] is not None else None,
                "index": str(row["index"]) if row["index"] is not None else None,
                "apy": str(row["apy"]),
            }
            objects.append(UsdmMetrics(**_row))
    UsdmMetrics.objects.bulk_create(objects, ignore_conflicts=True)


def update_buidl_redemption_metrics():
    query_result = query_dune(3543899)
    objects = []
    for row in query_result.result.rows:
        _row = {
            "date": dateutil.parser.parse(row["day"]).replace(tzinfo=timezone.utc),
            "balance": str(row["balance_raw"]) if row["balance_raw"] is not None else None,
        }
        objects.append(BuidlRedemptionMetrics(**_row))
    BuidlRedemptionMetrics.objects.bulk_create(objects, ignore_conflicts=True)


@shared_task
def task__ethena__metric_snapshot():
    logger.info("running task to update ethena metrics")

    try:
        logger.info("updating chain metrics")
        update_chain_metrics()
    except Exception as e:
        logger.exception(e)

    try:
        logger.info("update reserve fund breakdown")
        update_reserve_fund_breakdown()
    except Exception as e:
        logger.exception(e)

    try:
        logger.info("updating collateral metrics")
        update_collateral_metrics()
    except Exception as e:
        logger.exception(e)

    try:
        logger.info("updating reserve fund metrics")
        update_reserve_fund_metrics()
    except Exception as e:
        logger.exception(e)

    logger.info("ethena metrics update task completed successfully")


@shared_task
def task__ethena__uniswap_stats():
    logger.info("running task to update uniswap stats")
    update_uniswap_pool_snapshots()
    logger.info("updating uniswap stats")


@shared_task
def task__ethena__curve_metrics():
    logger.info("running task to update curve pool metrics")
    update_curve_pool_info()
    logger.info("updating curve pool metrics")


@shared_task
def task__ethena__curve_pool_snapshots():
    logger.info("running task to update curve pool snapshots")
    update_curve_pool_snapshots()
    logger.info("updating curve pool snapshots")


@shared_task
def task__ethena__staking_metrics():
    logger.info("running task to update staking metrics")
    query_result = query_dune(4069937)
    objects = []
    for row in query_result.result.rows:
        _row = {**row, "day": dateutil.parser.parse(row["day"]).replace(tzinfo=timezone.utc)}
        objects.append(StakingMetrics(**_row))
    StakingMetrics.objects.bulk_create(objects, ignore_conflicts=True)
    logger.info("updating staking metrics")


@shared_task
def task__ethena__exit_queue_metrics():
    logger.info("running task to update exit queue metrics")
    query_result = query_dune(4026879)
    objects = []
    for row in query_result.result.rows:
        _row = {
            "withdraw_day": dateutil.parser.parse(row["withdraw_day"]).replace(tzinfo=timezone.utc),
            "unlock_day": dateutil.parser.parse(row["unlock_day"]).replace(tzinfo=timezone.utc),
            "usde": row["USDe"],
            "susde": row["sUSDe"],
            "total_usde": row["total_USDe"],
            "total_susde": row["total_sUSDe"],
        }
        objects.append(ExitQueueMetrics(**_row))
    ExitQueueMetrics.objects.bulk_create(objects, ignore_conflicts=True)
    logger.info("updating exit queue metrics")


@shared_task
def task__ethena__apy_metrics():
    logger.info("running task to update apy metrics")
    update_apy_metrics()
    logger.info("updated apy metrics")


@shared_task
def task__ethena__funding_rate_metrics():
    logger.info("running task to update funding rate metrics")
    update_funding_rates()
    logger.info("updated funding rate metrics")


@shared_task
def task__ethena__ustb_yield_metrics():
    logger.info("running task to update ustb yield metrics")
    update_ustb_yield_metrics()
    logger.info("updated ustb yield metrics")


@shared_task
def task__ethena__buidl_metrics():
    logger.info("running task to update buidl metrics")
    try:
        update_buidl_yield_metrics()
    except Exception:
        logger.exception("BUIDL Yield metrics error: %s", exc_info=True)
    try:
        update_buidl_redemption_metrics()
    except Exception:
        logger.exception("BUIDL redemption metrics error: %s", exc_info=True)
    logger.info("updated buidl metrics")


@shared_task
def task__ethena__usdm_yield_metrics():
    logger.info("running task to update usdm yield metrics")
    update_usdm_metrics()
    logger.info("updated usdm yield metrics")
