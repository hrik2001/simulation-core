import dotenv
import pandas as pd
import os
import requests
from typing import Optional, Dict

from core.models import Chain
from curve.simuliq.models.curve_protocol import CurveMintMarketDTO

dotenv.load_dotenv()

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
                
        return response.json()['data']
        
    except requests.RequestException as e:
        return None


market_data = fetch_curve_market_data()

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

