import requests
from web3 import Web3
from core.models import ERC20, Chain, UniswapLPPosition
from core.pricing.univ3 import get_positions_details
from datetime import datetime
from time import sleep

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
        if position_details is None:
            return None
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

def update_uniswap_lp(asset: UniswapLPPosition):
    # asset = UniswapLPPosition.objects.get(contract_address__iexact=contract_address, chain=chain, token_id=str(token_id))
    w3 = Web3(Web3.HTTPProvider(asset.chain.rpc))
    position_details = get_positions_details(
        asset.contract_address,
        w3,
        int(asset.token_id)
    )
    asset.liquidity = str(position_details["liquidity"]),
    asset.tickLower = str(position_details["tickLower"]),
    asset.tickUpper = str(position_details["tickUpper"]),
    asset.token1 = ERC20.objects.get(contract_address__iexact=position_details["token1"]),
    asset.token0 = ERC20.objects.get(contract_address__iexact=position_details["token0"]),
    asset.save()
    return asset

def get_oracle_lastround_price(oracle_address,w3):

    abi = [{
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
      },
      {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"internalType": "uint80", "name": "roundId", "type": "uint80"},
            {"internalType": "int256", "name": "answer", "type": "int256"},
            {"internalType": "uint256", "name": "startedAt", "type": "uint256"},
            {"internalType": "uint256", "name": "updatedAt", "type": "uint256"},
            {"internalType": "uint80", "name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    }]

    address = Web3.to_checksum_address(oracle_address)

    contract = w3.eth.contract(address=address, abi=abi)

    try:
      data = contract.functions.latestRoundData().call()
      decimal = contract.functions.decimals().call()

    except Exception as e:
      print(f"Error calling function: {e}")

    return data[1]/pow(10,decimal)

def price_defillama(chain_name: str, contract_address: str, timestamp: int = None):
    base_url = "https://coins.llama.fi/prices"
    coins_url = f"{chain_name}:{contract_address}"
    if timestamp is None:
        url = f"{base_url}/current/{coins_url}"
    else:
        url = f"{base_url}/historical/{timestamp}/{coins_url}"
    data = requests.get(url).json()
    try:
        if contract_address.startswith("0x"):
            contract_address = Web3.to_checksum_address(contract_address)
        price = data["coins"][f"{chain_name}:{contract_address}"]["price"]
    except KeyError:
        raise Exception(f"{data=} {chain_name=} {contract_address=}")
    return price
