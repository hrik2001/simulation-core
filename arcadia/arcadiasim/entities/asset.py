from ..models.asset import (Asset, ConcentratedLiquidityAsset,
                            ConcentratedLiquidityAssetPosition)
from .chain import base, ethereum

usdt = Asset(
    symbol="USDT",
    name="Tether USD",
    decimals=6,
    contract_address="0xdAC17F958D2ee523a2206206994597C13D831ec7",
    chain=ethereum,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "tether"},
    },
)


usdc = Asset(
    symbol="USDC",
    name="Circle USD",
    decimals=6,
    contract_address="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
    chain=base,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "usd-coin", "coingecko_vs_currency": "usd"},
    },
)

usdbc = Asset(
    symbol="USDBC",
    name="Bridged USD Coin (Base)",
    decimals=6,
    contract_address="0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca",
    chain=base,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "usd-coin", "coingecko_vs_currency": "usd"},
    },
)

dai = Asset(
    symbol="DAI",
    name="Dai",
    decimals=18,
    contract_address="0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
    chain=base,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "usd-coin", "coingecko_vs_currency": "usd"},
    },
)

weth = Asset(
    symbol="WETH",
    name="Wrapped ETH",
    decimals=18,
    contract_address="0x4200000000000000000000000000000000000006",
    chain=base,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "weth", "coingecko_vs_currency": "eth"},
    },
)

cbETH = Asset(
    symbol="cbETH",
    name="Coinbase Wrapped Staked ETH",
    decimals=18,
    chain=base,
    contract_address="0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22",
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        # "strategy": "dexguru_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "coinbase-wrapped-staked-eth"},
    },
)

rETH = Asset(
    symbol="RETH",
    name="Rocket Pool ETH",
    decimals=18,
    contract_address="0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c",
    chain=base,
    pricing_metadata={
        # "strategy": "coingecko_strategy",
        "strategy": "defillama_strategy",
        "metadata": {"coingecko_id": "rocket-pool-eth"},
    },
)


lp_share_usdc_weth = Asset(
    symbol="vAMM-WETH/USDC",
    name="LP Share: USDC-WETH (Aerodrome)",
    decimals=18,
    contract_address="0xcdac0d6c6c59727a65f871236188350531885c43",
    chain=base,
    pricing_metadata={
        "strategy": "LPS_usdc_weth_pricing",
        "metadata": {
            "protocol_name": "Aerodrome",
            "reserve_asset_0": weth,
            "reserve_asset_1": usdc,
        },
    },
)

usdc_chainlink = Asset(
    symbol="USDC",
    name="Circle USD",
    decimals=6,
    contract_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    chain=ethereum,
    pricing_metadata={
        "strategy": "chainlink_strategy",
        "metadata": {
            "feed_name": "USDC / USD",
            "chainlink_feed_contract_address": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
            "decimals": 8,
        },
    },
)

############################################
### Uni V3 LP Collateral Asset           ###
############################################

weth_usdc_univ3_lp = ConcentratedLiquidityAsset(
    symbol="weth-usdc",
    name="WETH-USDC",
    contract_address="0xd0b53D9277642d899DF5C87A3966A349A798F224",
    decimals=18,
    chain=base,
    token0=weth,
    token1=usdc,
    fee=500,
    position=ConcentratedLiquidityAssetPosition(
        usd_value_invested=1,
        interval_spread=0.1,
    ),
    pricing_metadata=None,
)

usdc_usdbc_univ3_lp = ConcentratedLiquidityAsset(
    symbol="usdc-usdbc",
    name="USDC-USDBC",
    contract_address="0x06959273E9A65433De71F5A452D529544E07dDD0",
    decimals=18,
    chain=base,
    token0=usdc,
    token1=usdbc,
    fee=100,
    position=ConcentratedLiquidityAssetPosition(
        usd_value_invested=1,
        interval_spread=0.001,
    ),
    pricing_metadata=None,
)

cbeth_weth_univ3_lp = ConcentratedLiquidityAsset(
    symbol="cbeth-weth",
    name="CBETH-WETH",
    contract_address="0x10648BA41B8565907Cfa1496765fA4D95390aa0d",
    decimals=18,
    chain=base,
    token0=cbETH,
    token1=weth,
    fee=500,
    position=ConcentratedLiquidityAssetPosition(
        usd_value_invested=1,
        interval_spread=0.001,
    ),
    pricing_metadata=None,
)

weth_usdbc_univ3_lp = ConcentratedLiquidityAsset(
    symbol="weth-usdbc",
    name="WETH-USDBC",
    contract_address="0x4C36388bE6F416A29C8d8Eee81C771cE6bE14B18",
    decimals=18,
    chain=base,
    token0=weth,
    token1=usdbc,
    fee=500,
    position=ConcentratedLiquidityAssetPosition(
        usd_value_invested=1,
        interval_spread=0.1,
    ),
    pricing_metadata=None,
)
