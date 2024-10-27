from .models import ERC20, UniswapLPPosition, Chain
from time import sleep
from .caching import cache
from .pricing.univ3 import get_value_of_lp, get_positions_details
from typing import List
from web3 import Web3
from arcadia.utils import erc20_to_pydantic
from arcadia.arcadiasim.models.asset import Asset, SimCoreUniswapLPPosition

COINGECKO_WINDOW_HOURS = 3
COINGECKO_API_KEY = ""
DEXGURU_API_KEY = ""
class HistoricalPriceStrategyMethods:
    """
    Strategy class where all the possible historical price fetching strategies are stored
    All the strategies must have a common interface

    TODO: implement an abstract base class to specify and validate for regression testing
    """

    @staticmethod
    def coingecko_strategy(
        asset: ERC20,
        numeraire: ERC20 | str,
        *,
        target_timestamp: int,
        **kwargs,
    ):
        crypto_symbol = asset.pricing_metadata["metadata"]["coingecko_id"]
        numeraire_symbol = numeraire.pricing_metadata["metadata"]["coingecko_vs_currency"]
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
                raise Exception("Pricing not available")
        else:
            raise Exception(
                f"Failed to retrieve data from the API. Status code: 404: {crypto_symbol} @ {target_timestamp}\nTried to query {url}"
            )

    @staticmethod
    def dexguru_strategy(
        asset: ERC20,
        numeraire: ERC20 | str,
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
            raise Exception("Pricing not available")

    def defillama_strategy(
        asset: ERC20, numeraire: ERC20 | str, *, target_timestamp: int, **kwargs
    ):

        name_mapping = {8453: "base", 1: "ethereum"}
        timestamp = int(target_timestamp)
        chain_name = name_mapping[asset.chain.chain_id]
        url = f"https://coins.llama.fi/prices/historical/{timestamp}/{chain_name}:{asset.contract_address}"
        data = cache.cached_request_get(url)
        if not data["is_internally_cached"]:
            sleep(1)
        # price = data["coins"][f"{chain_name}:{asset.contract_address}"]["price"]
        price = None
        for d in list(data["coins"].keys()):
            if d.lower() == f"{chain_name}:{asset.contract_address}".lower():
                price = data["coins"][d]["price"]
        if price is None:
            raise KeyError
        if numeraire == "usd":
            return price
        else:
            return price / historical_get_price(
                numeraire, "usd", target_timestamp=target_timestamp
            )
        # timestamp = datetime.fromtimestamp(timestamp).replace(tzinfo=timezone.utc)


def historical_get_price(
    asset: ERC20 | UniswapLPPosition,
    numeraire: ERC20 | str | UniswapLPPosition,
    *,
    target_timestamp: int,
    **kwargs,
):
    """
    Calls class method that matches the strategy of an asset
    """
    if asset.pricing_metadata == {}:
        asset.pricing_metadata["strategy"] = "defillama_strategy"
    if not isinstance(asset, UniswapLPPosition):
        return getattr(HistoricalPriceStrategyMethods, asset.pricing_metadata["strategy"])(
            asset,
            numeraire,
            target_timestamp=target_timestamp,
            **kwargs,
        )
    else:
        if asset.liquidity is None:
            w3 = Web3(Web3.HTTPProvider(asset.chain.rpc))
            position_details = get_positions_details(
                asset.contract_address,
                w3,
                int(asset.token_id)
            )
            asset.liquidity = str(position_details["liquidity"])
            asset.tickLower = str(position_details["tickLower"])
            asset.tickUpper = str(position_details["tickUpper"])
            asset.token1 = ERC20.objects.get(contract_address__iexact=position_details["token1"])
            asset.token0 = ERC20.objects.get(contract_address__iexact=position_details["token0"])
            asset.save()

        # getting price
        return get_value_of_lp(
            int(asset.liquidity),
            float(asset.tickLower),
            float(asset.tickUpper),
            historical_get_price(
                asset.token0, numeraire, target_timestamp=target_timestamp
            ),
            historical_get_price(
                asset.token1, numeraire, target_timestamp=target_timestamp
            ),
        )

def create_market_price_feed(
    assets: List[ERC20],
    numeraire: ERC20 | str,
    chain: Chain,
    start_timestamp: int,
    end_timestamp: int,
    timestep: int = 3600,
):
    """
    Creates a cached price feed to prevent multiple network calls
    TODO: sleep param to not exhaust the coingecko api, could be an optional field
    """
    context = {}
    for i in assets:
        context[i] = {}
    current_timestamp = start_timestamp
    for current_timestamp in filter(
        lambda x: x <= end_timestamp,
        range(start_timestamp, end_timestamp + timestep, timestep),
    ):
        for i in assets:
            i_pydantic = erc20_to_pydantic(i)
            context[i_pydantic][current_timestamp] = historical_get_price(
                i,
                numeraire,
                target_timestamp=current_timestamp,
            )
    return context

