import os
from time import sleep

import requests
from dotenv import load_dotenv

from ..caching import cache
from ..exceptions import HistoricalSpotPriceNotFoundError
from ..models.asset import (Asset, ConcentratedLiquidityAsset,
                            SimCoreUniswapLPPosition)
from ..univ3.utils import get_value_of_lp, initiate_liquidity_position

load_dotenv()

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", None)
DEXGURU_API_KEY = os.getenv("DEXGURU_API_KEY", None)
COINGECKO_WINDOW_HOURS = 3


class HistoricalPriceStrategyMethods:
    """
    Strategy class where all the possible historical price fetching strategies are stored
    All the strategies must have a common interface

    TODO: implement an abstract base class to specify and validate for regression testing
    """

    @staticmethod
    def coingecko_strategy(
        asset: Asset,
        numeraire: Asset | str,
        *,
        target_timestamp: int,
        **kwargs,
    ):
        crypto_symbol = asset.pricing_metadata.metadata["coingecko_id"]
        numeraire_symbol = numeraire.pricing_metadata.metadata["coingecko_vs_currency"]
        window_hours = kwargs.get("window_hours", COINGECKO_WINDOW_HOURS)
        from_timestamp = target_timestamp - (window_hours * 3600)
        to_timestamp = target_timestamp + (window_hours * 3600)

        if COINGECKO_API_KEY is None:
            url = f"https://api.coingecko.com/api/v3/coins/{crypto_symbol}/market_chart/range?&vs_currency={numeraire_symbol}&precision=6&from={from_timestamp}&to={to_timestamp}"
        else:
            url = f"https://pro-api.coingecko.com/api/v3/coins/{crypto_symbol}/market_chart/range?&vs_currency={numeraire_symbol}&precision=6&from={from_timestamp}&to={to_timestamp}&x_cg_pro_api_key={COINGECKO_API_KEY}"

        data = cache.cached_request_get(url)

        if data:
            prices = data["prices"]

            # Find the timestamps within the time window
            target_timestamp_ms = target_timestamp * 1000
            sorted_timestamps_ms = sorted(
                enumerate(prices), key=lambda x: abs(x[1][0] - target_timestamp_ms)
            )
            try:
                # print(sorted_timestamps_ms[0][1][1])
                return sorted_timestamps_ms[0][1][1]
            except IndexError:
                raise HistoricalSpotPriceNotFoundError("Pricing not available")
        else:
            raise HistoricalSpotPriceNotFoundError(
                f"Failed to retrieve data from the API. Status code: 404: {crypto_symbol} @ {target_timestamp}\nTried to query {url}"
            )

    @staticmethod
    def dexguru_strategy(
        asset: Asset,
        numeraire: Asset | str,
        *,
        target_timestamp: int,
        **kwargs,
    ):
        address = asset.contract_address
        chain = [
            (
                "eth"
                if asset.chain.name.lower() == "ethereum"
                else asset.chain.name.lower()
            )
        ][0]
        window_hours = kwargs.get("window_hours", COINGECKO_WINDOW_HOURS)
        from_timestamp = target_timestamp - (window_hours * 3600)
        to_timestamp = target_timestamp + (window_hours * 3600)

        if DEXGURU_API_KEY is None:
            raise "DEXGURU_API_KEY Missing"
        else:
            base_url = "https://api.dev.dex.guru/v1/tradingview/history"
            params = {
                "symbol": f"{str(address)}-{str(chain)}_USD",
                "resolution": str(int(5)),
                "from": from_timestamp,
                "to": to_timestamp,
                "currencyCode": "USD",
            }
            headers = {"accept": "application/json", "api-key": DEXGURU_API_KEY}

            # response = requests.get(base_url, params=params, headers=headers)
            response = cache.cached_request_get(
                base_url, params=params, headers=headers
            )

        result = response

        # Find the timestamps within the time window
        print(f"LOG:: {result}")

        closest_index = min(
            range(len(result["t"])),
            key=lambda x: abs(result["t"][x] - target_timestamp),
        )
        try:
            avg_price = (result["o"][closest_index] + result["c"][closest_index]) / 2
            print(avg_price)
            return avg_price
        except IndexError:
            raise HistoricalSpotPriceNotFoundError("Pricing not available")

    def defillama_strategy(
        asset: Asset, numeraire: Asset | str, *, target_timestamp: int, **kwargs
    ):
        name_mapping = {8453: "base", 1: "ethereum"}
        timestamp = int(target_timestamp)
        chain_name = name_mapping[asset.chain.chain_id]
        url = f"https://coins.llama.fi/prices/historical/{timestamp}/{chain_name}:{asset.contract_address}"
        data = cache.cached_request_get(url)
        if not data["is_internally_cached"]:
            sleep(1)
        price = data["coins"][f"{chain_name}:{asset.contract_address}"]["price"]
        if numeraire == "usd":
            return price
        else:
            return price / historical_get_price(
                numeraire, "usd", target_timestamp=target_timestamp
            )
        # timestamp = datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)


def historical_get_price(
    asset: Asset,
    numeraire: Asset | str,
    *,
    target_timestamp: int,
    **kwargs,
):
    """
    Calls class method that matches the strategy of an asset
    """
    if asset.pricing_metadata.strategy is None:
        asset.pricing_metadata.strategy = "defillama_strategy"
    if not isinstance(asset, SimCoreUniswapLPPosition):
        return getattr(HistoricalPriceStrategyMethods, asset.pricing_metadata.strategy)(
            asset,
            numeraire,
            target_timestamp=target_timestamp,
            **kwargs,
        )
    else:
        # if asset.position.liquidity_estimate is None:
        # (
        # asset.position.liquidity_estimate,
        # asset.position.lower_price,
        # asset.position.upper_price,
        # _,
        # _,
        # ) = initiate_liquidity_position(
        # asset.position.usd_value_invested,
        # historical_get_price(
        # asset.token0, numeraire, target_timestamp=target_timestamp
        # ),
        # historical_get_price(
        # asset.token1, numeraire, target_timestamp=target_timestamp
        # ),
        # asset.position.interval_spread,
        # )

        # getting price
        print(f"{asset.liquidity=} {asset.tickLower=} {asset.tickUpper=}")
        if int(asset.liquidity) == 0 or (
            asset.tickLower.startswith("-") or asset.tickLower.startswith("-")
        ):
            return 0
        return get_value_of_lp(
            int(asset.liquidity),
            1.001 ** float(asset.tickLower),
            1.001 ** float(asset.tickUpper),
            historical_get_price(
                asset.token0, numeraire, target_timestamp=target_timestamp
            ),
            historical_get_price(
                asset.token1, numeraire, target_timestamp=target_timestamp
            ),
        )
        # return get_value_of_lp(
        # asset.position.liquidity_estimate,
        # asset.position.lower_price,
        # asset.position.upper_price,
        # historical_get_price(
        # asset.token0, numeraire, target_timestamp=target_timestamp
        # ),
        # historical_get_price(
        # asset.token1, numeraire, target_timestamp=target_timestamp
        # ),
        # )
