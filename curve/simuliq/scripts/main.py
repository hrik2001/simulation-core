import os
from itertools import product
from typing import Tuple, Dict, Any, Optional

import pandas as pd
import requests
from tqdm import tqdm

from core.models import Chain
from curve.models import Simuliq
from curve.simuliq.models.curve_protocol import CurveMintMarketDTO
from curve.simuliq.models.token import TokenDTO
from curve.simuliq.models.trade_pair import PairDTO
from curve.simuliq.scripts.process_stored_data_aave import create_asset_mapping, create_health_ratio_data, \
    create_health_ratio_data_emode, create_liquidatable_user_data


def analyze_liquidatable_positions(
    aave_supported_asset_data: pd.DataFrame,
    aave_user_position_data: pd.DataFrame,
    asset_under_consideration: str,
    price_assumption: float,
    emode_lt: float,
    min_usd_threshold: float = 15000
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Analyzes liquidatable positions for given asset and price assumption.
    Returns both raw and USD values for liquidatable collateral and debt.
    """
    # Create price mapping
    new_price_mapping = {asset_under_consideration: price_assumption}
    price_mapping = dict(zip(aave_supported_asset_data['symbol'], aave_supported_asset_data['price']))

    # Create asset mapping and get health ratios
    asset_mapping = create_asset_mapping(aave_supported_asset_data, new_price_mapping)

    # Get health ratio data for both normal and emode
    health_ratio_data_no_emode = create_health_ratio_data(aave_user_position_data, asset_mapping)
    health_ratio_data_emode = create_health_ratio_data_emode(aave_user_position_data, asset_mapping, emode_lt)
    health_ratio_data = pd.concat([health_ratio_data_no_emode, health_ratio_data_emode])

    # Get liquidatable positions
    total_liquidatable_collateral, total_liquidatable_debt = create_liquidatable_user_data(health_ratio_data)

    # Filter non-zero positions
    total_liquidatable_collateral = {k: v for k, v in total_liquidatable_collateral.items() if v > 0}
    total_liquidatable_debt = {k: v for k, v in total_liquidatable_debt.items() if v > 0}

    # Convert to USD
    total_liquidatable_collateral_usd = {
        symbol: quantity * price_mapping.get(symbol, 1)
        for symbol, quantity in total_liquidatable_collateral.items()
    }

    total_liquidatable_debt_usd = {
        symbol: quantity * price_mapping.get(symbol, 1)
        for symbol, quantity in total_liquidatable_debt.items()
    }

    # Filter by USD threshold
    filtered_collateral_usd = {k: v for k, v in total_liquidatable_collateral_usd.items() if v > min_usd_threshold}
    filtered_debt_usd = {k: v for k, v in total_liquidatable_debt_usd.items() if v > min_usd_threshold}

    # Reconstruct raw values from filtered USD values
    filtered_collateral = {
        symbol: float(usd_value) / price_mapping.get(symbol, 1)
        for symbol, usd_value in filtered_collateral_usd.items()
    }

    filtered_debt = {
        symbol: float(usd_value) / price_mapping.get(symbol, 1)
        for symbol, usd_value in filtered_debt_usd.items()
    }

    return filtered_collateral, filtered_debt


def get_curve_liquidation_data(output_liq_df: pd.DataFrame, price_assumption: float, asset_under_consideration_curve: str) -> \
tuple[None, None] | tuple[dict[Any, Any], dict[str, float]]:
    """
    Get curve liquidation data for the closest price point >= price_assumption.
    Returns (collateral, debt) tuple or (None, None) if no suitable price found.
    """
    # Check if there are any prices >= price_assumption
    valid_rows = output_liq_df[output_liq_df['max_price'] <= price_assumption]

    if valid_rows.empty:
        return None, None

    # Get the closest row
    closest_row = valid_rows.sort_values('max_price').iloc[-1]
    return {asset_under_consideration_curve: float(closest_row['max_collateral_value'])}, {
        'crvUSD': float(closest_row['debt'])}


def merge_liquidation_data(aave_data: dict, curve_data: dict) -> dict:
    """
    Merge liquidation data from Aave and Curve protocols.
    """
    merged_data = aave_data.copy()  # Start with Aave data

    # Merge Curve data
    for token, amount in curve_data.items():
        if token in merged_data:
            merged_data[token] += amount
        else:
            merged_data[token] = amount

    return merged_data


# Function to create and store PairDTO if it doesn't exist
def create_and_store_pair(chain, aave_asset_object_dict, sell_token, buy_token, trade_pair_hashmap):
    if sell_token != buy_token:
        key = f"{sell_token}-{buy_token}"
        if key not in trade_pair_hashmap:
            print(f"Creating pair: {sell_token} -> {buy_token}")

            pair_dto = PairDTO(
                sell_token=aave_asset_object_dict[sell_token],
                buy_token=aave_asset_object_dict[buy_token],
                chain=chain
            )

            print(pair_dto.sell_token.name, pair_dto.buy_token.name, pair_dto.exchange_price, pair_dto.k, pair_dto.c)

            Simuliq(
                chain=chain,
                sell_token=pair_dto.sell_token.name,
                buy_token=pair_dto.buy_token.name,
                exchange_price=pair_dto.exchange_price,
                k=pair_dto.k,
                c=pair_dto.c
            ).save()

            trade_pair_hashmap[key] = pair_dto
            return 1
    return 0


def fetch_curve_market_data(
        network: str = "ethereum"
) -> Optional[Dict]:
    """
    Fetch market data from Curve Finance API.

    Args:
        network (str): Network name (default: "ethereum")
        page (int): Page number for pagination (default: 1)
        per_page (int): Number of items per page (default: 10)
        fetch_on_chain (bool): Whether to fetch on-chain data (default: False)

    Returns:
        Optional[Dict]: JSON response from the API or None if request fails
    """

    base_url = "https://prices.curve.fi/v1/crvusd/markets"

    try:
        # Construct URL with query parameters
        url = f"{base_url}/{network}"
        params = {}

        # Make the request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise exception for non-200 status codes

        market_data = response.json()['data']

        market_objects_dict = {}

        chain = Chain.objects.get(chain_name__iexact="ethereum")

        for market in market_data:
            if market['borrowable'] > 0:
                asset = market['collateral_token']['symbol']
                market_objects_dict[asset] = CurveMintMarketDTO(
                    chain=chain,
                    protocol="curve",
                    address=market['address'],
                    llamma=market['llamma'],
                    collateral_token_symbol=market['collateral_token']['symbol'],
                    collateral_token_address=market['collateral_token']['address'],
                    borrow_token_symbol=market['stablecoin_token']['symbol'],
                    borrow_token_address=market['stablecoin_token']['address']
                )

        return market_objects_dict
    except requests.RequestException as e:
        return None


def main():
    AAVE_EMODE_LT = 0.95
    ASSET_UNDER_CONSIDERATION = "WETH"
    ASSET_UNDER_CONSIDERATION_CURVE = 'WETH'

    chain = Chain.objects.get(chain_name__iexact="ethereum")
    aave_supported_asset_data = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "aave_supported_asset_data.csv"))
    aave_user_position_data = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "aave_user_position_data.csv"))

    aave_asset_object_dict = {}

    for _, row in tqdm(aave_supported_asset_data.iterrows(), total=len(aave_supported_asset_data), desc="Creating TokenDTO objects"):
        token = TokenDTO(
            address=row['assetAddress'],
            name=row['symbol'],
            symbol=row['symbol'],
            decimals=row['decimals'],
            chain=chain,
            price=row['price'],
        )
        aave_asset_object_dict[row['symbol']] = token

    current_price_mapping = {}
    for index, asset in aave_supported_asset_data.iterrows():
        current_price_mapping[asset['symbol']] = asset['price']

    asset_object = next((value for key, value in aave_asset_object_dict.items() if key == ASSET_UNDER_CONSIDERATION),
                        None)
    PRICE_ASSUMPTION = 0.8 * asset_object.price
    aave_collateral, aave_debt = analyze_liquidatable_positions(
        aave_supported_asset_data,
        aave_user_position_data,
        ASSET_UNDER_CONSIDERATION,
        PRICE_ASSUMPTION,
        AAVE_EMODE_LT
    )

    market = fetch_curve_market_data()[ASSET_UNDER_CONSIDERATION_CURVE]
    df = market.get_user_position_data()
    output_liq_df, output_liq_df_raw = market.compute_price_for_max_hard_liq(df, 0.80)
    curve_collateral, curve_debt = get_curve_liquidation_data(output_liq_df, PRICE_ASSUMPTION, ASSET_UNDER_CONSIDERATION_CURVE)

    total_collateral = merge_liquidation_data(aave_collateral, curve_collateral)
    total_debt = merge_liquidation_data(aave_debt, curve_debt)

    trade_pair_hashmap = {}

    # FLASHLOAN_ASSET_SYMBOLS = ['WETH']
    FLASHLOAN_ASSET_SYMBOLS = ['USDC', 'USDT', 'DAI', 'WETH']

    # Create sets for easier lookup
    flashloan_assets = set(FLASHLOAN_ASSET_SYMBOLS)
    liquidatable_debt_assets = set(total_debt.keys())
    liquidatable_collateral_assets = set(total_collateral.keys())

    # Set 1: Flashloan assets as sell, liquidatable debt as buy
    new_pairs_count = 0
    total_pairs_set1 = len(flashloan_assets) * len(liquidatable_debt_assets)
    for sell_token, buy_token in tqdm(product(flashloan_assets, liquidatable_debt_assets),
                                      total=total_pairs_set1,
                                      desc="Creating Set 1 PairDTO objects"):
        new_pairs_count += create_and_store_pair(chain, aave_asset_object_dict, sell_token, buy_token, trade_pair_hashmap)

    # Set 2: Liquidatable collateral as sell, flashloan assets as buy
    total_pairs_set2 = len(liquidatable_collateral_assets) * len(flashloan_assets)
    for sell_token, buy_token in tqdm(product(liquidatable_collateral_assets, flashloan_assets),
                                      total=total_pairs_set2,
                                      desc="Creating Set 2 PairDTO objects"):
        new_pairs_count += create_and_store_pair(chain, aave_asset_object_dict, sell_token, buy_token, trade_pair_hashmap)

    print(f"New pairs added: {new_pairs_count}")
