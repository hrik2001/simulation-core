import requests
from requests.exceptions import ConnectionError, Timeout, RequestException, HTTPError
from typing import Dict, Any, Optional

class RateLimitExceededException(Exception):
    """Exception raised for rate limit exceeded (429 Too Many Requests)."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message)
        self.retry_after = retry_after

def get_current_price(token_address: str, network: str) -> Optional[float]:
    """
    Fetches the current price of a token from the Coin Llama API and extracts the price.

    Args:
        token_address (str): The address of the token.
        network (str): The network identifier (e.g., 'arbitrum').

    Returns:
        Optional[float]: The current price of the token or None if an error occurs.
    """
    base_url = "https://coins.llama.fi/prices/current"
    url = f"{base_url}/{network}:{token_address}?searchWidth=1h"

    print(url)
    
    response = requests.get(url)
    if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitExceededException("Rate limit exceeded.", retry_after=int(retry_after) if retry_after else None)
    response.raise_for_status()  # Raise an exception for HTTP errors

    data = response.json()
    price_info = data.get('coins', {}).get(f'{network}:{token_address}', {})
    return price_info.get('price')


# Example usage
# price = get_current_price(
#     token_address="0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
#     network="arbitrum"
# )
# if price is not None:
#     print(f"The current price is: {price}")
# else:
#     print("Failed to fetch the current price.")
