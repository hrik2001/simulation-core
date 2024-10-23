from ..entities.chain import base, ethereum
from ..models.chain import Chain
from ..models.arcadia import AuctionInformation
from ..models.asset import Asset
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import os
from typing import List, Dict, Any
from ..entities.asset import base, ethereum
from ..caching import cache

## TO_DO
# - Create an ETH Asset in Entities


load_dotenv()

OWLRACLE_WINDOW_HOURS = 3


def get_gas_owlracle_usd(
    chain: Chain, *, target_timestamp: int, numeraire_decimals: int, **kwargs
):
    window_hours = kwargs.get("window_hours", OWLRACLE_WINDOW_HOURS)
    from_timestamp = target_timestamp - (window_hours * 3600)
    to_timestamp = target_timestamp + (window_hours * 3600)
    target_datetime = datetime.fromtimestamp(target_timestamp).replace(
        tzinfo=timezone.utc
    )
    api_key = os.getenv("OWLRACLE_API_KEY", None)
    if api_key is None:
        raise Exception("Owlracle API key not available")
    if chain == base:
        # api_response = requests.get(
        # f"https://api.owlracle.info/v4/base/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        # ).json()
        api_response = cache.cached_request_get(
            f"https://api.owlracle.info/v4/base/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        )
    elif chain == ethereum:
        # api_response = requests.get(
        # f"https://api.owlracle.info/v4/eth/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        # ).json()
        api_response = cache.cached_request_get(
            f"https://api.owlracle.info/v4/eth/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        )
    nearest_entry = min(
        api_response["candles"],
        key=lambda x: abs(
            target_datetime - datetime.fromisoformat(x["timestamp"][:-1] + "+00:00")
        ),
    )
    token_price = (
        nearest_entry["tokenPrice"]["open"] + nearest_entry["tokenPrice"]["close"]
    ) / 2
    print(
        ((nearest_entry["gasPrice"]["high"] / 1e9) * token_price)
        * (10**numeraire_decimals)
    )
    return ((nearest_entry["gasPrice"]["high"] / 1e9) * token_price) * (
        10**numeraire_decimals
    )


def get_gas_owlracle_eth(
    chain: Chain, *, target_timestamp: int, numeraire_decimals: int, **kwargs
):
    window_hours = kwargs.get("window_hours", OWLRACLE_WINDOW_HOURS)
    from_timestamp = target_timestamp - (window_hours * 3600)
    to_timestamp = target_timestamp + (window_hours * 3600)
    target_datetime = datetime.fromtimestamp(target_timestamp).replace(
        tzinfo=timezone.utc
    )
    api_key = os.getenv("OWLRACLE_API_KEY", None)
    if api_key is None:
        raise Exception("Owlracle API key not available")
    if chain == base:
        api_response = requests.get(
            f"https://api.owlracle.info/v4/base/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        ).json()
    elif chain == ethereum:
        api_response = requests.get(
            f"https://api.owlracle.info/v4/eth/history?apikey={api_key}&from={from_timestamp}&to={to_timestamp}&timeframe=1h&page=1&tokenprice=true"
        ).json()
    nearest_entry = min(
        api_response["candles"],
        key=lambda x: abs(
            target_datetime - datetime.fromisoformat(x["timestamp"][:-1] + "+00:00")
        ),
    )
    return ((nearest_entry["gasPrice"]["high"] / 1e9)) * (10**numeraire_decimals)
