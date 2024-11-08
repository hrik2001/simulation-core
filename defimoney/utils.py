from __future__ import annotations
from core.dex_quotes.DTO import TOKEN_DTOs, STABLES, TokenDTO, COLLATERAL, USDC_OP_DTO, USDT_OP_DTO, USDC_ARB_DTO, USDT_ARB_DTO, WETH_OP_DTO, WETH_ARB_DTO, WBTC_OP_DTO, WBTC_ARB_DTO, WSTETH_OP_DTO, ARB_DTO, GMX_DTO, RDNT_DTO, WSTETH_ARB_DTO, PENDLE_DTO, OP_DTO, VELO_DTO, USDC_BASE_DTO, WETH_BASE_DTO, CBBTC_BASE_DTO, CBETH_BASE_DTO, WSTETH_BASE_DTO
"""
Provides the `ExternalMarket` class for modeling
swaps in external liquidity venues.
"""
from collections import defaultdict
from itertools import permutations
from functools import cached_property
from typing import Tuple, Dict, TYPE_CHECKING, List
import numpy as np
import pandas as pd
from web3 import Web3
from sklearn.isotonic import IsotonicRegression


import time
import os
import numpy as np
from core.utils import price_defillama
from core.models import Chain
from typing import List
from django.db.models import Q, F, Min, Max
from django.db.models.functions import Lower
from core.models import DexQuote
from django.db.models.query import QuerySet
import pandas as pd




class ExternalMarket:
    """
    A representation of external liquidity venues
    for relevant tokens. These markets are statistical
    models trained on 1inch quotes. We are currently
    using an IsotonicRegression to model fees and price impact.

    Note
    ----
    We always assume that the External Market is *at*
    the market price.
    """

    def __init__(
        self,
        coins: Tuple[TokenDTO, TokenDTO],
    ):
        n = len(coins)
        assert n == 2

        self.coins = coins
        self.pair_indices = list(permutations(range(n), 2))
        self.n = n
        self.prices: Dict[int, Dict[int, float]] | None = None
        self.models: Dict[int, Dict[int, IsotonicRegression]] = defaultdict(dict)

    def name(self) -> str:
        """Market name."""
        return f"External Market ({self.coins[0].symbol}, {self.coins[1].symbol})"

    def coin_names(self) -> List[str]:
        """List of coin names in the market."""
        return [c.name for c in self.coins]

    def coin_symbols(self) -> List[str]:
        """List of coin symbols in the market."""
        return [c.symbol for c in self.coins]

    @property
    def coin_addresses(self) -> List[str]:
        """List of coin addresses in the market."""
        return [c.address for c in self.coins]

    def coin_decimals(self) -> List[int]:
        """List of coin decimals in the market."""
        return [c.decimals for c in self.coins]

    def price(self, i: int, j: int) -> float:
        """Get the price of token i in terms of token j."""
        if not self.prices:
            raise ValueError("Prices not set for External Market.")
        return self.prices[i][j]

    def update_price(self, prices: "PairwisePricesType") -> None:
        """
        Update the markets prices.

        Parameters
        ----------
        prices : PairwisePricesType
            prices[token1][token2] is the price of token1 in terms of token2.
            Notice that token1, token2 are addresses.
        """
        self.prices = {
            self.coin_addresses.index(token_in): {
                self.coin_addresses.index(token_out): price
                for token_out, price in token_out_prices.items()
                if token_out in self.coin_addresses
            }
            for token_in, token_out_prices in prices.items()
            if token_in in self.coin_addresses
        }

    def fit(self, quotes: pd.DataFrame) -> None:
        """
        Fit an IsotonicRegression to the price impact data for each
        pair of tokens.

        Parameters
        ----------
        quotes : pd.DataFrame
            DataFrame of 1inch quotes.
        """
        for i, j in self.pair_indices:
            # print(f"{self.coin_addresses[i].lower()=} {self.coin_addresses[j].lower()=}")
            quotes_ = quotes.loc[(self.coin_addresses[i].lower(), self.coin_addresses[j].lower())] #.sort_values(by='price_impact', ascending=True)

            x = quotes_["in_amount"].values.reshape(-1, 1)
            y = quotes_["price_impact"].values

            model = IsotonicRegression(
                y_min=0, y_max=1, increasing=True, out_of_bounds="clip"
            )
            model.fit(x, y)
            self.models[i][j] = model

    def trade(self, i: int, j: int, size: int) -> int:
        """
        Execute a trade on the external market using
        the current price.

        Parameters
        ----------
        i : int
            The index of the token_in.
        j : int
            The index of the token_out.
        size : int
            The amount of token_in to sell for each trade.

        Returns
        -------
        int
            The amount of token j the user gets out.

        Note
        ----
        The market's fee should already be incorporated into the
        price impact estimation.
        """
        assert self.prices, "Prices not set for External Market."
        out = size * self.prices[i][j] * (1 - self.price_impact(i, j, size))
        # Correct for decimals
        out = out / 10 ** self.coin_decimals[i] * 10 ** self.coin_decimals[j]
        return int(out)

    def price_impact(self, i: int, j: int, size: int) -> float:
        """
        We model price impact using an IsotonicRegression.

        Parameters
        ----------
        i : int
            The index of the token_in.
        j : int
            The index of the token_out.
        size : Any
            The amount of token_in to sell.

        Returns
        -------
        int or List[int]
            The price_impact for given trade.
        """
        model = self.models[i][j]
        x = np.clip(
            np.array(size).reshape(-1, 1).astype(float), model.X_min_, model.X_max_
        )
        return float(model.f_(x)[0][0])  # NOTE this is way faster than `predict`

    def price_impact_many(self, i: int, j: int, size: np.ndarray) -> np.ndarray:
        """
        Predict price impact on many obs.
        """
        model = self.models[i][j]
        if size.ndim == 1:
            size = size.reshape(-1, 1)
        return model.predict(size)

    def get_max_trade_size(self, i: int, j: int, out_balance_perc: float = 0.01) -> int:
        """Returns the maximum trade size observed when fitting quotes."""
        model = self.models[i][j]
        return int(model.X_max_ * (1 - out_balance_perc))

    def __repr__(self) -> str:
        return self.name



def get_stable_quotes(target: TokenDTO, stables: List[str]) -> pd.DataFrame:
    # Convert all input addresses to lowercase
    target_address = target.address.lower()
    stables_lower = [stable.address.lower() for stable in stables]

    # Create the query
    quotes = DexQuote.objects.annotate(
        src_lower=Lower('src'),
        dst_lower=Lower('dst')
    ).filter(
        (Q(src_lower__in=stables_lower) & Q(dst_lower=target_address)) |
        (Q(dst_lower__in=stables_lower) & Q(src_lower=target_address))
    )

    # return pd.DataFrame(quotes.values())
    result_df = pd.DataFrame(quotes.values())

    # df_black_swan = pd.read_csv("raw_data.csv")
    # df_black_swan["src_lower"] = df_black_swan["src"].str.lower()
    # df_black_swan["dst_lower"] = df_black_swan["dst"].str.lower()
    # # df_black_swan[(df_black_swan["src_lower"].isin(stables_lower) & df_black_swan["dst_lower"]==target_address) | (df_black_swan["src_lower"]==target_address & df_black_swan["dst_lower"].isin(stables_lower))]
    # stables_str = ", ".join(f"'{s}'" for s in stables_lower)

    # query_str = f"(src_lower in ({stables_str}) and dst_lower == @target_address) or (src_lower == @target_address and dst_lower in ({stables_str}))"

    # result = df_black_swan.query(query_str)
    # print(f"{len(result)=} {len(df_black_swan)=}")
    # result_df = pd.concat([result, result_df])

    return result_df

def find_debt_ceiling(market: ExternalMarket, df):
    i = 1
    j = 0
    df['in_amount'] = pd.to_numeric(df['in_amount'], errors='coerce')
    # Drop rows with NaN values in 'in_amount' (if any were introduced by coercion)
    df = df.dropna(subset=['in_amount'])
    x = np.geomspace(df["in_amount"].min(), df["in_amount"].max(), 100)
    y = market.price_impact_many(i, j, x) * 100
    in_token = market.coins[i]
    out_token = market.coins[j]
    sub_10_slippage_idx = np.where((y > 3) & (y < 20))[0]
    x_sub_10 = x[sub_10_slippage_idx]
    y_sub_10 = y[sub_10_slippage_idx]
    print(y_sub_10)
    
    # Find the kink in the curve using the second derivative
    dydx = np.gradient(y_sub_10)
    d2ydx2 = np.gradient(dydx)
    
    # Find the index of the maximum point in the second derivative
    peak_idx = np.argmax(np.abs(d2ydx2))
    debt_ceiling_amount = x_sub_10[peak_idx] / 10**in_token.decimals
    # debt_ceiling_impact = y_sub_10[peak_idx]
    return debt_ceiling_amount

def get_llamma_debt(dto: TokenDTO, contract_address: str):
    w3 = Web3(Web3.HTTPProvider(Chain.objects.get(chain_name__iexact=dto.network.network).rpc))
    contract_address = Web3.to_checksum_address(contract_address)
    contract_abi = [
        {
            "stateMutability": "view",
            "type": "function",
            "name": "total_debt",
            "inputs": [],
            "outputs": [{"name": "", "type": "uint256"}]
        }
    ]

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    return contract.functions.total_debt().call()


def collateral_debt_ceilings():
    # collateral = COLLATERAL[0]
    response = {
            WETH_OP_DTO: {"debt_ceiling": 450},
            WETH_ARB_DTO: {"debt_ceiling": 5400},
            WBTC_OP_DTO: {"debt_ceiling": 14},
            WBTC_ARB_DTO: {"debt_ceiling": 149},
            WSTETH_OP_DTO: {"debt_ceiling": 357},
            WSTETH_ARB_DTO: {"debt_ceiling": 1607},
            OP_DTO: {"debt_ceiling": 1119402},
            ARB_DTO: {"debt_ceiling": 12244897},
            VELO_DTO: {"debt_ceiling": 5000000},
            GMX_DTO: {"debt_ceiling": 120000},
            PENDLE_DTO: {"debt_ceiling": 286738},
            RDNT_DTO: {"debt_ceiling": 70257610},
            WETH_BASE_DTO: {"debt_ceiling": 8237.72},
            CBBTC_BASE_DTO: {"debt_ceiling": 209.82},
            CBETH_BASE_DTO: {"debt_ceiling": 2778.25},
            WSTETH_BASE_DTO: {"debt_ceiling": None}
    }
    # for collateral in COLLATERAL:
        # flag = True
        # try:
            # collateral_dto = TOKEN_DTOs["Optimism"][collateral]
            # chain = "optimism"
        # except KeyError:
            # try:
                # collateral_dto = TOKEN_DTOs["Arbitrum"][collateral]
                # chain = "arbitrum"
            # except KeyError:
                # print("Asset is neither arbitrum nor optimism asset")
                # flag = False
                
        
        # if not flag:
            # continue
        
    for collateral_dto in response.keys():
        chain = collateral_dto.network.network.lower()
        collateral = collateral_dto.address
        print(f"Trying {collateral_dto.symbol} {collateral_dto.address} on {chain}")
        # df_collateral = pd.DataFrame(get_stable_quotes(collateral_dto, [USDT_ARB_DTO, USDC_ARB_DTO, USDT_OP_DTO, USDC_OP_DTO]).values())
        df_collateral = get_stable_quotes(collateral_dto, [USDT_ARB_DTO, USDC_ARB_DTO, USDT_OP_DTO, USDC_OP_DTO, USDC_BASE_DTO])
        df_backup = df_collateral.copy(deep=True)
        df_collateral['src'] = df_collateral['src_lower']
        df_collateral['dst'] = df_collateral['dst_lower']
        df_collateral.loc[df_collateral['src_lower'] != collateral.lower(), 'src'] = USDC_ARB_DTO.address.lower()
        df_collateral.loc[df_collateral['dst_lower'] != collateral.lower(), 'dst'] = USDC_ARB_DTO.address.lower()

        # print(f"{df_collateral['src'].unique()=}")
        # print(f"{df_collateral['dst'].unique()=}")

        df_collateral.set_index(["src", "dst"], inplace=True)
        pair = (USDC_ARB_DTO, collateral_dto)
        in_token = pair[1]
        out_token = pair[0]
        market = ExternalMarket(pair)
        market.fit(df_collateral)
        try:
            dc = find_debt_ceiling(market, df_collateral)
        except ValueError as e:
            print(f"{collateral_dto.symbol} {chain} MESSED UP")
            continue


        time.sleep(1)
        # print(f"{collateral_dto.symbol} {chain} {dc} {dc_usd}")
        previous_ceiling = response[collateral_dto]["debt_ceiling"]
        if previous_ceiling is not None:
            if (abs(previous_ceiling - dc) / previous_ceiling) < 0.5:
                response[collateral_dto] = {"debt_ceiling": dc}
        else:
            response[collateral_dto] = {"debt_ceiling": dc}


    for dto, ceiling in response.items():
        ceiling = ceiling["debt_ceiling"]
        collateral = dto.address
        chain = dto.network.network.lower()
        if collateral == "0x3082CC23568eA640225c2467653dB90e9250AaA0":
            chain = "coingecko"
            collateral = "radiant"
        price = price_defillama(chain, collateral)
        dc_usd = price * ceiling
        response[dto]["debt_ceiling_usd"] = dc_usd
        response[dto]["actual_debt"] = None

    llammas = {
        WETH_ARB_DTO: "0xe38fb572099a8fdb51e0929cb2b439d0479fc43e",
        WBTC_ARB_DTO: "0xb745f12ecf271484c79d3999ca12164fe1c4e5f9",
        WSTETH_ARB_DTO: "0xE927e8B43Da90f017b146Eff5f99515372630DD1",
        ARB_DTO: "0xec70ac48d2cc382987a176f64fe74d77d010f9d1",
        # GMX_DTO: "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
        PENDLE_DTO: "0xFF75fa72bbc5DB02FceB948901614A1155925592",
        RDNT_DTO: "0xE304eF44F4240E44d0A8E954c22e5007a93a4378",
        OP_DTO: "0x13aa7dBB49d414A321b403EabB1B4231e61C7b29",
        WETH_OP_DTO: "0xd74a1f6b44395cf8c4833df5bc965c6c2b567476",
        WBTC_OP_DTO: "0xc82b4c656ba6aa4a2ef6bfe6b511d206c93b405b",
        WSTETH_OP_DTO: "0xfc6ec1f94f2ffce0f0bcb79592d765abd3e1baef",
        WETH_BASE_DTO: "0xA929A836148E0635aB5EDf5B474d664601aDD2cE",
        CBETH_BASE_DTO: "0xdf887F7a76744df87CF8111349657688E73257dc",
        CBBTC_BASE_DTO: "0xA86e8d5ed6F07DAb21C44e55e8576742760a7aFB",
        GMX_DTO: "0xa8ED217624218a4c65e6d577A26D7810E2f8f790",
        VELO_DTO: "0x7e0242FCAA2d4844C6fF0769fac9c9cF5f8DE2d6",
        WSTETH_BASE_DTO: "0x72765c346e139eF09d104955dD0bd3d4F45441bF"

    }


    final_response = dict()
    for dto, ceiling in response.items():
        if dto in llammas:
            print(f"{dto=}")
            ceiling["actual_debt"] = get_llamma_debt(dto, llammas[dto])/1e18
        final_response[f"{dto.symbol.lower()}-{dto.network.network.lower()}"] = ceiling
        
    return final_response
 
