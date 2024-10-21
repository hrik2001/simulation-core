import math
from typing import Dict, List

from arcadia.arcadiasim.exceptions import NotEnoughLiquidity
from arcadia.arcadiasim.models.arcadia import (AssetMetadata,
                                               AssetsInMarginAccount,
                                               AssetValueAndRiskFactors,
                                               AuctionInformation,
                                               LiquidationConfig,
                                               MarginAccount)
from arcadia.arcadiasim.models.asset import Asset
from arcadia.arcadiasim.models.time import SimulationTime


def calculate_asked_share(
    auction_information: AuctionInformation, asked_amounts: Dict[Asset, int]
) -> int:
    total_share = 0
    for asset, asked_amount in asked_amounts.items():
        metadata = auction_information.assets[asset]
        total_share += (asked_amount * metadata.share) // metadata.amount
    return total_share


def dry_run_update_portfolio_balance(
    auction_information: AuctionInformation, asked_amount: Dict[Asset, int]
):
    """
    Looks if successfully asset can be transferred or not

    raises NotEnoughLiquidity
    """
    # two loops to make sure updation doesn't occur in invalid cases
    for asset, asked_amount in asked_amount.items():
        if asked_amount > auction_information.assets[asset].current_amount:
            raise NotEnoughLiquidity


def update_portfolio_balance(
    auction_information: AuctionInformation, asked_amounts: Dict[Asset, int]
):
    """
    Looks if successfully asset can be transferred or not
    And updates AuctionInformation accordingly

    raises NotEnoughLiquidity
    """
    # two loops to make sure updation doesn't occur in invalid cases
    for asset, asked_amount in asked_amounts.items():
        if asked_amount > auction_information.assets[asset].current_amount:
            raise NotEnoughLiquidity

    for asset, asked_amount in asked_amounts.items():
        auction_information.assets[asset].current_amount -= asked_amount


def calculate_liquidation_value(
    account: MarginAccount, sim_time: SimulationTime, decimals: int
):
    total_value = 0
    for asset_in_margin_account in account.assets:
        asset = asset_in_margin_account.asset
        metadata = asset_in_margin_account.metadata
        total_value += (
            (
                (sim_time.get_price(asset) * metadata.current_amount)
                / (10**asset.decimals)
            )
            * metadata.risk_metadata.liquidation_factor
        ) * (10**decimals)
    return total_value


def is_liquidatable(account: MarginAccount, sim_time: SimulationTime, decimals: int):
    liquidation_value = calculate_liquidation_value(account, sim_time, decimals)
    # print(liquidation_value/(10**6), account.debt/(10**6))
    return (liquidation_value <= account.debt) and (liquidation_value != 0)


def is_account_fully_liquidated(auction_information: AuctionInformation):
    for i in list(auction_information.assets.values()):
        if i.current_amount != 0:
            return False
    return True


def prepare_assets_in_margin_account(
    assets: List[AssetsInMarginAccount], sim_time: SimulationTime
):
    total_value = 0
    values = {}
    return_context = {}

    for asset in assets:
        # TODO: optimize
        value = (
            asset.metadata.current_amount / (10**asset.asset.decimals)
        ) * sim_time.get_price(asset.asset)
        total_value += value
        values[asset.asset] = value

    for asset in assets:
        asset.metadata.share = int((values[asset.asset] / total_value) * 1e6)
        return_context[asset.asset] = asset.metadata

    return return_context


def calculate_bid_price(
    auction_information: AuctionInformation, asked_share: int, current_timestamp: int
) -> float:
    # Calculate the time passed since the auction started
    # time_passed = (current_timestamp - auction_information.start_time) * 10 ** 18
    time_passed = current_timestamp - auction_information.start_time

    # Cache minPriceMultiplier
    min_price_multiplier_ = auction_information.min_price_multiplier
    exponential_decay = math.pow((auction_information.base / (10**18)), time_passed)
    exponential_decay *= 10**18

    subtraction = auction_information.start_price_multiplier - min_price_multiplier_

    price = (
        auction_information.start_debt
        * asked_share
        * (exponential_decay * (subtraction) + 10**18 * (min_price_multiplier_))
    ) / 10**28
    return price
