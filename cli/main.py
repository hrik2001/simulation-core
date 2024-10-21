import argparse
import datetime
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from external_market import ExternalMarket
from lmfit.models import ConstantModel, StepModel
from plotting import plot_regression, plot_simple
from quotes import get_quotes
from scipy.interpolate import BSpline, make_smoothing_spline

# Add '../core' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.dex_quotes.DTO import NAME_TO_ADDRESS_PER_NETWORK, TOKEN_DTOs

LIQUIDATION_BONUS = 0.075
PAGE_SIZE = 1000
PAGE_SLEEP = 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A CLI tool to interact with the simulation backend"
    )
    subparser = parser.add_subparsers(dest="command", required=True)

    plot_subparser = subparser.add_parser("plot", help="Enable plotting mode")
    plot_subparser.add_argument(
        "--collateral",
        type=str,
        required="plot",
        help="Collateral asset coingecko name",
    )
    plot_subparser.add_argument(
        "--debt", type=str, required="plot", help="Debt asset coingecko name"
    )
    plot_subparser.add_argument(
        "--timestamp",
        type=str,
        required=False,
        help="Approximate unix timestamp (accepts 'now' for latest timestamp)",
    )
    plot_subparser.add_argument(
        "--network",
        type=str,
        required="plot",
        help="Network",
        choices=["ethereum", "arbitrum", "optimism"],
    )
    plot_subparser.add_argument(
        "--plot-type",
        type=str,
        required="plot",
        help="Plot type",
        choices=["simple", "regression"],
    )

    list_subparser = subparser.add_parser(
        "list", help="List supported collateral and debt assets per network"
    )

    args = parser.parse_args()

    if args.command == "list":
        for network, assets in NAME_TO_ADDRESS_PER_NETWORK.items():
            print(f"> {network}")
            for asset_name in assets:
                print(f"    > {asset_name}")
        quit()

    if args.collateral not in NAME_TO_ADDRESS_PER_NETWORK[args.network]:
        print(f"{args.collateral} is not a supported collateral asset")
        quit()
    collateral_token_address = NAME_TO_ADDRESS_PER_NETWORK[args.network][
        args.collateral
    ]

    if args.debt not in NAME_TO_ADDRESS_PER_NETWORK[args.network]:
        print(f"{args.debt} is not a supported debt asset")
        quit()
    debt_token_address = NAME_TO_ADDRESS_PER_NETWORK[args.network][args.debt]

    print(f"Collateral asset: {args.collateral} ({collateral_token_address})")
    print(f"Debt asset: {args.debt} ({debt_token_address})")

    unix_timestamp = None
    if args.timestamp != None:
        if (
            args.timestamp == "now"
        ):  # compute unix timestamp in a platform-independent way
            unix_timestamp = int(
                (
                    datetime.datetime.now(datetime.timezone.utc)
                    - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
                ).total_seconds()
            )
        else:
            try:
                unix_timestamp = int(args.timestamp)
            except:
                print(
                    "not a valid timestamp (value values are 'now' or a unix timestamp as an integer')"
                )
                unix_timestamp = int(
                    (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
                    ).total_seconds()
                )

    quotes = get_quotes(
        collateral_token_address, debt_token_address, PAGE_SIZE, PAGE_SLEEP
    )

    capitalized_network_name = args.network.capitalize()
    collateral_token = TOKEN_DTOs[capitalized_network_name][collateral_token_address]
    debt_token = TOKEN_DTOs[capitalized_network_name][debt_token_address]

    market = ExternalMarket((collateral_token, debt_token))
    market.fit(quotes)

    if args.plot_type == "simple":
        plot_simple(
            quotes, collateral_token, debt_token, unix_timestamp, LIQUIDATION_BONUS
        )
    elif args.plot_type == "regression":
        plot_regression(quotes, 0, 1, market, scale="log")
