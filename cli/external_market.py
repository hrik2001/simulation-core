"""
Provides the `ExternalMarket` class for modeling
swaps in external liquidity venues.
"""
from __future__ import annotations
import os, sys
from collections import defaultdict
from itertools import permutations
from functools import cached_property
from typing import Tuple, Dict, TYPE_CHECKING, List
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

# Add '../core' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from core.dex_quotes.DTO import TokenDTO

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

    @cached_property
    def name(self) -> str:
        """Market name."""
        return f"External Market ({self.coins[0].symbol}, {self.coins[1].symbol})"

    @cached_property
    def coin_names(self) -> List[str]:
        """List of coin names in the market."""
        return [c.name for c in self.coins]

    @cached_property
    def coin_symbols(self) -> List[str]:
        """List of coin symbols in the market."""
        return [c.symbol for c in self.coins]

    @cached_property
    def coin_addresses(self) -> List[str]:
        """List of coin addresses in the market."""
        return [c.address for c in self.coins]

    @cached_property
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


    def fit_bounded(self, quotes: pd.DataFrame, num_bins: int = 100, iqr_factor: float = 1.5) -> None:
        """
        Fit three different IsotonicRegressions based on quartiles of price impact
        at various price impact levels (filtered by bins) with outlier filtering.

        Parameters
        ----------
        quotes : pd.DataFrame
            DataFrame of 1inch quotes.
        num_bins : int
            Number of bins to segment the data for quartile calculation.
        iqr_factor : float
            Multiplier for the IQR to determine outliers. Default is 1.5.
        """
        for i, j in self.pair_indices:
            quotes_ = quotes.loc[(self.coin_addresses[i].lower(), self.coin_addresses[j].lower())]

            # Bin the input amounts
            quotes_['bin'] = pd.qcut(quotes_['in_amount'], num_bins, duplicates='drop')

            # Initialize lists to store the binned data
            x_lower, y_lower = [], []
            x_central, y_central = [], []
            x_upper, y_upper = [], []

            # Iterate through each bin to calculate quartiles and filter outliers
            for bin_name, group in quotes_.groupby('bin'):
                x_bin = group['in_amount'].median()
                
                # Calculate IQR for price impact
                q1 = group['price_impact'].quantile(0.25)
                q3 = group['price_impact'].quantile(0.75)
                iqr = q3 - q1
                
                # Determine bounds for filtering
                lower_bound = q1 - iqr_factor * iqr
                upper_bound = q3 + iqr_factor * iqr
                
                # Filter out outliers
                filtered_group = group[(group['price_impact'] >= lower_bound) & (group['price_impact'] <= upper_bound)]
                
                # Calculate quartiles on filtered data
                y_lower.append(filtered_group['price_impact'].quantile(0.25))
                y_central.append(filtered_group['price_impact'].quantile(0.50))
                y_upper.append(filtered_group['price_impact'].quantile(0.75))

                # # Filter for different quartile ranges
                # lower_quantile_group = filtered_group[filtered_group['price_impact'] <= filtered_group['price_impact'].quantile(0.25)]
                # central_quantile_group = filtered_group[(filtered_group['price_impact'] > filtered_group['price_impact'].quantile(0.25)) &
                #                                         (filtered_group['price_impact'] <= filtered_group['price_impact'].quantile(0.75))]
                # upper_quantile_group = filtered_group[filtered_group['price_impact'] > filtered_group['price_impact'].quantile(0.75)]

                # # Append the median values to each list
                # y_lower.append(lower_quantile_group['price_impact'].median())
                # y_central.append(central_quantile_group['price_impact'].median())
                # y_upper.append(upper_quantile_group['price_impact'].median())
                
                x_lower.append(x_bin)
                x_central.append(x_bin)
                x_upper.append(x_bin)

            # Fit the lower bound model
            lower_bound_model = IsotonicRegression(increasing=True)
            lower_bound_model.fit(x_lower, y_lower)
            self.models[i][f"{j}_lower"] = lower_bound_model

            # Fit the central prediction model
            central_model = IsotonicRegression(increasing=True)
            central_model.fit(x_central, y_central)
            self.models[i][j] = central_model

            # Fit the upper bound model
            upper_bound_model = IsotonicRegression(increasing=True)
            upper_bound_model.fit(x_upper, y_upper)
            self.models[i][f"{j}_upper"] = upper_bound_model



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
            #quotes_ = quotes.loc[(self.coin_addresses[i].lower(), self.coin_addresses[j].lower())]

            x = quotes["in_amount"].values.reshape(-1, 1)
            y = quotes["price_impact"].values

            model = IsotonicRegression(y_min=0, y_max=1, increasing=True, out_of_bounds="clip")
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
