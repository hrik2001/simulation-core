import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from typing import Dict, Any
from datetime import datetime, timedelta
from ..DTO import network_mapping


def get_quote(
    src_token: str, 
    src_decimals: int, 
    dest_token: str, 
    dest_decimals: int, 
    usd_amount: float, 
    market_price: float,
    network_id: int
) -> Dict[str, Any]:
    """
    Fetches the swap rate between two tokens using the KyberSwap API.

    Args:
        src_token (str): The address of the source token.
        src_decimals (int): The number of decimals for the source token.
        dest_token (str): The address of the destination token.
        dest_decimals (int): The number of decimals for the destination token.
        usd_amount (float): The amount of USD to swap.
        market_price (float): The current market price of the source token.
        network (str): The network identifier (e.g., '42161' for Arbitrum).

    Returns:
        Dict[str, Any]: A dictionary containing the response from the KyberSwap API or an error message.
    """

    network = network_mapping[network_id].network.lower()
    api_url = f"https://aggregator-api.kyberswap.com/{network}/api/v1/routes"

    # Calculate the amount of the source token to swap


    # Construct the request parameters
    params = {
        "tokenIn": src_token,
        "amountIn":  int((usd_amount / market_price) * (10 ** src_decimals)),
        "tokenOut": dest_token,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        # Make the API request
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        if response.status_code == 200:
            quote_raw = response.json()

            # extract
            src_amount = float(quote_raw['data']['routeSummary']['amountIn'])
            dest_amount = float(quote_raw['data']['routeSummary']['amountOut'])
            src_usd = float(quote_raw['data']['routeSummary']['amountInUsd']) 
            dest_usd = float(quote_raw['data']['routeSummary']['amountOutUsd']) 
            aggregator = str('kyberswap')

            # format row 
            row = {
                "network": network_id,
                "dex_aggregator": aggregator, 
                "src": src_token,
                "src_decimals": src_decimals,
                "dst": dest_token,
                "dest_decimals": dest_decimals,
                "in_amount_usd": usd_amount,
                "in_amount": src_amount, 
                "out_amount": dest_amount,
                "market_price": market_price, 
                "price": (src_amount/(10**src_decimals)) / (dest_amount/(10**dest_decimals)), #execution_price
                "price_impact": (src_usd-dest_usd) / src_usd, #impact_cost
                "timestamp": round((datetime.now() + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0).timestamp())
            }

            # print(row)

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

# Example usage
# quote_kyberswap = get_quote(
#     src_token="0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
#     src_decimals=18,
#     dest_token="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
#     dest_decimals=6,
#     usd_amount=100.0,
#     market_price=1.0,
#     network='arbitrum'
# )
