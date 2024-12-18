import pandas as pd
import json

def compute_health_yellow_sl_efficiency(debt, 
                                        collateral, 
                                        oracle_price, 
                                        base_price, 
                                        start_band, 
                                        finish_band, 
                                        A, 
                                        liq_discount, 
                                        soft_liq_efficiency):
    
    # Compute the range and band data
    bands = abs(finish_band - start_band + 1)
    band_collateral = float(collateral) / float(bands)
    total_discounted_value = 0
    new_collateral_value = 0
    new_crvusd_value = 0

    # Iterate through each band to calculate the discounted value in bands
    for i in range(start_band, finish_band + 1):
        x_min = base_price * ((A - 1) / A)**(i + 1)
        x_max = base_price * ((A - 1) / A)**i
        avg_sell_price = (x_max + x_min) / 2
        
        if oracle_price <= x_min:
            # Adjust collateral for soft liquidation losses
            effective_band_collateral = band_collateral * soft_liq_efficiency
            collat_value = avg_sell_price * effective_band_collateral
            discounted_collat_value = collat_value * (1 - liq_discount / 100)
            new_crvusd_value += effective_band_collateral
        
        else:
            effective_band_collateral = band_collateral
            collat_value = avg_sell_price * effective_band_collateral
            discounted_collat_value = collat_value * (1 - liq_discount / 100)
            new_collateral_value += band_collateral
            
        
        total_discounted_value += discounted_collat_value

    # Calculate healthYellow
    health_yellow = (total_discounted_value / debt - 1) * 100
    
    return health_yellow, new_collateral_value, new_crvusd_value

def compute_price_for_max_hard_liq_row(row, market_params, soft_liq_efficiency):
    
    start_band = row['n1']
    finish_band = row['n2']
    collateral = row['collateral']
    base_price = market_params['base_price']
    A = market_params['A']
    liq_discount = market_params['liq_discount']
    debt = row['debt']
    
    # Compute the range and band data
    bands = abs(finish_band - start_band + 1)
    band_collateral = float(collateral) / float(bands)
    avg_price = []

    # Iterate through each band to calculate the discounted value in bands
    for i in range(start_band-1, finish_band + 1):
        
        price_dict = {}
        
        x_min = base_price * ((A - 1) / A)**(i + 1)
        x_max = base_price * ((A - 1) / A)**i
        avg_sell_price = (x_max + x_min) / 2
        
        price_dict['price'] = avg_sell_price
        
        health_yellow, new_collateral_value, new_crvusd_value = compute_health_yellow_sl_efficiency(debt,
                                                                                                    collateral,
                                                                                                    avg_sell_price,
                                                                                                    base_price,
                                                                                                    start_band,
                                                                                                    finish_band,
                                                                                                    A,
                                                                                                    liq_discount,
                                                                                                    soft_liq_efficiency)
        
        price_dict['health'] = health_yellow
        price_dict['new_collateral_value'] = new_collateral_value
        price_dict['new_crvusd_value'] = new_crvusd_value
        
        # Append the price dictionary to the list
        avg_price.append(price_dict)
        
    # Find dictionaries with health < 0
    negative_health_prices = [price_dict for price_dict in avg_price if price_dict['health'] < 0]

    # If no prices with negative health found, return None
    if not negative_health_prices:
        return None, None, None

    # Find the dictionary with maximum new_collateral_value among negative health entries
    max_price_dict = max(negative_health_prices, key=lambda x: x['new_collateral_value'])

    # Return the values from the found dictionary
    max_price = max_price_dict['price']
    max_collateral_value = max_price_dict['new_collateral_value']
    max_crvusd_value = max_price_dict['new_crvusd_value']
    health = max_price_dict['health']

    return max_price, max_collateral_value, max_crvusd_value, health
    
    
def compute_price_for_max_hard_liq(df_wbtc_users,
                                   market_params,
                                   soft_liq_efficiency):
    
    return_list = []
    
    for _, row in df_wbtc_users.iterrows():
        debt = row['debt']
        return_dict = {}
        
        max_price, max_collateral_value, max_crvusd_value, health = compute_price_for_max_hard_liq_row(row, market_params, soft_liq_efficiency)
        return_dict['index'] = _
        return_dict['max_price'] = max_price
        return_dict['max_collateral_value'] = max_collateral_value
        # return_dict['max_crvusd_value'] = max_crvusd_value
        return_dict['debt'] = debt - max_crvusd_value
        
        return_dict['debt_raw'] = debt
        return_dict['max_crvusd_value'] = max_crvusd_value
        
        return_list.append(return_dict)
        
    return_df = pd.DataFrame(return_list)
    
    # print(json.dumps(return_df.to_dict(), indent=4))
    
    
        # Group by max_price and sum both max_collateral_value and debt
    return_df_grouped = return_df.groupby('max_price').agg({
        'max_collateral_value': 'sum',
        'debt': 'sum'
    }).reset_index()
    
    return return_df_grouped, return_df
    
    