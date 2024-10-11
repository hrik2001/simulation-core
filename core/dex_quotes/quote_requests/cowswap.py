import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from typing import Dict, Any
from datetime import datetime, timedelta

def get_quote(
    src_token: str, 
    src_decimals: int, 
    dst_token: str, 
    dst_decimals: int, 
    src_usd_amount: float, 
    src_price: float,
    dst_price: float,
    network_id: int
) -> Dict[str, Any]:
    """
    Fetches the swap rate between two tokens using the 1inch API.

    Args:
        src_token (str): The address of the source token.
        src_decimals (int): The number of decimals for the source token.
        dst_token (str): The address of the destination token.
        dst_decimals (int): The number of decimals for the destination token.
        src_usd_amount (float): USD amount of the source token to swap.
        src_price (float): USD price of the source token.
        dst_price (float): USD price of the destination token.
        network_id (int): The network identifier (e.g., '1' for Ethereum Mainnet).

    Returns:
        Dict[str, Any]: A dictionary containing the response from the ParaSwap API or an error message.

    For more details refer to: https://developers.paraswap.network/api/get-rate-for-a-token-pair-1
    """

    network = ""
    if network_id == 1:
        network = "mainnet"
    elif network_id == 42161:
        network = "arbitrum"
    else:
        return {"error": "Argument error", "message": "unsupported network ['mainnet','arbitrum']"}

    body = {
        "sellToken": src_token,
        "buyToken": dst_token,
        "receiver": "0x3727cfCBD85390Bb11B3fF421878123AdB866be8",
        "appData": "{\"version\":\"0.9.0\",\"metadata\":{}}",
        "appDataHash": "0xc990bae86208bfdfba8879b64ab68da5905e8bb97aa3da5c701ec1183317a6f6",
        "sellTokenBalance": "erc20",
        "buyTokenBalance": "erc20",
        "from": "0x3727cfCBD85390Bb11B3fF421878123AdB866be8",
        "priceQuality": "verified",
        "signingScheme": "eip712",
        "onchainOrder": False,
        "kind": "sell",
        "sellAmountBeforeFee": f"{int((src_usd_amount/src_price) * (10 ** src_decimals))}"
    }

    try:
        response = requests.post(f'https://api.cow.fi/{network}/api/v1/quote', json=body)
        response.raise_for_status()
        data = response.json()['quote']

        dst_usd_amount = float(data['buyAmount']) * dst_price / (10 ** dst_decimals)

        return {
            "network": network_id,
            "dex_aggregator": "cowswap", 
            "src": src_token,
            "src_decimals": src_decimals,
            "dst": dst_token,
            "dest_decimals": dst_decimals,
            "in_amount_usd": src_usd_amount,
            "in_amount": data['sellAmount'], 
            "out_amount": data['buyAmount'],
            "market_price": src_price, 
            "price": (float(data['sellAmount'])/(10**src_decimals)) / (float(data['buyAmount'])/(10**dst_decimals)),
            "price_impact": (src_usd_amount-dst_usd_amount) / src_usd_amount, # calculate the price impact
            "timestamp": round((datetime.now() + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0).timestamp())
        }

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
