from typing import Dict, Tuple, Union
import pandas as pd
import numpy as np
import logging
from tqdm import tqdm 
import json
from scipy import optimize

from curve.simuliq.models.trade_pair import PairDTO

FLASHLOAN_ASSET_SYMBOLS = ['USDC', 'USDT', 'DAI', 'WETH']
# FLASHLOAN_ASSET_SYMBOLS = ['WETH']

'''
"network": network.network,
"batch_data_provider_address": network.batch_data_provider_address,
"aave_pool_address": network.aave_pool_address,
"aave_data_provider_address": network.aave_data_provider_address,
"holder_query_id": network.holder_query_id,

"user_position_df": user_position_df,
"asset_data_df": asset_data_df,
"primary_asset_object_dict": primary_asset_object_dict,
"secondary_asset_object_dict": secondary_asset_object_dict,
"trade_pair_hashmap": trade_pair_hashmap
'''

'''
Sample new_price_mapping ->
    new_price_mapping = {
        "WETH": 2446.7,
        "cbETH": 2652.65,
        "USDbC": 0.999141,
        "wstETH": 2908.765217,
        "USDC": 0.999141,
        "weETH": 2571.945325,
        "cbBTC": 62685.49565
        }
'''


def update_trade_pair_exchange_price(trade_pair_hashmap: Dict[str, PairDTO], new_price_mapping: Dict = None):
    # scale_price_and_identify_liquidatable_collateral
    if new_price_mapping is None:
        return trade_pair_hashmap

    for pair_key, trade_pair in trade_pair_hashmap.items():
        sell_token_symbol, buy_token_symbol = pair_key.split('-')
        
        # logging.info(f"Checking {sell_token_symbol} and {buy_token_symbol}")
        
        if sell_token_symbol in new_price_mapping and buy_token_symbol in new_price_mapping:
            sell_token_price = new_price_mapping[sell_token_symbol]
            buy_token_price = new_price_mapping[buy_token_symbol]
            
            if sell_token_price != 0:
                new_exchange_price = sell_token_price / buy_token_price
                trade_pair.new_exchange_price = new_exchange_price
            else:
                print(f"Warning: Sell token price for {sell_token_symbol} is 0. Skipping update for pair {pair_key}.")
        else:
            print(f"Warning: Price not found for {sell_token_symbol} or {buy_token_symbol}. Skipping update for pair {pair_key}.")
    
    return trade_pair_hashmap


def create_asset_mapping(asset_data_df: pd.DataFrame, new_price_mapping: Dict = None):
    asset_mapping = {}
    
    for index, row in asset_data_df.iterrows():
        param_dict = {}
        
        if new_price_mapping and row['symbol'] in new_price_mapping:
            param_dict['price'] = new_price_mapping[row['symbol']]
        else:
            param_dict['price'] = row['price']
        
        param_dict['liquidationThreshold'] = row['liquidationThreshold']
        
        asset_mapping[row['symbol']] = param_dict
        
    return asset_mapping


def create_health_ratio_data(user_position_df: pd.DataFrame, asset_mapping: Dict):
    
    user_position_df = user_position_df.copy()
    user_position_df = user_position_df[user_position_df['emode'] == 0]
    
    def calculate_user_metrics(row):
        total_scaled_collateral = 0
        total_actual_collateral = 0
        total_user_debt = 0
        for symbol, data in asset_mapping.items():
            collateral_col = f"a{symbol}"
            if collateral_col in row.index:
                total_scaled_collateral += row[collateral_col] * data['liquidationThreshold'] * data['price']
                total_actual_collateral += row[collateral_col] * data['price']
            debt_col = f"d{symbol}"
            if debt_col in row.index:
                total_user_debt += row[debt_col] * data['price']
        return pd.Series({
            'total_scaled_collateral': total_scaled_collateral,
            'total_actual_collateral': total_actual_collateral,
            'total_user_debt': total_user_debt
        })

    user_position_df[['total_scaled_collateral', 'total_actual_collateral', 'total_user_debt']] = user_position_df.apply(calculate_user_metrics, axis=1)
    user_position_df['health_ratio'] = user_position_df['total_scaled_collateral'] / user_position_df['total_user_debt']
    user_position_df['health_ratio'] = user_position_df['health_ratio'].replace([np.inf, -np.inf], 1e6)
    user_position_df['health_ratio'] = user_position_df['health_ratio'].fillna(0)
    
    filtered_data = user_position_df[(user_position_df['total_user_debt'] > 100)]

    return filtered_data


def create_health_ratio_data_emode(user_position_df: pd.DataFrame, asset_mapping: Dict, emode_LT: float):
    
    LT = emode_LT
    
    user_position_df = user_position_df.copy()
    user_position_df = user_position_df[user_position_df['emode'] == 1]
    
    def calculate_user_metrics(row):
        total_scaled_collateral = 0
        total_actual_collateral = 0
        total_user_debt = 0
        for symbol, data in asset_mapping.items():
            collateral_col = f"a{symbol}"
            if collateral_col in row.index:
                total_scaled_collateral += row[collateral_col] * LT * data['price']
                total_actual_collateral += row[collateral_col] * data['price']
            debt_col = f"d{symbol}"
            if debt_col in row.index:
                total_user_debt += row[debt_col] * data['price']
        return pd.Series({
            'total_scaled_collateral': total_scaled_collateral,
            'total_actual_collateral': total_actual_collateral,
            'total_user_debt': total_user_debt
        })
    
    if user_position_df.empty:
        # print("No users found in user_position_df")
        return pd.DataFrame()
    else:  
        user_position_df[['total_scaled_collateral', 'total_actual_collateral', 'total_user_debt']] = user_position_df.apply(calculate_user_metrics, axis=1)
        user_position_df['health_ratio'] = user_position_df['total_scaled_collateral'] / user_position_df['total_user_debt']
        user_position_df['health_ratio'] = user_position_df['health_ratio'].replace([np.inf, -np.inf], 1e6)
        user_position_df['health_ratio'] = user_position_df['health_ratio'].fillna(0)
        
        filtered_data = user_position_df[(user_position_df['total_user_debt'] > 100)]

        return filtered_data


def create_liquidatable_user_data(health_ratio_df: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, float]]:
    

    liquidatable_user_data = health_ratio_df[health_ratio_df['health_ratio'].round(2) < 1]
    # print(f"Number of liquidatable users found: {len(liquidatable_user_data)}")
    
    if liquidatable_user_data.empty:
        # print("No liquidatable users found, returning empty dictionaries")
        return {}, {}

    # Sum all the column values for all the liquidatable users
    liquidatable_user_sum = liquidatable_user_data.sum()
    # logging.info(f"Sum of liquidatable user data calculated")
    
    # Process collateral (columns starting with 'a')
    total_liquidatable_collateral = {
        column[1:]: liquidatable_user_sum[column]
        for column in liquidatable_user_sum.index
        if column.startswith('a')
    }
    # logging.info(f"total_liquidatable_collateral calculated")
    
    # Process debt (columns starting with 'd')
    total_liquidatable_debt = {
        column[1:]: liquidatable_user_sum[column]
        for column in liquidatable_user_sum.index
        if column.startswith('d')
    }
    
    return total_liquidatable_collateral, total_liquidatable_debt





def derived_func(x, r, k, c):
    try:
        if x <= 0 or c == 0:
            return 0
        exponent = k * (x ** -c)
        if exponent > 700:  # np.exp(709) is approximately the largest value exp can handle
            return x * r
        y = (x * r) * (1 - (1/np.exp(exponent)))
        return y
    except Exception as e:
        logging.error(f"Error in derived_func: {str(e)}, x={x}, r={r}, k={k}, c={c}")
        return 0
    
    
# def find_x(y_target, r, k, c):
#     if r == 0 or k == 0 or c == 0:
#         logging.warning(f"Invalid parameters in find_x: r={r}, k={k}, c={c}")
#         return 0
    
#     def objective(x):
#         return abs(derived_func(x, r, k, c) - y_target)
    
#     try:
#         result = optimize.minimize_scalar(objective, method='brent')
#         return result.x
#     except Exception as e:
#         logging.error(f"Error in find_x: {str(e)}, y_target={y_target}, r={r}, k={k}, c={c}")
#         return 0

def find_x(y_target, r, k, c, max_iterations=100, tolerance=1e-10): # Newton's method implementation to find x.
    """Newton's method implementation to find x."""
    def f(x):
        return derived_func(x, r, k, c) - y_target
        
    def df(x):
        # Numerical derivative
        h = 1e-7
        return (f(x + h) - f(x)) / h
    
    # Initial guess
    x = y_target / r  # Simple initial guess
    
    for _ in range(max_iterations):
        fx = f(x)
        if abs(fx) < tolerance:
            return x
            
        dfx = df(x)
        if dfx == 0:
            break
            
        x = x - fx/dfx
        
        if x <= 0:  # Keep x positive
            x = tolerance
            
    return x
    
    
def create_liquidations_v2(
    updated_trade_pair_hashmap: Dict[str, PairDTO],
    asset_mapping: Dict[str, Dict[str, float]],
    total_liquidatable_collateral: Dict[str, float], 
    total_liquidatable_debt: Dict[str, float]
) -> Union[Dict[str, Union[str, float]], None]:
    
    slippage_hashmap = updated_trade_pair_hashmap.copy()
    
    def compute_flashloan_start(total_liquidatable_debt: Dict[str, float],
                                flashloan_asset: str,
                                flashloan_asset_price: float
                                ):
        
        flashloan_start = 0
        
        # print(json.dumps(total_liquidatable_debt, indent=4))
        
        for asset, debt in total_liquidatable_debt.items():
            if debt*flashloan_asset_price > 10:
                if asset == flashloan_asset:
                    flashloan_start += debt
                    # logging.info(f"{asset} == {flashloan_asset} | Added debt {debt} to flashloan_start for {asset}")
                    continue
                else:
                    lookup_key = f'{flashloan_asset}-{asset}'
                    if lookup_key in slippage_hashmap:
                        # logging.info(f"Processing {lookup_key} | Debt: {debt}, Exchange price: {slippage_hashmap[lookup_key].new_exchange_price}, k: {slippage_hashmap[lookup_key].k}, c: {slippage_hashmap[lookup_key].c}")
                        try:
                            x = find_x(debt, slippage_hashmap[lookup_key].new_exchange_price, slippage_hashmap[lookup_key].k, slippage_hashmap[lookup_key].c)
                            flashloan_start += x
                            # logging.info(f"{lookup_key} found! | Added {x} to flashloan_start for {lookup_key}")
                        except Exception as e:
                            logging.error(f"Error processing {lookup_key}: {str(e)}")
                    else:
                        logging.info(f"Lookup key {lookup_key} not found in slippage_hashmap")
        
        return flashloan_start

    def compute_flashloan_end(total_liquidatable_collateral: Dict[str, float],
                            flashloan_asset: str,
                            flashloan_asset_price: float
                            ):
        
        flashloan_end = 0
        
        # print(json.dumps(total_liquidatable_collateral, indent=4))
        
        for asset, collateral in total_liquidatable_collateral.items():
            if collateral*flashloan_asset_price > 10:
                if asset == flashloan_asset:
                    flashloan_end += collateral
                    # logging.info(f"{asset} == {flashloan_asset} | Added collateral {collateral} to flashloan_end for {asset}")
                    continue
                else:
                    lookup_key = f'{asset}-{flashloan_asset}'
                    if lookup_key in slippage_hashmap:
                        # logging.info(f"Processing {lookup_key} | Collateral: {collateral}, Exchange price: {slippage_hashmap[lookup_key].new_exchange_price}, k: {slippage_hashmap[lookup_key].k}, c: {slippage_hashmap[lookup_key].c}")
                        try:
                            y = derived_func(collateral, slippage_hashmap[lookup_key].new_exchange_price, slippage_hashmap[lookup_key].k, slippage_hashmap[lookup_key].c)
                            flashloan_end += y
                            # logging.info(f"{lookup_key} found! | Added {y} to flashloan_end for {lookup_key}")
                        except Exception as e:
                            logging.error(f"Error processing {lookup_key}: {str(e)}")
                    else:
                        logging.info(f"Lookup key {lookup_key} not found in slippage_hashmap")
        
        return flashloan_end
    

    liquidations = []
    for flashloan_asset in FLASHLOAN_ASSET_SYMBOLS:
        if flashloan_asset in asset_mapping:
            flashloan_start = compute_flashloan_start(total_liquidatable_debt, flashloan_asset, asset_mapping[flashloan_asset]['price'])
            flashloan_end = compute_flashloan_end(total_liquidatable_collateral, flashloan_asset, asset_mapping[flashloan_asset]['price'])
            
            print(json.dumps(total_liquidatable_collateral, indent=4))
            print(json.dumps(total_liquidatable_debt, indent=4))
                        
            flashloan_profit = (flashloan_end - flashloan_start) * asset_mapping[flashloan_asset]['price']
            
            liq_dict = {
                'flashloan_asset': flashloan_asset,
                'flashloan_asset_price': asset_mapping[flashloan_asset]['price'],
                'flashloan_start': flashloan_start,
                'flashloan_start_usd': flashloan_start * asset_mapping[flashloan_asset]['price'],
                'flashloan_end': flashloan_end,
                'flashloan_end_usd': flashloan_end * asset_mapping[flashloan_asset]['price'],
                'flashloan_profit': flashloan_profit,
                'flashloan_profit_usd': flashloan_profit * asset_mapping[flashloan_asset]['price']
            }
            
            liquidations.append(liq_dict)
            # logging.info(f"Added liquidation for {flashloan_asset}: profit_usd = {liq_dict['flashloan_profit_usd']}")
    
    
    print(json.dumps(liquidations, indent=4))
    print("*"*100)
    
    if not liquidations:
        logging.info("No profitable liquidations found")
        return None
    
    max_profit_dict = max(liquidations, key=lambda x: x['flashloan_profit_usd'])
    
    return max_profit_dict



# def create_liquidations(
#     updated_trade_pair_hashmap: Dict[str, PairDTO],
#     asset_mapping: Dict[str, Dict[str, float]],
#     total_liquidatable_collateral: Dict[str, float], 
#     total_liquidatable_debt: Dict[str, float]
# ) -> Union[Dict[str, Union[str, float]], None]:
    
#     logging.info("Starting create_liquidations function")
#     liquidations = []
    
#     assets_under_consideration = set(total_liquidatable_debt.keys()) & set(total_liquidatable_collateral.keys())
#     logging.info(f"Assets under consideration: {assets_under_consideration}")
    
#     for flashloan_asset in FLASHLOAN_ASSET_SYMBOLS:
#         if flashloan_asset not in asset_mapping:
#             logging.info(f"Skipping {flashloan_asset} as it's not in asset mapping")
#             continue

#         flashloan_asset_price = asset_mapping[flashloan_asset]['price']
#         flashloan_start = 0
        
#         for asset, debt in total_liquidatable_debt.items():
#             lookup_key = f'{flashloan_asset}-{asset}'
#             if lookup_key not in updated_trade_pair_hashmap:
#                 if flashloan_asset == asset:
#                     flashloan_start += debt
#                     logging.info(f"Added debt {debt} to flashloan_start for {flashloan_asset}")
#                 else:
#                     logging.info(f"Lookup key {lookup_key} not found in updated_trade_pair_hashmap")
#                 continue

#             pair_object = updated_trade_pair_hashmap[lookup_key]
#             r, k, c = pair_object.new_exchange_price, pair_object.k, pair_object.c
#             y = debt  # The debt is our target y value

#             if r == 0:
#                 logging.warning(f"Exchange price is zero for {lookup_key}")
#                 continue

#             def func_to_solve(x):
#                 return derived_func(x, r, k, c) - y
            
#             def find_x(y_target, r, k, c):
#                 def objective(x):
#                     return abs(derived_func(x, r, k, c) - y_target)
                
#                 result = optimize.minimize_scalar(objective, method='brent')
#                 return result.x
            
            
#             try:
#                 # Use a more robust initial guess
#                 initial_guess = y / r if r != 0 else y
#                 x_solution = optimize.root_scalar(func_to_solve, x0=initial_guess, x1=initial_guess*1.1, method='secant')
#                 if x_solution.converged:
#                     flashloan_start += x_solution.root
#                     logging.debug(f"Added {x_solution.root} to flashloan_start for {lookup_key}")
#                 else:
#                     logging.warning(f"Failed to find solution for {lookup_key}")
#             except Exception as e:
#                 logging.warning(f"Error solving for {lookup_key}: {str(e)}")
        
#         if not total_liquidatable_collateral:
#             logging.warning("No liquidatable collateral available")
#             continue

#         first_collateral = next(iter(total_liquidatable_collateral))
#         collateral_sell_lookup_key = f'{first_collateral}-{flashloan_asset}'
#         sell_qt = total_liquidatable_collateral[first_collateral]
        
#         if collateral_sell_lookup_key in updated_trade_pair_hashmap:
#             col_pair_object = updated_trade_pair_hashmap[collateral_sell_lookup_key]
#             r, k, c = col_pair_object.new_exchange_price, col_pair_object.k, col_pair_object.c
#             flashloan_end = derived_func(sell_qt, r, k, c)
#         elif flashloan_asset == first_collateral:
#             flashloan_end = sell_qt
#         else:
#             flashloan_end = 0
        
#         flashloan_profit = (flashloan_end - flashloan_start) * flashloan_asset_price
        
#         liq_dict = {
#             'flashloan_asset': flashloan_asset,
#             'flashloan_asset_price': flashloan_asset_price,
#             'flashloan_start': flashloan_start,
#             'flashloan_start_usd': flashloan_start * flashloan_asset_price,
#             'flashloan_end': flashloan_end,
#             'flashloan_end_usd': flashloan_end * flashloan_asset_price,
#             'flashloan_profit': flashloan_profit,
#             'flashloan_profit_usd': flashloan_profit * flashloan_asset_price
#         }
        
#         liquidations.append(liq_dict)
#         logging.debug(f"Added liquidation for {flashloan_asset}: profit_usd = {liq_dict['flashloan_profit_usd']}")
    
#     if not liquidations:
#         logging.warning("No profitable liquidations found")
#         return None

#     max_profit_dict = max(liquidations, key=lambda x: x['flashloan_profit_usd'])
#     logging.info(f"Most profitable liquidation: {max_profit_dict}")
    
#     return max_profit_dict
    

def scale_supply_and_create_liquidations(
    updated_trade_pair_hashmap: Dict[str, PairDTO],
    asset_mapping: Dict[str, Dict[str, float]],
    total_liquidatable_collateral: Dict[str, float], 
    total_liquidatable_debt: Dict[str, float],
    lower_limit_scale: float,
    upper_limit_scale: float,
    iterations: int
    ) -> pd.DataFrame:
    
    def scale_total_liquidatable_collateral(total_liquidatable_collateral: Dict[str, float], 
                                            scale_factor: float) -> Dict[str, float]:
        return {asset: amount * scale_factor for asset, amount in total_liquidatable_collateral.items()}
    
    def scale_total_liquidatable_debt(total_liquidatable_debt: Dict[str, float], 
                                      scale_factor: float) -> Dict[str, float]:
        return {asset: amount * scale_factor for asset, amount in total_liquidatable_debt.items()}
    
    scale_series = np.linspace(lower_limit_scale, upper_limit_scale, iterations)
    
        
    iteration_liquidations = []
    
    
    for scale in scale_series:
        scaled_collateral = scale_total_liquidatable_collateral(total_liquidatable_collateral, scale)
        scaled_debt = scale_total_liquidatable_debt(total_liquidatable_debt, scale)
        
        # print(json.dumps(scaled_collateral, indent=4))
        # print(json.dumps(scaled_debt, indent=4))
        
        liquidations = create_liquidations_v2(updated_trade_pair_hashmap, asset_mapping, scaled_collateral, scaled_debt)
        
        liquidations["scale"] = scale
        if liquidations:
            iteration_liquidations.append(liquidations)
    
    #convert iteration_liquidations to a dataframe
    iteration_liquidations_df = pd.DataFrame(iteration_liquidations)    
    
    return iteration_liquidations_df



def scale_price_and_identify_liquidatable_collateral(
    asset_data_df: pd.DataFrame,
    user_position_df: pd.DataFrame,
    new_price_mapping: Dict[str, float],
    emode_lt: float,
    subjected_token_symbol: str,
    lower_limit_scale: float,
    iterations: int
) -> pd.DataFrame:
    
    original_price = new_price_mapping[subjected_token_symbol]
    scale_series = np.linspace(lower_limit_scale, 1, iterations)
    
    liquidation_list = []
    
    # Add tqdm progress bar
    for scale in tqdm(scale_series, desc=f"Scaling {subjected_token_symbol} price", unit="scale"):
        new_price_mapping_loop = new_price_mapping.copy()
        new_price_mapping_loop[subjected_token_symbol] = original_price * scale
        # print(f"Applied {subjected_token_symbol} price: {new_price_mapping_loop[subjected_token_symbol]}")
        
        asset_mapping = create_asset_mapping(asset_data_df, new_price_mapping_loop)
        
        health_ratio_data_no_emode = create_health_ratio_data(user_position_df, asset_mapping)
        health_ratio_data_emode = create_health_ratio_data_emode(user_position_df, asset_mapping, emode_lt)
        health_ratio_data = pd.concat([health_ratio_data_no_emode, health_ratio_data_emode])
        
        health_ratio_data_filtered = health_ratio_data[health_ratio_data['health_ratio'] < 1]
        
        total_liquidatable_collateral, total_liquidatable_debt = create_liquidatable_user_data(health_ratio_data_filtered)

        liquidatable_collateral = total_liquidatable_collateral.get(subjected_token_symbol, 0)

        liquidation_dict = {
            'scale': scale,
            'liquidatable_collateral': liquidatable_collateral,
            'price': new_price_mapping_loop[subjected_token_symbol]
        }
        
        liquidation_list.append(liquidation_dict)
    
    liquidation_df = pd.DataFrame(liquidation_list) 
    
    return liquidation_df


def create_liquidatable_user_data_series(user_position_df: pd.DataFrame,
                                         asset_data_df: pd.DataFrame,
                                         new_price_mapping: Dict[str, float],
                                         emode_lt: float,
                                         subjected_token_symbol: str,
                                        lower_limit_scale: float,
                                        iterations: int,
                                         filter_usd: float) -> Tuple[Dict[str, float], Dict[str, float]]:
    
    scale_series = np.linspace(lower_limit_scale, 1, iterations)
    original_price = new_price_mapping[subjected_token_symbol]
    
    liquidation_data = []
    
    for scale in scale_series:
        new_price_mapping_loop = new_price_mapping.copy()
        new_price_mapping_loop[subjected_token_symbol] = original_price * scale
        
        record_loop = {
            'scale': scale,
            'price': new_price_mapping_loop[subjected_token_symbol],
        }
        
        asset_mapping = create_asset_mapping(asset_data_df, new_price_mapping_loop)
        
        health_ratio_data_no_emode = create_health_ratio_data(user_position_df, asset_mapping)
        print(health_ratio_data_no_emode.shape)

        health_ratio_data_emode = create_health_ratio_data_emode(user_position_df, asset_mapping, emode_lt)
        print(health_ratio_data_emode.shape)

        # concat health_ratio_data and health_ratio_data_emode
        health_ratio_data = pd.concat([health_ratio_data_no_emode, health_ratio_data_emode])
        
        total_liquidatable_collateral, total_liquidatable_debt = create_liquidatable_user_data(health_ratio_data)

            # Create a price mapping from asset_data_df
        price_mapping = dict(zip(asset_data_df['symbol'], asset_data_df['price']))

        # Modify total_liquidatable_collateral
        total_liquidatable_collateral_usd = {
            symbol: quantity * price_mapping.get(symbol, 1)  # Default to 1 if price not found
            for symbol, quantity in total_liquidatable_collateral.items()
        }

        # Modify total_liquidatable_debt
        total_liquidatable_debt_usd = {
            symbol: quantity * price_mapping.get(symbol, 1)  # Default to 1 if price not found
            for symbol, quantity in total_liquidatable_debt.items()
        }

        # Filter total_liquidatable_collateral and total_liquidatable_debt and only show values greater than 0
        total_liquidatable_collateral_usd = {k: v for k, v in total_liquidatable_collateral_usd.items() if v > 10000}
        total_liquidatable_debt_usd = {k: v for k, v in total_liquidatable_debt_usd.items() if v > filter_usd}

        record_loop["liquidatable_collateral"] = total_liquidatable_collateral_usd
        record_loop["liquidatable_debt"] = total_liquidatable_debt_usd
        
        liquidation_data.append(record_loop)
        
    return liquidation_data