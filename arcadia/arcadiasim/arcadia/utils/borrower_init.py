from collections import defaultdict
from typing import Dict, List

import numpy as np
import requests
from arcadiasim.entities.asset import cbETH, dai, rETH, usdbc, usdc, weth
from arcadiasim.models.arcadia import (AssetMetadata, AssetsInMarginAccount,
                                       AssetValueAndRiskFactors, Ranges)
from arcadiasim.models.asset import Asset, ConcentratedLiquidityAsset
from arcadiasim.models.borrower import BorrowerDetailsFromModel

from .borrower_debt_model import *


def borrower_init_arcadia_v1_short_term_cbETH_rETH(
    exposure: float,  # In terms of numeraire, normalized
    prices: Dict[Asset, float],
    collateral_per_asset: List[List[AssetsInMarginAccount]],
    numeraire: Asset,
) -> List[BorrowerDetailsFromModel]:
    debt_values = []
    while True:
        debt_values = borrow_model_arcadia_v1_short_term(len(collateral_per_asset))
        if np.sum(debt_values) <= exposure:
            break
        else:
            debt_values = []

    return_context = []

    for index, collateral_assets in enumerate(collateral_per_asset):
        collateral_value = 1 / (0.6 * 0.9 + 0.4 * 0.8) * debt_values[index]
        for i, asset_in_margin_account in enumerate(collateral_assets):
            weight = 0
            if asset_in_margin_account.asset == cbETH:
                weight = 0.6
            elif asset_in_margin_account.asset == rETH:
                weight = 0.4

            fixed_point_amount = (
                (collateral_value * weight)
                / prices[asset_in_margin_account.asset]
                * (10**asset_in_margin_account.asset.decimals)
            )
            collateral_per_asset[index][i].metadata.amount = fixed_point_amount
            collateral_per_asset[index][i].metadata.current_amount = fixed_point_amount

        return_context.append(
            BorrowerDetailsFromModel(
                **{
                    "debt": debt_values[index],
                    "collateral_value": collateral_value,
                }
            )
        )
    return return_context


def borrower_init_arcadia_v1_short_term_single_asset(
    exposure: Dict[Asset, int],  # In terms of numeraire, normalized
    prices: Dict[Asset, float],
    collateral_per_asset: List[List[AssetsInMarginAccount]],
    numeraire: Asset,
) -> List[BorrowerDetailsFromModel]:
    total_collateral_distribution = defaultdict(int)
    debt_values = []
    debt_values = borrow_model_arcadia_v1_short_term(len(collateral_per_asset))[0]

    return_context = []

    while True:
        return_context = []
        total_collateral_distribution = defaultdict(int)
        for index, collateral_assets in enumerate(collateral_per_asset):
            # Assuming that there's only one element per account in
            # collateral_per_asset
            collateral_value = (
                debt_values[index]
                / collateral_assets[0].metadata.risk_metadata.collateral_factor
            )
            fixed_point_amount = (
                collateral_value
                / prices[collateral_assets[0].asset]
                * (10 ** collateral_assets[0].asset.decimals)
            )
            collateral_per_asset[index][0] = collateral_per_asset[index][0].model_copy()
            collateral_per_asset[index][0].metadata.amount = fixed_point_amount
            collateral_per_asset[index][0].metadata.current_amount = fixed_point_amount
            total_collateral_distribution[
                collateral_assets[0].asset
            ] += fixed_point_amount
            return_context.append(
                BorrowerDetailsFromModel(
                    **{
                        "debt": int(debt_values[index]),
                        "collateral_value": collateral_value,
                    }
                )
            )
        stop = True
        for asset in exposure:
            if exposure[asset] >= total_collateral_distribution[asset]:
                stop = True

        if stop:
            break

    return return_context


def borrower_init_moonwell_simple(
    exposure: Dict[Asset, int],
    prices: Dict[Asset, float],
    collateral_per_asset: List[List[AssetsInMarginAccount]],
    numeraire: Asset,
) -> List[BorrowerDetailsFromModel]:
    # Initialize variables outside the while loop
    exposure_met = False
    attempt = 0
    max_attempts = 100  # Prevent infinite loop by limiting the number of attempts

    while not exposure_met and attempt < max_attempts:
        model_output = borrow_model_moonwell_simple(
            len(collateral_per_asset),
            condition=1
            / (collateral_per_asset[0][0].metadata.risk_metadata.collateral_factor),
        )
        debt_values = model_output[:, 1]  # Total debt in log10.
        collateral_ratios = model_output[:, 0]  # Collateral ratio.

        return_context = []
        total_collateral_distribution = defaultdict(int)

        for index, collateral_assets in enumerate(collateral_per_asset):
            debt_value = 10 ** debt_values[index]
            collateral_value = debt_value * collateral_ratios[index]
            fixed_point_amount = (
                collateral_value
                / prices[collateral_assets[0].asset]
                * (10 ** collateral_assets[0].asset.decimals)
            )

            collateral_assets[0] = collateral_assets[0].model_copy()
            collateral_assets[0].metadata.amount = fixed_point_amount
            collateral_assets[0].metadata.current_amount = fixed_point_amount
            total_collateral_distribution[
                collateral_assets[0].asset
            ] += fixed_point_amount

            return_context.append(
                BorrowerDetailsFromModel(
                    debt=int(debt_value),
                    collateral_value=collateral_value,
                )
            )

        # Check if exposure requirements are met
        exposure_met = all(
            exposure[asset] <= total
            for asset, total in total_collateral_distribution.items()
        )
        attempt += 1

    return return_context


def borrower_init_moonwell_multiasset(
    exposure: float,  # In terms of numeraire, normalized
    prices: Dict[Asset, float],
    collateral_per_asset: List[List[AssetsInMarginAccount]],
    numeraire: Asset,
) -> List[BorrowerDetailsFromModel]:
    # ensure exposure is correct
    df_samples = []
    while True:
        df_samples = sample_empirical_multiasset_positions(
            numeraire=numeraire, n_samples=len(collateral_per_asset), condition=1
        )

        exposure_check = True
        for asset, permitted_exposure in exposure.items():
            sample_key = asset.contract_address
            sample_exposure_numeraire = sum(
                df_samples[sample_key] * (10 ** df_samples["log10_borrow"])
            )
            sample_exposure = (sample_exposure_numeraire / prices[asset]) * (
                10**asset.decimals
            )

            if sample_exposure > permitted_exposure:
                # WARNING: EXPOSURE CHECK DISABLED IF SET TO TRUE
                exposure_check = False  #
                break

        if exposure_check:
            break

    return_context = []
    for index, collateral_assets in enumerate(collateral_per_asset):
        debt = 10 ** df_samples.iloc[index]["log10_borrow"]
        collateral_value_numeraire = df_samples.iloc[index]["CR"] * debt

        index_asset_to_remove = []
        for i, asset_in_margin_account in enumerate(collateral_assets):
            weight = 0

            sample_key = asset_in_margin_account.asset.contract_address
            weight = df_samples.iloc[index][sample_key]

            if weight == 0:
                index_asset_to_remove.append(i)

            else:
                fixed_point_amount = (
                    (collateral_value_numeraire * weight)
                    / prices[asset_in_margin_account.asset]
                    * (10**asset_in_margin_account.asset.decimals)
                )
                collateral_per_asset[index][i].metadata.amount = fixed_point_amount
                collateral_per_asset[index][
                    i
                ].metadata.current_amount = fixed_point_amount

        # remove assets with weight 0
        for i in sorted(index_asset_to_remove, reverse=True):
            del collateral_per_asset[index][i]

        return_context.append(
            BorrowerDetailsFromModel(
                **{
                    "debt": debt,
                    "collateral_value": collateral_value_numeraire,
                }
            )
        )

    return return_context


def borrower_init_moonwell_multiasset_conditional(
    exposure: float,  # In terms of numeraire, normalized
    prices: Dict[Asset, float],
    collateral_per_asset: List[List[AssetsInMarginAccount]],
    numeraire: Asset,
) -> List[BorrowerDetailsFromModel]:
    # Get all unique asset form ranges defined in Orchestrator in order to
    # create a filtering condition for empricical sampling
    # Initialize sets for uniqueness
    asset_condition_set = set()
    lp_integration_set = set()

    for collateral_assets in collateral_per_asset:
        for asset_in_margin_account in collateral_assets:
            asset_instance = asset_in_margin_account.asset
            if isinstance(asset_instance, ConcentratedLiquidityAsset):
                # Directly add asset instance to the set
                lp_integration_set.add(asset_instance)
            elif isinstance(asset_instance, Asset):
                # Directly add asset instance to the set
                asset_condition_set.add(asset_instance)

    # Convert sets to lists if necessary for further processing
    asset_condition = list(asset_condition_set)
    lp_integration = list(lp_integration_set)

    # ensure exposure is correct
    df_samples = []
    while True:
        df_samples = sample_empirical_multiasset_positions_conditional(
            numeraire=numeraire,
            n_samples=len(collateral_per_asset),
            cr_condition=1,
            asset_condition=asset_condition,
            lp_integration=lp_integration,
        )

        exposure_check = True
        for asset, permitted_exposure in exposure.items():
            sample_key = asset.contract_address
            sample_exposure_numeraire = sum(
                df_samples[sample_key] * (10 ** df_samples["log10_borrow"])
            )
            sample_exposure = (sample_exposure_numeraire / prices[asset]) * (
                10**asset.decimals
            )

            if sample_exposure > permitted_exposure:
                # WARNING: EXPOSURE CHECK DISABLED IF SET TO TRUE
                exposure_check = False
                break

        if exposure_check:
            break

    return_context = []
    for index, collateral_assets in enumerate(collateral_per_asset):
        debt = 10 ** df_samples.iloc[index]["log10_borrow"]
        collateral_value_numeraire = df_samples.iloc[index]["CR"] * debt

        index_asset_to_remove = []
        for i, asset_in_margin_account in enumerate(collateral_assets):
            weight = 0

            sample_key = asset_in_margin_account.asset.contract_address
            weight = df_samples.iloc[index][sample_key]

            if weight == 0:
                index_asset_to_remove.append(i)

            else:
                fixed_point_amount = (
                    (collateral_value_numeraire * weight)
                    / prices[asset_in_margin_account.asset]
                    * (10**asset_in_margin_account.asset.decimals)
                )
                collateral_per_asset[index][i].metadata.amount = fixed_point_amount
                collateral_per_asset[index][
                    i
                ].metadata.current_amount = fixed_point_amount

        # remove assets with weight 0
        for i in sorted(index_asset_to_remove, reverse=True):
            del collateral_per_asset[index][i]

        return_context.append(
            BorrowerDetailsFromModel(
                **{
                    "debt": debt,
                    "collateral_value": collateral_value_numeraire,
                }
            )
        )

    return return_context


def open_positions_init_moonwell(timestamp, numeraire):
    """
    Looks up the historical number of open position on moonwell
    """
    # Get the directory of the current script.
    current_script_path = os.path.dirname(os.path.realpath(__file__))

    # Load data
    if numeraire == usdc or numeraire == usdbc:
        model_file_path = os.path.join(
            current_script_path, "moonwell_position_data/open_position_usdc_usdbc.csv"
        )
        df_position_count = pd.read_csv(model_file_path, index_col=0)

    elif numeraire == weth:
        model_file_path = os.path.join(
            current_script_path, "moonwell_position_data/open_position_weth.csv"
        )
        df_position_count = pd.read_csv(model_file_path, index_col=0)
    else:
        KeyError(f"No data on Open Positision available for Numeraire {numeraire}")

    # Identify relevant block
    r = requests.get(f"https://coins.llama.fi/block/base/{timestamp}")
    blocknumber = r.json()["height"]

    # Use the closest block number for lookup
    closest_blocknumber = df_position_count.index[
        abs((df_position_count.index - blocknumber)).argmin()
    ]

    no_of_positions = int(df_position_count.loc[closest_blocknumber]["position_count"])

    # Ensure a minimum number of positions
    if no_of_positions < 10:
        no_of_positions = 10
        print(
            f"Default to 10 accounts timestamp as blocknumber {closest_blocknumber} (i.e timestamp {timestamp}) retrieved less than 10 open positions"
        )
    return no_of_positions
