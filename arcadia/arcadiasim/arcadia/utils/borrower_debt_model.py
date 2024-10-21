import os
import pickle

import numpy as np
import pandas as pd
import requests
from arcadiasim.entities.asset import *
from scipy.stats import truncnorm


def borrow_model_arcadia_v1_short_term(n=1):
    """
    Contains the anticipated borrow model in the short terrm based on Arcadia v1.

    Ref.: https://docs.google.com/spreadsheets/d/1MVMk4R6ilzrlB1_YIFsiVzLLxVDd40CyByFhIsemjHg/edit#gid=1171147095
    """

    mu = 5.74830248
    sigma = 2.510468636

    # Set bounds
    lower_bound, upper_bound = (0 - mu) / sigma, np.inf

    # Create the truncated normal distribution
    truncated_dist = truncnorm(lower_bound, upper_bound, loc=mu, scale=sigma)

    debt = truncated_dist.rvs(n)

    collateral_ratio = 1

    return np.exp(debt), collateral_ratio


def borrow_model_arcadia_v1_medium_term():
    """
    Contains the anticipated borrow model in the medium terrm based on Arcadia v1.

    Ref.: https://docs.google.com/spreadsheets/d/1MVMk4R6ilzrlB1_YIFsiVzLLxVDd40CyByFhIsemjHg/edit#gid=1171147095
    """

    mu = 7.5
    sigma = 3

    # Set bounds
    lower_bound, upper_bound = (0 - mu) / sigma, np.inf

    # Create the truncated normal distribution
    truncated_dist = truncnorm(lower_bound, upper_bound, loc=mu, scale=sigma)

    debt = truncated_dist.rvs(1)

    collateral_ratio = 1

    return np.exp(debt), collateral_ratio


def borrow_model_arcadia_v1_long_term():
    """
    Contains the anticipated borrow model in the long terrm based on Arcadia v1.

    Ref.: https://docs.google.com/spreadsheets/d/1MVMk4R6ilzrlB1_YIFsiVzLLxVDd40CyByFhIsemjHg/edit#gid=1171147095
    """

    mu = 9
    sigma = 4

    # Set bounds
    lower_bound, upper_bound = (0 - mu) / sigma, np.inf

    # Create the truncated normal distribution
    truncated_dist = truncnorm(lower_bound, upper_bound, loc=mu, scale=sigma)

    debt = truncated_dist.rvs(1)

    collateral_ratio = 1

    return np.exp(debt), collateral_ratio


def borrow_model_moonwell_simple(n_samples, condition: float = 1):
    """
    Generate samples from the KDE model where the first column must be greater than 1.

    :param n_samples: The number of samples to generate.
    :return: An array of samples satisfying the condition with collateral Ratio and Total Debt log 10
    """
    # Get the directory of the current script.
    current_script_path = os.path.dirname(os.path.realpath(__file__))

    # Construct the path to the .pkl file.
    model_file_path = os.path.join(current_script_path, "borrower_model_moonwell.pkl")

    with open(model_file_path, "rb") as file:
        kde_model = pickle.load(file)

    samples = []
    while len(samples) < n_samples:
        # Generate a batch of samples
        batch = kde_model.sample(n_samples)
        # Check which samples satisfy the condition (i.e., CR greater than 1)
        valid = batch[:, 0] > condition
        # Keep only the valid ones
        samples.extend(batch[valid])

    return np.array(samples[:n_samples])


def lp_helper(df, lp_assets=[]):
    for lp_token in lp_assets:
        # Identifying the contract addresses
        t0_address = lp_token.token0.contract_address
        t1_address = lp_token.token1.contract_address
        lp_address = lp_token.contract_address

        # Initializing the LP token balance column to 0
        df[lp_address] = 0

        # A custom row operation function to allocate LP tokens
        def allocate_lp_tokens(row):
            t0_balance, t1_balance = row[t0_address], row[t1_address]
            min_balance = min(t0_balance, t1_balance)

            if round(min_balance, 2) > 0:
                # Allocate LP tokens based on the smallest balance
                row[lp_address] = 2 * min_balance

                # Subtract allocated tokens from each token balance
                row[t0_address] -= min_balance
                row[t1_address] -= min_balance
                return row
            else:
                return row

        # Apply the function across the DataFrame rows
        df = df.apply(allocate_lp_tokens, axis=1)

    return df


def sample_empirical_multiasset_positions(numeraire, n_samples, condition=1):
    # Get the directory of the current script.
    current_script_path = os.path.dirname(os.path.realpath(__file__))

    # Load data
    if numeraire == usdc or numeraire == usdbc:
        model_file_path = os.path.join(
            current_script_path,
            "moonwell_position_data/moonwell_usdc_usdcb_collateral_distribution.csv",
        )
        df_empirical_positions = pd.read_csv(model_file_path, index_col=0)
    elif numeraire == weth:
        model_file_path = os.path.join(
            current_script_path,
            "moonwell_position_data/moonwell_weth_collateral_distribution.csv",
        )
        df_empirical_positions = pd.read_csv(model_file_path, index_col=0)
    else:
        KeyError(f"No Position Data available for Numeraire {numeraire}")

    # Filter DataFrame first to satisfy the condition, improving efficiency
    valid_samples = df_empirical_positions[df_empirical_positions["CR"] > condition]

    # Ensure we have enough valid samples; if not, reduce no_of_positions or repeat valid samples
    if len(valid_samples) < n_samples:
        repeat_times = -(
            -n_samples // len(valid_samples)
        )  # Ceiling division to ensure enough samples
        valid_samples = (
            pd.concat([valid_samples] * repeat_times)
            .iloc[:n_samples]
            .reset_index(drop=True)
        )
    else:
        # Sample directly from valid samples if we have enough
        valid_samples = valid_samples.sample(n=n_samples)

    valid_samples.reset_index(drop=True, inplace=True)

    return round(valid_samples, 3)


def sample_empirical_multiasset_positions_conditional(
    numeraire, n_samples, cr_condition, asset_condition=None, lp_integration=None
):
    # Initialize asset_condition and lp_integration if None to avoid mutable default arguments
    asset_condition = asset_condition if asset_condition is not None else []
    lp_integration = lp_integration if lp_integration is not None else []

    # Define the base directory for position data
    current_script_path = os.path.dirname(os.path.realpath(__file__))
    base_data_path = os.path.join(current_script_path, "moonwell_position_data")

    # Map numeraires to their corresponding file names
    file_map = {
        usdc: "moonwell_usdc_usdcb_collateral_distribution.csv",
        usdbc: "moonwell_usdc_usdcb_collateral_distribution.csv",
        weth: "moonwell_weth_collateral_distribution.csv",
    }

    # Check if numeraire is supported
    if numeraire not in file_map:
        raise KeyError(
            f"No Position Data available for Numeraire {numeraire} with filter condition CR {cr_condition} and Asset filter {asset_condition}"
        )

    # Load data
    model_file_path = os.path.join(base_data_path, file_map[numeraire])
    df = pd.read_csv(model_file_path, index_col=0)

    # Apply asset conditions if any
    if asset_condition:
        condition = pd.Series([True] * len(df), index=df.index)
        for asset in asset_condition:
            condition &= df[asset.contract_address] != 0
        df = df[condition]

    # Filter DataFrame to satisfy the CR condition
    valid_samples = df[df["CR"] > cr_condition]

    # Apply LP integration adjustments if any
    if lp_integration:
        valid_samples = lp_helper(valid_samples, lp_integration)

    # Handle sampling
    if len(valid_samples) < n_samples:
        # Repeat valid samples if there aren't enough
        repeat_times = -(
            -n_samples // len(valid_samples)
        )  # Ceiling division to ensure enough samples
        valid_samples = (
            pd.concat([valid_samples] * repeat_times)
            .iloc[:n_samples]
            .reset_index(drop=True)
        )
    else:
        # Sample directly if we have enough
        valid_samples = valid_samples.sample(n=n_samples).reset_index(drop=True)

    return round(valid_samples, 3)
