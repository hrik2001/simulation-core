"""Simple DTO for token data."""
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any

import numpy as np
import pandas as pd
from requests import get, post, ConnectionError, Timeout, RequestException
from scipy.optimize import curve_fit
from tqdm import tqdm

from core.models import Chain
from curve.simuliq.models.token import TokenDTO


# TokenDTO
# address: str
# name: str
# symbol: str
# decimals: int
# network: ChainDTO
# price: float = field(init=False)
# supply: int = field(init=False)
# timestamp: Optional[int] = None

# def derived_func(x, r, k, c):
#     """
#     Calculate the value of y based on the given formula.

#     Parameters:
#         x (float): The value of x in the formula.
#         r (float): The value of r in the formula.
#         k (float): The value of k in the formula.
#         c (float): The value of c in the formula.

#     Returns:
#         float: The calculated value of y.
#     """
#     exponent = k * (x ** -c)
#     y = (x * r) * (1 - (1/np.exp(exponent)))
#     return y

def derived_func(x, r, k, c):
    try:
        # Convert inputs to numpy arrays
        x = np.array(x)
        r = np.array(r)
        k = np.array(k)
        c = np.array(c)

        # Handle cases where x <= 0 or c == 0
        mask = (x > 0) & (c != 0)
        y = np.zeros_like(x)

        # Calculate only for valid inputs
        exponent = np.where(mask, k * (x ** -c), 0)
        
        # Handle large exponents to avoid overflow
        large_exp_mask = exponent > 700
        y[large_exp_mask] = x[large_exp_mask] * r

        # Calculate for normal cases
        normal_mask = mask & ~large_exp_mask
        y[normal_mask] = (x[normal_mask] * r) * (1 - (1/np.exp(exponent[normal_mask])))

        return y
    except Exception as e:
        logging.error(f"Error in derived_func: {str(e)}, x={x}, r={r}, k={k}, c={c}")
        return np.zeros_like(x)

@dataclass()
class PairDTO:
    """
    Data Transfer Object to store relevant
    token data.
    """
    sell_token: TokenDTO
    buy_token: TokenDTO
    chain: Chain
    exchange_price: float = field(init=False)
    k: float = field(init=False)
    c: float = field(init=False)
    quotes_df: pd.DataFrame = field(init=False)
    
    new_exchange_price: Optional[float] = None
    new_k: Optional[float] = None
    new_c: Optional[float] = None
    
    timestamp: Optional[int] = None

    def __post_init__(self):
        """Initialize the PairDTO with computed values."""
        self.exchange_price = self.compute_exchange_price()
        
        # Initialize with None first
        self.quotes_df = None
        self.k = None
        self.c = None
        
        if self.exchange_price is not None:
            # Get quotes and verify we have valid data
            quotes_df = self.get_quotes_aggregator()
            if quotes_df is not None and not quotes_df.empty and 'sell_token_amount' in quotes_df.columns:
                self.quotes_df = quotes_df
                self.k, self.c = self.get_function_constants_with_df(quotes_df)
            
        # Initialize new values with current values
        self.new_exchange_price = self.exchange_price
        self.new_k = self.k
        self.new_c = self.c
    
    def is_valid(self) -> bool:
        """Check if the PairDTO has all required data."""
        return all([
            self.exchange_price is not None,
            self.quotes_df is not None,
            not self.quotes_df.empty,
            self.k is not None,
            self.c is not None
        ])
        
    def compute_exchange_price(self) -> Optional[float]:
        
        '''
        If sell token is USDC and buy token is ETH, 
        then the exchange price is the ETH price in USD
        i.e. (USD/ETH) / (USD/USDC) = USDC/ETH
        if ETH is $2000, and USDC is $1.01, then 1 ETH = ~1980.2 USDC
        exchnage price is thus 1980.2 which is nothing but 2000/1.01
        '''
        
        if self.buy_token.price is None or self.sell_token.price is None:
            return None
        if self.sell_token.price == 0:
            return None
        return  self.sell_token.price / self.buy_token.price
    
    
    
    def kyberswap_quote(self, sell_amount: float) -> Dict[str, Any]:
        
        sell_token = self.sell_token.address
        sell_token_decimals = self.sell_token.decimals
        sell_token_price = self.sell_token.price
        
        buy_token = self.buy_token.address
        buy_token_decimals = self.buy_token.decimals
        buy_token_price = self.buy_token.price
        
        network_id = 1

        network = self.chain.chain_name.lower()
        
        api_url = f"https://aggregator-api.kyberswap.com/{network}/api/v1/routes"

        
        # Construct the request parameters
        params = {
            "tokenIn": sell_token,
            "amountIn": int(sell_amount * (10 ** sell_token_decimals)),
            "tokenOut": buy_token,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            # Make the API request
            response = get(api_url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors

            if response.status_code == 200:
                # logging.info(f"Kyberswap Response +ve")
                quote_raw = response.json()

                # extract
                sell_token_amount = float(quote_raw['data']['routeSummary']['amountIn'])
                buy_token_amount = float(quote_raw['data']['routeSummary']['amountOut'])
                aggregator = str('kyberswap')

                # format row 
                row = {
                    "network": network_id,
                    "dex_aggregator": aggregator,
                     
                    "sell_token": sell_token,
                    "sell_token_decimals": sell_token_decimals,
                    "sell_token_amount": sell_token_amount,
                    "sell_token_price": sell_token_price,
                    
                    "buy_token": buy_token,
                    "buy_token_decimals": buy_token_decimals,
                    "buy_token_amount": buy_token_amount,
                    "buy_token_price": buy_token_price,
                }

                return row
        
        except ConnectionError as ce:
            print(f"Connection error: {ce}")
            return {"error": "ConnectionError", "message": str(ce)}
        except Timeout as te:
            print(f"Timeout error: {te}")
            return {"error": "TimeoutError", "message": str(te)}
        except RequestException as re:
            print(f"Request exception: {re}")
            return {"error": "RequestException", "message": str(re)}
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {"error": "UnexpectedError", "message": str(e)}
    
    
    def paraswap_quote(self, sell_amount: float) -> Dict[str, Any]:
    
        sell_token = self.sell_token.address
        sell_token_decimals = self.sell_token.decimals
        sell_token_price = self.sell_token.price
        
        buy_token = self.buy_token.address
        buy_token_decimals = self.buy_token.decimals
        buy_token_price = self.buy_token.price
        
        network_id = 1

        network = self.chain.chain_name.lower()
        
        api_url = "https://api.paraswap.io/swap"
        
        # Construct the request parameters
        params = {
            "userAddress": "0x3727cfCBD85390Bb11B3fF421878123AdB866be8",
            "srcToken": sell_token,
            "srcDecimals": sell_token_decimals,
            "destToken": buy_token,
            "destDecimals": buy_token_decimals,
            "amount": f"{int(sell_amount * (10 ** sell_token_decimals))}",
            "side": "SELL",
            "network": str(network_id),
            "slippage": 9999,  # 100% slippage tolerance
            "maxImpact": 100
        }
    
        try:
            # Make the API request
            response = get(api_url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors

            if 'priceRoute' in response.json():
                # logging.info(f"Paraswap Response +ve")
                quote_raw = response.json()['priceRoute']

                # extract
                sell_token_amount = float(quote_raw['srcAmount'])
                buy_token_amount = float(quote_raw['destAmount'])
                aggregator = str('paraswap')
                              
                # format row 
                row = {
                    "network": network_id,
                    "dex_aggregator": aggregator,
                     
                    "sell_token": sell_token,
                    "sell_token_decimals": sell_token_decimals,
                    "sell_token_amount": sell_token_amount,
                    "sell_token_price": sell_token_price,
                    
                    "buy_token": buy_token,
                    "buy_token_decimals": buy_token_decimals,
                    "buy_token_amount": buy_token_amount,
                    "buy_token_price": buy_token_price,
                }

                return row

        except ConnectionError as ce:
            print(f"Connection error: {ce}")
            return {"error": "ConnectionError", "message": str(ce)}
        except Timeout as te:
            print(f"Timeout error: {te}")
            return {"error": "TimeoutError", "message": str(te)}
        except RequestException as re:
            print(f"Request exception: {re}")
            return {"error": "RequestException", "message": str(re)}
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {"error": "UnexpectedError", "message": str(e)}
        

    def conveyor_finance_quote(self, sell_amount: float) -> Dict[str, Any]:
        sell_token = self.sell_token.address
        sell_token_decimals = self.sell_token.decimals
        sell_token_price = self.sell_token.price
        
        buy_token = self.buy_token.address
        buy_token_decimals = self.buy_token.decimals
        buy_token_price = self.buy_token.price
        
        network_id = 1
        
        api_url = "https://api.conveyor.finance"
        
        # Construct the request parameters
        params = {
            "tokenIn": sell_token,
            "tokenOut": buy_token,
            "tokenInDecimals": sell_token_decimals,
            "tokenOutDecimals": buy_token_decimals,
            "amountIn": str(int(sell_amount * (10 ** sell_token_decimals))),
            "slippage": "100",  # Set appropriate slippage value as needed
            "chainId": network_id,
            "recipient": "0xD65e57395288AA88f99F8e52D0A23A551E0Ad6Ac",
            "partner": "Caddi"
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            # Make the API request
            response = post(api_url, headers=headers, json=params)
            response.raise_for_status()  # Raise an exception for HTTP errors

            if response.status_code == 200:
                # logging.info(f"Conveyor Finance Response +ve")
                quote_raw = response.json()

                # extract
                # sell_token_amount = float(quote_raw['body']['info']['amountOutMin'])/(10 ** sell_token_decimals)
                buy_token_amount = float(quote_raw['body']['info']['amountOut']) #/(10 ** buy_token_decimals)
                aggregator = str('conveyor_finance')

                # format row 
                row = {
                    "network": self.chain.chain_name,
                    "dex_aggregator": aggregator,
                    
                    "sell_token": sell_token,
                    "sell_token_decimals": sell_token_decimals,
                    "sell_token_amount": int(sell_amount * (10 ** sell_token_decimals)),
                    "sell_token_price": sell_token_price,
                    
                    "buy_token": buy_token,
                    "buy_token_decimals": buy_token_decimals,
                    "buy_token_amount": buy_token_amount,
                    "buy_token_price": buy_token_price,
                }

                return row
        
        except ConnectionError as ce:
            print(f"Connection error: {ce}")
            return {"error": "ConnectionError", "message": str(ce)}
        except Timeout as te:
            print(f"Timeout error: {te}")
            return {"error": "TimeoutError", "message": str(te)}
        except RequestException as re:
            print(f"Request exception: {re}")
            return {"error": "RequestException", "message": str(re)}
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {"error": "UnexpectedError", "message": str(e)}


    def get_quotes_aggregator(self, samples=20):
        new_rows_list = []
        
        sell_token = self.sell_token
        buy_token = self.buy_token

        # Fetch sell token price 
        price = sell_token.price
        
        min_mc = min(sell_token.mcap, buy_token.mcap)
        
        # print(f"[{sell_token.symbol} -> {buy_token.symbol}] | sell_token.mcap: {sell_token.mcap} | buy_token.mcap: {buy_token.mcap}")
        
        start_amount = (min_mc * 0.0001)/sell_token.price # 1% of the smaller token's TVL
        end_amount = (min_mc * 0.10)/sell_token.price # 70% of the smaller token's TVL

        amounts = np.geomspace(start_amount, end_amount, num=samples).astype(float).tolist()

        # Iterate through the generated amounts and fetch quotes
        for amount in tqdm(amounts, desc=f"Fetching quotes for {sell_token.symbol} -> {buy_token.symbol}", leave=False):
            try:                
                new_row = self.paraswap_quote(amount)
                # new_row2 = self.kyberswap_quote(amount)
                # new_row3 = self.conveyor_finance_quote(amount)  # Adding Conveyor Finance

                # Append quotes to the list
                new_rows_list.append(new_row)
                # new_rows_list.append(new_row2)
                # new_rows_list.append(new_row3)

            except Exception as e:
                print(f"Failed to save entry to DB: {e}")

            time.sleep(1.2)  # Adjust the sleep duration if necessary

        df = pd.DataFrame(new_rows_list)
        return df
        
        # @lru_cache(maxsize=1000)
        # def get_quotes_aggregator(self, samples=25):
            
        #     stopping_criteria = 0 
        #     new_rows_list = []
            
        #     sell_token = self.sell_token
        #     buy_token = self.buy_token

        #     # Fetch sell token price 
        #     price = sell_token.price
            
        #     min_mc = min(sell_token.mcap, buy_token.mcap)
            
        #     print(f"[{sell_token.symbol} -> {buy_token.symbol}] | sell_token.mcap: {sell_token.mcap} | buy_token.mcap: {buy_token.mcap}")
            
        #     start_amount = (min_mc * 0.01)/sell_token.price # 10% of the smaller token's TVL
        #     end_amount = (min_mc * 0.7)/sell_token.price # 70% of the smaller token's TVL
        #     amounts = np.geomspace(start_amount, end_amount, num=samples).astype(float).tolist()

        #     # Iterate through the generated amounts and fetch quotes
        #     for amount in amounts:

        #         # Add a print statement to check the amount
        #         # logging.info(f"Fetching Quotes[{sell_token.symbol} -> {buy_token.symbol}] || Amount: {amount}")
        #         try:                
        #             new_row = self.paraswap_quote(amount)
        #             # new_row2 = self.kyberswap_quote(amount)

        #             # new_row is a dictionary, create a list of dictionaries and append new_row to new_rows_list
        #             new_rows_list.append(new_row)
        #             # new_rows_list.append(new_row2)

        #         except Exception as e:
        #             print(f"Failed to save entry to DB: {e}")

        #         # Early stopping criteria 
        #         if stopping_criteria > 0.99: 
        #             break
        #         else:
        #             # Sleep for a short duration to avoid hitting the rate limit of the API
        #             time.sleep(1.1)  # Adjust the sleep duration if necessary
        
        #     df = pd.DataFrame(new_rows_list)
        #     return df
        

        
    # @lru_cache(maxsize=1000)
    def get_function_constants_with_df(self, quotes_df):
        if self.exchange_price is None:
            return None, None
            
        exchange_price = self.compute_exchange_price()
        
        # # Extract data from DataFrame
        # x_data = quotes_df['sell_token_amount'].values / pow(10, quotes_df['sell_token_decimals'].iloc[0])
        # y_data = quotes_df['buy_token_amount'].values / pow(10, quotes_df['buy_token_decimals'].iloc[0])
        
        # Convert to numeric values explicitly
        x_data = pd.to_numeric(quotes_df['sell_token_amount'].values, errors='coerce') / float(pow(10, quotes_df['sell_token_decimals'].iloc[0]))
        y_data = pd.to_numeric(quotes_df['buy_token_amount'].values, errors='coerce') / float(pow(10, quotes_df['buy_token_decimals'].iloc[0]))
    
        
        
        # Remove inf and NaN values
        mask = np.isfinite(x_data) & np.isfinite(y_data)
        x_data = x_data[mask]
        y_data = y_data[mask]
        
        # Check if we have enough data points after filtering
        if len(x_data) < 2:
            print("Error: Not enough valid data points for curve fitting.")
            return None, None
        
        initial_guess = [1.0, 1.0]  # [B, c]
        bounds = ([0, 0], [np.inf, np.inf])
        try:
            popt, pcov = curve_fit(
                lambda x, k, c: derived_func(x, exchange_price, k, c),
                x_data, y_data,
                p0=initial_guess,
                bounds=bounds,
                maxfev=10000  # Increase max function evaluations
            )
        except RuntimeError as e:
            print(f"Error: Curve fit failed. {str(e)}")
            return None, None
        except ValueError as e:
            print(f"Error: Invalid values in data. {str(e)}")
            return None, None
        
        k, c = popt
        return k, c