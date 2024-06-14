"""
Utils to initiate a pipeline
"""

from typing import List

from ..caching import cache
from ..models.asset import Asset
from ..models.chain import Chain
from ..entities.chain import ethereum, base
from ..models.time import SimulationTime
from ..pricing.historical_pricing import historical_get_price
from ..gas.gas import get_gas_owlracle_usd, get_gas_owlracle_eth
import requests


def create_market_price_feed(
    assets: List[Asset],
    numeraire: Asset,
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
            context[i][current_timestamp] = historical_get_price(
                i,
                numeraire,
                target_timestamp=current_timestamp,
            )
    return context


def create_gas_feed_usd(
    chain: Chain,
    start_timestamp: int,
    end_timestamp: int,
    numeraire_decimals: int,
    timestep: int = 3600,
):
    """
    Creates a cached gas price feed to prevent multiple network calls
    TODO: sleep param to not exhaust the coingecko api, could be an optional field
    """
    context = {}
    current_timestamp = start_timestamp

    for current_timestamp in filter(
        lambda x: x <= end_timestamp,
        range(start_timestamp, end_timestamp + timestep, timestep),
    ):
        context[current_timestamp] = get_gas_owlracle_usd(
            chain,
            target_timestamp=current_timestamp,
            numeraire_decimals=numeraire_decimals,
        )

    return context


def create_gas_feed_eth(
    chain: Chain, start_timestamp: int, end_timestamp: int, numeraire_decimals: int
):
    """
    Creates a cached gas price feed to prevent multiple network calls
    TODO: sleep param to not exhaust the coingecko api, could be an optional field
    """
    context = {}
    current_timestamp = start_timestamp

    for current_timestamp in filter(
        lambda x: x <= end_timestamp,
        range(start_timestamp, end_timestamp + timestep, timestep),
    ):
        context[current_timestamp] = get_gas_owlracle_eth(
            chain,
            target_timestamp=current_timestamp,
            numeraire_decimals=numeraire_decimals,
        )

    return context


def create_oracle_price_feed(
    assets: List[Asset],
    chain: Chain,
    numeraire: Asset,
    start_timestamp: int,
    end_timestamp: int,
):
    context = {}
    for asset in assets:
        if chain == ethereum or chain == base:
            context[asset] = cache.get_cached_chainlink(
                asset=asset.symbol.lower(),
                chain=chain,
                numeraire=numeraire.symbol.lower(),
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            )
    return context
