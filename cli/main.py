import click
import sys
import os
import matplotlib.pyplot as plt
import datetime
from scipy.interpolate import make_smoothing_spline, BSpline
import numpy as np
from lmfit.models import StepModel, ConstantModel
from external_market import ExternalMarket
from plotting import plot_simple, plot_regression
from quotes import get_quotes

# Add '../core' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.dex_quotes.DTO import TOKEN_DTOs, NAME_TO_ADDRESS_PER_NETWORK

LIQUIDATION_BONUS = 0.075
PAGE_SIZE = 1000
PAGE_SLEEP = 1


def validate_asset(ctx, param, value, network):
    """Validate that an asset exists in the specified network."""
    if value not in NAME_TO_ADDRESS_PER_NETWORK[network]:
        raise click.BadParameter(f"{value} is not a supported asset for network {network}")
    return value


def get_unix_timestamp(timestamp_str):
    """Convert timestamp string to unix timestamp."""
    if timestamp_str is None:
        return None

    if timestamp_str.lower() == "now":
        return int(
            (
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            ).total_seconds()
        )

    try:
        return int(timestamp_str)
    except ValueError:
        raise click.BadParameter("Timestamp must be 'now' or a unix timestamp as an integer")


@click.group()
def cli():
    """A CLI tool to interact with the simulation backend"""
    pass


@cli.command()
def list():
    """List supported collateral and debt assets per network"""
    for network, assets in NAME_TO_ADDRESS_PER_NETWORK.items():
        click.echo(f"> {network}")
        for asset_name in assets:
            click.echo(f"    > {asset_name}")


@cli.command()
@click.option("--collateral", required=True, help="Collateral asset coingecko name")
@click.option("--debt", required=True, help="Debt asset coingecko name")
@click.option("--network", required=True, type=click.Choice(["ethereum", "arbitrum", "optimism"]))
@click.option("--timestamp", required=False, help="Approximate unix timestamp (accepts 'now' for latest timestamp)")
@click.option("--plot-type", required=True, type=click.Choice(["simple", "regression"]))
def plot(collateral, debt, network, timestamp, plot_type):
    """Enable plotting mode"""
    # Validate assets for the given network
    validate_asset(None, None, collateral, network)
    validate_asset(None, None, debt, network)

    collateral_token_address = NAME_TO_ADDRESS_PER_NETWORK[network][collateral]
    debt_token_address = NAME_TO_ADDRESS_PER_NETWORK[network][debt]

    click.echo(f"Collateral asset: {collateral} ({collateral_token_address})")
    click.echo(f"Debt asset: {debt} ({debt_token_address})")

    unix_timestamp = get_unix_timestamp(timestamp)

    quotes = get_quotes(collateral_token_address, debt_token_address, PAGE_SIZE, PAGE_SLEEP)
    capitalized_network_name = network.capitalize()
    collateral_token = TOKEN_DTOs[capitalized_network_name][collateral_token_address]
    debt_token = TOKEN_DTOs[capitalized_network_name][debt_token_address]

    market = ExternalMarket((collateral_token, debt_token))
    market.fit(quotes)

    if plot_type == "simple":
        plot_simple(quotes, collateral_token, debt_token, unix_timestamp, LIQUIDATION_BONUS)
    elif plot_type == "regression":
        plot_regression(quotes, 0, 1, market, scale="log")


if __name__ == "__main__":
    cli()
