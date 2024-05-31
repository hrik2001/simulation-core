from web3 import Web3
from core.models import ERC20, Chain, UniswapLPPosition
from core.pricing.univ3 import get_positions_details

# Define a minimal ABI to interact with an ERC20 token
erc20_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

def get_erc20_details(contract_address, w3):
    # Create a contract instance
    contract_address = Web3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=erc20_abi)
    
    # Fetch the details
    name = contract.functions.name().call()
    symbol = contract.functions.symbol().call()
    decimals = contract.functions.decimals().call()
    
    return {
        "name": name,
        "symbol": symbol,
        "decimals": decimals,
        "contract_address": contract_address
    }

def get_or_create_erc20(contract_address: str, chain: Chain):
    try:
        asset = ERC20.objects.get(contract_address__iexact=contract_address, chain=chain)
    except ERC20.DoesNotExist:
        response = get_erc20_details(contract_address, Web3(Web3.HTTPProvider(chain.rpc)))
        asset = ERC20(
            chain=chain,
            contract_address=contract_address,
            name=response["name"],
            symbol=response["symbol"],
            decimals=response["decimals"]
        )
        asset.save()
    return asset

def get_or_create_uniswap_lp(contract_address: str, chain: Chain, token_id: str | int):
    try:
        asset = UniswapLPPosition.objects.get(contract_address__iexact=contract_address, chain=chain, token_id=str(token_id))
    except UniswapLPPosition.DoesNotExist:
        w3 = Web3(Web3.HTTPProvider(chain.rpc))
        position_details = get_positions_details(
            contract_address,
            w3,
            int(token_id)
        )
        asset = UniswapLPPosition(
            contract_address = Web3.to_checksum_address(contract_address),
            token_id = str(token_id),
            chain = chain,
            liquidity = str(position_details["liquidity"]),
            tickLower = str(position_details["tickLower"]),
            tickUpper = str(position_details["tickUpper"]),
            token1 = ERC20.objects.get(contract_address__iexact=position_details["token1"]),
            token0 = ERC20.objects.get(contract_address__iexact=position_details["token0"]),
            name = f"{Web3.to_checksum_address(contract_address)}-{str(token_id)}",
            symbol = f"{Web3.to_checksum_address(contract_address)}-{str(token_id)}",
        )
        asset.save()
    return asset