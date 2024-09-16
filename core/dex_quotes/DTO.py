from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class chainDTO:
    """
    Data Transfer Object to store relevant
    chain data.
    """

    network: str
    network_id: int

@dataclass(frozen=True, order=True)
class TokenDTO:
    """
    Data Transfer Object to store relevant
    token data.
    """

    # TODO DTO min/max trade sizes should be dynamic
    address: str
    name: str
    symbol: str
    decimals: int
    network: chainDTO
    min_trade_size: float  # min amt_in for 1inch quotes
    max_trade_size: float  # max amt_in for 1inch quotes


######################### Chain Declaration ###############################

OPTIMISM_DTO = chainDTO(
    network="Optimism",
    network_id=10
    
) 

ARIBTRUM_DTO = chainDTO(
    network="Arbitrum",
    network_id=42161
    
) 

ETHEREUM_DTO = chainDTO(
    network="Ethereum",
    network_id=42161
    
)

network_mapping = {
    OPTIMISM_DTO.network_id: OPTIMISM_DTO,
    ARIBTRUM_DTO.network_id: ARIBTRUM_DTO,
    ETHEREUM_DTO.network_id: ETHEREUM_DTO

    # Add more chainDTO instances as needed
}


######################### Token Declaration ###############################
## Stables 
CRVUSD_OP = "0xC52D7F23a2e460248Db6eE192Cb23dD12bDDCbf6"
USDC_OP = "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
USDT_OP = "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58"
DAI_OP = "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1"
FRAX_OP = "0x2e3d870790dc77a83dd1d18184acc7439a53f475"

CRVUSD_ARB = "0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5"
USDC_ARB = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
USDT_ARB = "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
DAI_ARB= "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1" # same
FRAX_ARB = "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F"

CRVUSD_ETH = "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e"
USDC_ETH = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
USDT_ETH = "0xdac17f958d2ee523a2206206994597c13d831ec7"
USDP_ETH = "0x8e870d67f660d95d5be530380d0ec0bd388289e1"
TUSD_ETH = "0x0000000000085d4780b73119b644ae5ecd22b376"
PYUSD_ETH = "0x6c3ea9036406852006290770bedfcaba0e23a0e8"

## Collateral 
WETH_OP = "0x4200000000000000000000000000000000000006"
WSTETH_OP = "0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb"
WBTC_OP = "0x68f180fcCe6836688e9084f035309E29Bf0A2095"
OP = "0x4200000000000000000000000000000000000042"
VELO = "0x9560e827af36c94d2ac33a39bce1fe78631088db"


WETH_ARB = "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"
WSTETH_ARB = "0x5979D7b546E38E414F7E9822514be443A4800529"
WBTC_ARB = "0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f"
ARB = "0x912ce59144191c1204e64559fe8253a0e49e6548"
GMX = "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a"
PENDLE = "0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8"
RDNT = "0x3082CC23568eA640225c2467653dB90e9250AaA0"

# crvusd
WETH_ETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
WSTETH_ETH = "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0"
SFRXETH_ETH = "0x5e8422345238f34275888049021821e8e08caa1f"
WBTC_ETH = "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599"
TBTC_ETH = "0x18084fba666a33d37592fa2633fd49a74dd93a88"

# aave
WEETH_ETH = '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee'
AAVE_ETH = '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9'
CBBTC_ETH = '0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf'


STABLES = [USDC_OP, USDC_ARB, USDC_ETH, 
           USDT_OP, USDT_ARB, USDT_ETH, 
           USDP_ETH, PYUSD_ETH, TUSD_ETH,
           CRVUSD_OP, CRVUSD_ARB, CRVUSD_ETH,
           DAI_OP, DAI_OP, 
           FRAX_OP, FRAX_ARB]
COLLATERAL = [WETH_OP, WETH_ARB, WETH_ETH,
              WSTETH_OP, WSTETH_ARB, WSTETH_ETH,
              WBTC_OP, WBTC_ARB, WBTC_ETH, TBTC_ETH, 
              SFRXETH_ETH, AAVE_ETH, WEETH_ETH, CBBTC_ETH,
              OP, ARB, GMX, PENDLE, RDNT, VELO]
ADDRESSES = STABLES + COLLATERAL

# Coingecko Helpers
COINGECKO_IDS = {
    USDC_OP: "usd-coin", USDC_ARB: "usd-coin", USDC_ETH : "usd-coin", 
    USDT_OP: "tether", USDT_ARB: "tether", USDT_ETH: "tether", 
    CRVUSD_OP: "crvusd", CRVUSD_ARB: "crvusd", CRVUSD_ETH: "crvusd", 
    DAI_OP: "dai", DAI_ARB: "dai", 
    FRAX_OP: "frax", FRAX_ARB: "frax",
    WETH_OP: "weth", WETH_ARB: "weth",  WETH_ETH: "weth", 
    WSTETH_OP: "wrapped-steth", WSTETH_ARB: "wrapped-steth", WSTETH_ETH: "wrapped-steth",
    WBTC_OP: "wrapped-bitcoin", WBTC_ARB:  "wrapped-bitcoin", WBTC_ETH:  "wrapped-bitcoin",
    USDP_ETH: "paxos-standard", 
    PYUSD_ETH: "paypal-usd", 
    TUSD_ETH: "true-usd",
    SFRXETH_ETH: "staked-frax-ether", 
    TBTC_ETH: "tbtc", 
    WEETH_ETH: 'wrapped-eeth',
    AAVE_ETH: 'aave', 
    CBBTC_ETH: 'coinbase-wrapped-btc',


    OP: "optimism",
    ARB: "arbitrum", 
    GMX: "gmx", 
    PENDLE: "pendle", 
    RDNT: "radiant-capital",
    VELO: 'velodrome-finance'
}
STABLE_CG_IDS = [COINGECKO_IDS[coin] for coin in STABLES]
COINGECKO_IDS_INV = {v: k for k, v in COINGECKO_IDS.items()}

# TODO script to update these with new tokens

# DTOs
CRVUSD_OP_DTO = TokenDTO(
    address=CRVUSD_OP,
    name="Curve.Fi USD Stablecoin (Optimism)",
    symbol="crvUSD",
    decimals=18,
    network = OPTIMISM_DTO,
    min_trade_size=1e3,
    max_trade_size=300_000,
)  # NOTE don't add to TOKEN_DTOs

CRVUSD_ARB_DTO = TokenDTO(
    address=CRVUSD_ARB,
    name="Curve.Fi USD Stablecoin (Arbitrum)",
    symbol="crvUSD",
    decimals=18,
    network=ARIBTRUM_DTO, 
    min_trade_size=1e3,
    max_trade_size=1_100_000,
)  # NOTE don't add to TOKEN_DTOs

CRVUSD_ETH_DTO = TokenDTO(
    address=CRVUSD_ETH,
    name="Curve.Fi USD Stablecoin (Ethereum)",
    symbol="crvUSD",
    decimals=18,
    network=ETHEREUM_DTO, 
    min_trade_size=0,
    max_trade_size=0,
)  # NOTE don't add to TOKEN_DTOs

USDC_OP_DTO = TokenDTO(
    address=USDC_OP,
    name="USD Coin (Optimism)",
    symbol="USDC",
    decimals=6,
    network=OPTIMISM_DTO, 
    min_trade_size=1e2,
    max_trade_size=1_500_000,
)

USDC_ARB_DTO = TokenDTO(
    address=USDC_ARB,
    name="USD Coin (Arbitrum)",
    symbol="USDC",
    decimals=6,
    network=ARIBTRUM_DTO,
    min_trade_size=1e2,
    max_trade_size=4_500_000,
)

USDC_ETH_DTO = TokenDTO(
    address=USDC_ETH,
    name="USD Coin (Ethereum)",
    symbol="USDC",
    decimals=6,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

USDT_OP_DTO = TokenDTO(
    address=USDT_OP,
    name="Tether USD (Optimism)" ,
    symbol="USDT",
    decimals=6,
    network=OPTIMISM_DTO, 
    min_trade_size=1e2,
    max_trade_size=3_500_000,
)

USDT_ARB_DTO = TokenDTO(
    address=USDT_ARB,
    name="Tether USD (Arbitrum)",
    symbol="USDT",
    decimals=6,
    network=ARIBTRUM_DTO,
    min_trade_size=1e2,
    max_trade_size=3_500_000,
)

USDT_ETH_DTO = TokenDTO(
    address=USDT_ETH,
    name="Tether USD (Ethereum)",
    symbol="USDT",
    decimals=6,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

TUSD_ETH_DTO = TokenDTO(
    address=TUSD_ETH,
    name="True USD (Ethereum)",
    symbol="TUSD",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

PYUSD_ETH_DTO = TokenDTO(
    address=PYUSD_ETH,
    name="True USD (Ethereum)",
    symbol="PYUSD",
    decimals=6,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

USDP_ETH_DTO = TokenDTO(
    address=USDP_ETH,
    name="Pax Dollar",
    symbol="USDP",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

DAI_OP_DTO = TokenDTO(
    address=DAI_OP,
    name="DAI Stablecoin (Optimism)",
    symbol="DAI",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=1e2,
    max_trade_size=3_500_000,
)

DAI_ARB_DTO = TokenDTO(
    address=DAI_ARB,
    name="DAI Stablecoin (Arbitrum)",
    symbol="DAI",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=1e2,
    max_trade_size=5_500_000,
)

FRAX_OP_DTO =  TokenDTO(
    address=FRAX_OP,
    name="Frax Stablecoin (Optimism)",
    symbol="FRAX",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=1e2,
    max_trade_size=500_000,
)

FRAX_ARB_DTO =  TokenDTO(
    address=FRAX_ARB,
    name="Frax Stablecoin (Arbitrum)",
    symbol="FRAX",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=1e2,
    max_trade_size=1_500_000,
)


WETH_OP_DTO = TokenDTO(
    address=WETH_OP,
    name="Wrapped Ether (Optimism)",
    symbol="WETH",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=0.1,
    max_trade_size=30000,
)

WETH_ARB_DTO = TokenDTO(
    address=WETH_ARB,
    name="Wrapped Ether (Arbitrum)",
    symbol="WETH",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=0.1,
    max_trade_size=40000,
)

WETH_ETH_DTO = TokenDTO(
    address=WETH_ETH,
    name="Wrapped Ether (Ethereum)",
    symbol="WETH",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

WSTETH_OP_DTO = TokenDTO(
    address=WSTETH_OP,
    name="Wrapped liquid staked Ether 2.0 (Optimism)",
    symbol="WSTETH",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=0.5,
    max_trade_size=3500,
)

WSTETH_ARB_DTO = TokenDTO(
    address=WSTETH_ARB,
    name="Wrapped liquid staked Ether 2.0 (Arbitrum)",
    symbol="WSTETH",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=0.5,
    max_trade_size=2500,
)

WSTETH_ETH_DTO = TokenDTO(
    address=WSTETH_ETH,
    name="Wrapped liquid staked Ether 2.0 (Ethereum)",
    symbol="WSTETH",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

SFRXETH_ETH_DTO = TokenDTO(
    address=SFRXETH_ETH,
    name="Staked Frax Ether",
    symbol="SFRXETH",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

WEETH_ETH_DTO = TokenDTO(
    address=WEETH_ETH,
    name="Wrapped EtherFi Ether",
    symbol="WEETH",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)

TBTC_ETH_DTO = TokenDTO(
    address=TBTC_ETH,
    name="tBTC v2",
    symbol="TBTC",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0.5,
    max_trade_size=2500,
)

CBBTC_ETH_DTO = TokenDTO(
    address=CBBTC_ETH,
    name="Coinbase BTC",
    symbol="cbBTC",
    decimals=8,
    network=ETHEREUM_DTO,
    min_trade_size=0.5,
    max_trade_size=2500,

)

WBTC_OP_DTO = TokenDTO(
    address=WBTC_OP,
    name="Wrapped BTC (Optimism)",
    symbol="WBTC",
    decimals=8,
    network=OPTIMISM_DTO,
    min_trade_size=0.03,
    max_trade_size=20,
)

WBTC_ARB_DTO = TokenDTO(
    address=WBTC_ARB,
    name="Wrapped BTC (Arbitrum)",
    symbol="WBTC",
    decimals=8,
    network=ARIBTRUM_DTO,
    min_trade_size=0.03,
    max_trade_size=250,
)


WBTC_ETH_DTO = TokenDTO(
    address=WBTC_ETH,
    name="Wrapped BTC (Ethereum)",
    symbol="WBTC",
    decimals=8,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)


AAVE_ETH_DTO = TokenDTO(
    address=AAVE_ETH,
    name="Aave",
    symbol="AAVE",
    decimals=18,
    network=ETHEREUM_DTO,
    min_trade_size=0,
    max_trade_size=0,
)


OP_DTO = TokenDTO(
    address=OP,
    name="Optimism",
    symbol="OP",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=10,
    max_trade_size=1_000_000,
)

VELO_DTO = TokenDTO(
    address=VELO,
    name="Velodrome Finance",
    symbol="VELO",
    decimals=18,
    network=OPTIMISM_DTO,
    min_trade_size=10,
    max_trade_size=1_000_000,
)

ARB_DTO = TokenDTO(
    address=ARB,
    name="Arbitrum",
    symbol="ARB",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=10,
    max_trade_size=8_100_000,
)

GMX_DTO = TokenDTO(
    address=GMX,
    name="GMX",
    symbol="GMX",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=1,
    max_trade_size=60_000,
)

PENDLE_DTO = TokenDTO(
    address=PENDLE,
    name="Pendle Finance",
    symbol="PENDLE",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=10,
    max_trade_size=1_000_000,
)

RDNT_DTO = TokenDTO(
    address=RDNT,
    name="Radiant Capital",
    symbol="RDNT",
    decimals=18,
    network=ARIBTRUM_DTO,
    min_trade_size=500,
    max_trade_size=5_000_000,
)

TOKEN_DTOs = {

    "Optimism": {
        CRVUSD_OP: CRVUSD_OP_DTO,
        USDC_OP: USDC_OP_DTO,
        USDT_OP: USDT_OP_DTO,
        FRAX_OP: FRAX_OP_DTO,
        DAI_OP: DAI_OP_DTO, 

        WETH_OP: WETH_OP_DTO, 
        WSTETH_OP: WSTETH_OP_DTO, 
        WBTC_OP: WBTC_OP_DTO, 
        OP: OP_DTO, 
        VELO: VELO_DTO
                },

    "Arbitrum":{
        CRVUSD_ARB: CRVUSD_ARB_DTO,
        USDC_ARB: USDC_ARB_DTO,
        USDT_ARB: USDT_ARB_DTO, 
        FRAX_ARB: FRAX_ARB_DTO, 
        DAI_ARB: DAI_ARB_DTO, 

        WETH_ARB: WETH_ARB_DTO, 
        WSTETH_ARB: WSTETH_ARB_DTO, 
        WBTC_ARB: WBTC_ARB_DTO, 
        ARB: ARB_DTO, 
        GMX: GMX_DTO, 
        PENDLE: PENDLE_DTO, 
        RDNT:RDNT_DTO
    },

    "Ethereum": {
        CRVUSD_ETH: CRVUSD_ETH_DTO,
        USDC_ETH: USDC_ETH_DTO,
        USDT_ETH: USDT_ETH_DTO,
        PYUSD_ETH: PYUSD_ETH_DTO, 
        TUSD_ETH: TUSD_ETH_DTO, 
        USDP_ETH: USDP_ETH_DTO, 

        WETH_ETH: WETH_ETH_DTO,
        WSTETH_ETH: WSTETH_ETH_DTO,
        WEETH_ETH: WEETH_ETH_DTO,
        WBTC_ETH:WBTC_ETH_DTO,
        SFRXETH_ETH: SFRXETH_ETH_DTO, 
        TBTC_ETH: TBTC_ETH_DTO, 
        AAVE_ETH: AAVE_ETH_DTO,
        CBBTC_ETH: CBBTC_ETH_DTO


    }
}

