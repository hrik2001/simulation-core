import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from typing import Dict, Any
from datetime import datetime, timedelta
import urllib.parse
import hashlib
import base64
import hmac
import json

def get_okx_auth_signature(now, method, url, params, okx_secret):
    input_string = f'{now}{method}{url}?{urllib.parse.urlencode(params)}'
    hmac_hash = hmac.new(okx_secret.encode(), input_string.encode(), hashlib.sha256).digest()
    return base64.b64encode(hmac_hash).decode()

def get_dex_ids(
    okx_project_id: str,
    okx_api_key: str,
    okx_passphrase: str,
    okx_secret: str,
    network_id=1):

    if network_id not in [1, 10, 42161, 8453]: # only allow ethereum, optimism, arbitrum and base
        return {"error": "Argument error", "message": "unsupported network ['ethereum','optimism','arbitrum','base']"}

    urlPath = "/api/v5/dex/aggregator/get-liquidity"

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z';

    params = {"chainId": str(network_id)}

    headers = {
        'OK-ACCESS-PROJECT': okx_project_id,
        'OK-ACCESS-KEY': okx_api_key,
        'OK-ACCESS-TIMESTAMP': now,
        'OK-ACCESS-PASSPHRASE': okx_passphrase,
        'OK-ACCESS-SIGN': get_okx_auth_signature(now, 'GET', urlPath, params, okx_secret)}

    try:
        response = requests.get("https://www.okx.com" + urlPath, params=params, headers=headers)
        response.raise_for_status()

        dex_ids = []
        for e in response.json()['data']:
            dex_ids.append(int(e['id']))
        return dex_ids

    except requests.exceptions.RequestException as e:
        print(f"Error fetching DEX IDs: {e}")
        return None

def get_quote(
    okx_project_id: str,
    okx_api_key: str,
    okx_passphrase: str,
    okx_secret: str,
    src_token: str, 
    dst_token: str, 
    src_amount: int, 
    network_id: int,
    dex_ids: [],
) -> Dict[str, Any]:
    """
    Fetches the swap rate between two tokens using the OKX aggregator API.

    Args:
        okx_project_id (str): The OKX project ID
        okx_api_key (str): The OKX API key
        okx_passphrase (str): The OKX passphrase for the API key
        okx_secret (str): The OKX secret for the API key
        src_token (str): The address of the source token
        dst_token (str): The address of the destination token
        src_amount (int): Amount of token to sell
        network_id (int): The network identifier (e.g., '1' for Ethereum Mainnet)
        dex_ids (int[]): The dex IDs to use for getting the quote

    Returns:
        Dict[str, Any]: A dictionary containing the response or an error message.

    For more details refer to: https://www.okx.com/web3/build/docs/waas/dex-get-quote
    """

    if network_id not in [1, 10, 42161, 8453]: # only allow ethereum, optimism, arbitrum and base
        return {"error": "Argument error", "message": "unsupported network ['ethereum','optimism','arbitrum','base']"}

    urlPath = '/api/v5/dex/aggregator/quote'

    params = {
        "chainId": str(network_id),
        "amount": str(src_amount),
        "fromTokenAddress": src_token,
        "toTokenAddress": dst_token,
        "dexIds": ",".join(map(str, dex_ids)),
        "priceImpactProtectionPercentage": "1.0", # disable price impact protection
    }

    now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z';

    headers = {
        'OK-ACCESS-PROJECT': okx_project_id,
        'OK-ACCESS-KEY': okx_api_key,
        'OK-ACCESS-TIMESTAMP': now,
        'OK-ACCESS-PASSPHRASE': okx_passphrase,
        'OK-ACCESS-SIGN': get_okx_auth_signature(now, 'GET', urlPath, params, okx_secret),
    }

    try:
        response = requests.get('https://www.okx.com' + urlPath, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()['data'][0]

        dst_amount = int(data['toTokenAmount'])
        src_decimal = int(data['fromToken']['decimal'])
        dst_decimal = int(data['toToken']['decimal'])
        src_amount_usd = src_amount / 10**src_decimal * float(data['fromToken']['tokenUnitPrice'])
        dst_amount_usd = int(data['toTokenAmount']) / (10 ** dst_decimal) * float(data['toToken']['tokenUnitPrice'])

        return {
            "network": network_id,
            "dex_aggregator": "okx",
            "src": src_token,
            "src_decimals": src_decimal,
            "dst": dst_token,
            "dest_decimals": dst_decimal,
            "in_amount_usd": src_amount_usd,
            "in_amount": src_amount, 
            "out_amount": dst_amount,
            "market_price": float(data['fromToken']['tokenUnitPrice']), 
            "price": (float(src_amount) / dst_amount),
            "price_impact": (src_amount_usd-dst_amount_usd) / src_amount_usd, # calculate the price impact
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
