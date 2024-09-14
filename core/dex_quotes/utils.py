from core.dex_quotes.DTO import TokenDTO
from web3 import Web3
from core.models import Chain
from .price_fetcher import get_current_price
import numpy as np


def query_token_supply(dto: TokenDTO, *args, block_number=None):
    """
    Query a smart contract function.

    :param w3: Web3 instance
    :param contract_address: Address of the smart contract
    :param abi: ABI of the smart contract
    :param function_name: Name of the function to query
    :param args: Arguments to pass to the function (if any)
    :param block_number: Specific block number to query (optional)
    :return: Result of the function call or an error message
    """
    contract_address = dto.address
    
    w3 = Web3(Web3.HTTPProvider(Chain.objects.get(chain_name__iexact=dto.network.network).rpc))
    abi = [
            {
            "stateMutability": "view",
            "type": "function",
            "name": "totalSupply",
            "inputs": [],
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}]
        }
    ]
    
    try:
        # Create contract instance
        contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
        
        # Get the contract function
        contract_function = getattr(contract.functions, "totalSupply")
        
        # Call the function with arguments and block identifier if provided
        if block_number is not None:
            data = contract_function(*args).call(block_identifier=int(block_number))
        else:
            data = contract_function(*args).call()
        
        return data
    
    except Exception as e:
        return f'Error querying smart contract: {e}'

def compute_tvl(token: TokenDTO):
    supply = query_token_supply(token)/pow(10, token.decimals)
    price = get_current_price(token.address, token.network.network.lower())
    tvl = supply * price
    return tvl
    
def compute_sampling_points(sell_token: TokenDTO, buy_token: TokenDTO, num_samples: int):
    
    sell_token_tvl = compute_tvl(sell_token)
    buy_token_tvl = compute_tvl(buy_token)
    
    start_amount = min(sell_token_tvl, buy_token_tvl) * 0.001 # 0.1% of the smaller token's TVL
    end_amount = min(sell_token_tvl, buy_token_tvl) * 0.75 # 75% of the smaller token's TVL
    
    amounts = np.geomspace(start_amount, end_amount, num=num_samples).astype(int).tolist()
    
    return amounts