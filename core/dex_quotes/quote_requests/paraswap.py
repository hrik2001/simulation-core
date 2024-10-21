from datetime import datetime, timedelta
from typing import Any, Dict

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout


def get_quote(
    src_token: str,
    src_decimals: int,
    dest_token: str,
    dest_decimals: int,
    usd_amount: float,
    market_price: float,
    network_id: int,
) -> Dict[str, Any]:
    """
    Fetches the swap rate between two tokens using the ParaSwap API.

    Args:
        src_token (str): The address of the source token.
        src_decimals (int): The number of decimals for the source token.
        dest_token (str): The address of the destination token.
        dest_decimals (int): The number of decimals for the destination token.
        amount (float): The amount of the source token to swap.
        network (str): The network identifier (e.g., '1' for Ethereum Mainnet).

    Returns:
        Dict[str, Any]: A dictionary containing the response from the ParaSwap API or an error message.

    For more details refer to: https://developers.paraswap.network/api/get-rate-for-a-token-pair-1
    """
    api_url = "https://api.paraswap.io/swap"

    # Construct the request parameters
    params = {
        "userAddress": "0x3727cfCBD85390Bb11B3fF421878123AdB866be8",
        "srcToken": src_token,
        "srcDecimals": src_decimals,
        "destToken": dest_token,
        "destDecimals": dest_decimals,
        "amount": f"{int((usd_amount/market_price) * (10 ** src_decimals))}",
        "side": "SELL",
        "network": str(network_id),
        "slippage": 9999,  # 100% slippage tolerance
        "maxImpact": 100,
    }

    try:
        # Make the API request
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        if "priceRoute" in response.json():
            quote_raw = response.json()["priceRoute"]

            # extract
            src_amount = float(quote_raw["srcAmount"])
            dest_amount = float(quote_raw["destAmount"])
            src_usd = float(quote_raw["srcUSD"])
            dest_usd = float(quote_raw["destUSD"])
            aggregator = str("paraswap")

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
                "price": (src_amount / (10**src_decimals))
                / (dest_amount / (10**dest_decimals)),  # execution_price"
                "price_impact": (src_usd - dest_usd) / src_usd,  # impact_cost
                "timestamp": round(
                    (datetime.now() + timedelta(minutes=30))
                    .replace(minute=0, second=0, microsecond=0)
                    .timestamp()
                ),
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
# quote_paraswap = get_paraswap_rate(
#     src_token="0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
#     src_decimals=18,
#     dest_token="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
#     dest_decimals=6,
#     amount=50_000_000,
#     network="42161"
# )
