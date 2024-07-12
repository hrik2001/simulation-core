from web3 import Web3
from core.models import Chain, ERC20, UniswapLPPosition
from arcadia.models import AccountAssets
import requests
from django.core.cache import cache
from collections import defaultdict
from time import sleep
from arcadia.arcadiasim.models.asset import Asset, SimCoreUniswapLPPosition
from arcadia.arcadiasim.models.chain import Chain as ArcadiaChain
from core.pricing.univ3_nft_position import get_arcadia_account_nft_position

usdc_address = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
weth_address = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")

usdc_lending_pool_address = Web3.to_checksum_address("0x3ec4a293Fb906DD2Cd440c20dECB250DeF141dF1")
weth_lending_pool_address = Web3.to_checksum_address("0x803ea69c7e87D1d6C86adeB40CB636cC0E6B98E2")
# base = Chain.objects.get(chain_name="Base")

minimal_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "numeraire",
        "outputs": [
            {
                "name": "",
                "type": "address"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getCollateralValue",
        "outputs": [
            {
                "name": "collateralValue",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    # Existing ABI elements
    {
        "constant": True,
        "inputs": [
            {
                "name": "numeraire_",
                "type": "address"
            }
        ],
        "name": "getAccountValue",
        "outputs": [
            {
                "name": "accountValue",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "generateAssetData",
        "outputs": [
            {
                "name": "assetAddresses",
                "type": "address[]"
            },
            {
                "name": "assetIds",
                "type": "uint256[]"
            },
            {
                "name": "assetAmounts",
                "type": "uint256[]"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getLiquidationValue",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "getUsedMargin",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "isAccountUnhealthy",
        "outputs": [
            {
                "name": "",
                "type": "bool"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]


lending_pool_abi = [
    {
        "constant": True,
        "inputs": [
            {
                "name": "account",
                "type": "address"
            }
        ],
        "name": "getOpenPosition",
        "outputs": [
            {
                "name": "openPosition",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalLiquidity",
        "outputs": [
            {"internalType": "uint256", "name": "totalLiquidity_", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

web3 = Web3(Web3.HTTPProvider(Chain.objects.get(chain_name="Base").rpc))

# ABI and contract address configuration
ORACLE_CONTRACT_ADDRESS = Web3.to_checksum_address("0x6a5485E3ce6913890ae5e8bDc08a868D432eEB31")
ORACLE_INFO_ABI = [{
    "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
    "name": "oracleInformation",
    "outputs": [
        {"internalType": "uint32", "name": "cutOffTime", "type": "uint32"},
        {"internalType": "uint64", "name": "unitCorrection", "type": "uint64"},
        {"internalType": "address", "name": "oracle", "type": "address"},
    ],
    "stateMutability": "view",
    "type": "function",
}]
ORACLE_DESC_ABI = [{
    "inputs": [],
    "name": "description",
    "outputs": [{"internalType": "string", "name": "", "type": "string"}],
    "stateMutability": "view",
    "type": "function",
}]

def get_oracle_information(oracle_count: int):

    # get_oracle_information helps to track the oracles listed under 0x6a5485E3ce6913890ae5e8bDc08a868D432eEB31.
    # get_oracle_information generates a list of dict with all relevant info about the oracles being used.

    def get_oracle_description(oracle_address: str):
        try:
            address = Web3.to_checksum_address(oracle_address)
            contract = web3.eth.contract(address=address, abi=ORACLE_DESC_ABI)
            return contract.functions.description().call()
        except Exception as e:
            print(f"Error calling description function for address {oracle_address}: {e}")
            return None

    def get_oracle_address_from_id(oracle_id: int):
        try:
            contract = web3.eth.contract(address=ORACLE_CONTRACT_ADDRESS, abi=ORACLE_INFO_ABI)
            oracle_info = contract.functions.oracleInformation(oracle_id).call()
            return oracle_info[2]  # Returning the oracle address
        except Exception as e:
            print(f"Error calling oracleInformation function for oracle ID {oracle_id}: {e}")
            return None

    oracle_info_list = []

    for i in range(oracle_count):
        oracle_address = get_oracle_address_from_id(i)
        if oracle_address:
            oracle_description = get_oracle_description(oracle_address)
            oracle_dict = {
                "oracleId": i,
                "oracleAddress": oracle_address,
                "oracleDesc": oracle_description
            }
            oracle_info_list.append(oracle_dict)

    return oracle_info_list

def get_debt(lending_pool, account):
    contract_address = Web3.to_checksum_address(lending_pool)
    account = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=lending_pool_abi)
    return contract.functions.getOpenPosition(account).call()
# The contract address. Replace with the actual contract address.

def get_total_supply(lending_pool):
    contract_address = Web3.to_checksum_address(lending_pool)
    contract = web3.eth.contract(address=contract_address, abi=lending_pool_abi)
    return contract.functions.totalSupply().call()

def get_total_liquidity(lending_pool):
    contract_address = Web3.to_checksum_address(lending_pool)
    contract = web3.eth.contract(address=contract_address, abi=lending_pool_abi)
    return contract.functions.totalLiquidity().call()

# Function to get the account value
def get_account_value(account, numeraire):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.getAccountValue(numeraire).call()

def get_liquidation_value(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.getLiquidationValue().call()

def get_used_margin_value(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.getUsedMargin().call()

# Function to call generateAssetData
def call_generate_asset_data(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.generateAssetData().call()

def get_numeraire_address(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.numeraire().call()

def get_collateral_value(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.getCollateralValue().call()

def get_health_status(account):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return not contract.functions.isAccountUnhealthy().call()

def get_price_defillama(labels, search_width=4):
    result = defaultdict(int)
    labels_to_query = []

    for i in labels:
        cache_response = cache.get(i)
        if cache_response is None:
            labels_to_query.append(i)
        else:
            result[i] = cache_response
    if len(labels_to_query) > 0:
        q = ",".join(labels_to_query)
        r = requests.get(f"https://coins.llama.fi/prices/current/{q}?searchWidth={search_width}h")
        sleep(1)
        if r.status_code == 200:
            response = r.json()
            for label in labels_to_query:
                if label in response["coins"]:
                    cache.set(label, response["coins"][label], timeout=300)
                    result[label] = response["coins"][label]
                else:
                    cache.set(label, 0, timeout=300)
    return result
        
def update_amounts(account: str, asset_record: AccountAssets):
    usdc_value = get_account_value(account, usdc_address)
    if usdc_value == 0:
        weth_value = 0
    else:
        weth_value = get_account_value(account, weth_address)
    # asset_data = call_generate_asset_data(account)
    asset_data = asset_record.asset_details
    # collateral_value = get_collateral_value(account)
    # numeraire = get_numeraire_address(account)
    numeraire = asset_record.numeraire
    liquidation_value = get_liquidation_value(account)
    used_margin = get_used_margin_value(account)
    healthy = get_health_status(account)

    labels = list(set(asset_data[0]))
    prices = get_price_defillama([f"base:{i}" for i in labels])
    asset_data_usd = defaultdict(int)
    usd_value_without_nft = 0
    for i, asset in enumerate(asset_data[0]):
        p = prices[f"base:{asset}"]
        if p != 0:
            usd = asset_data[2][i] / (10 ** p["decimals"]) * (p["price"])
            asset_data_usd[asset] = usd
            usd_value_without_nft += usd
    
    
    if usdc_value != 0:
        if numeraire.lower() == weth_address.lower():
            price_weth = (weth_value / 1e18) / (usdc_value / 1e6)
            price_weth = 1/price_weth
            # collateral_value_usd = (collateral_value / 1e18) * price_weth
            debt = get_debt(weth_lending_pool_address, account)
            debt_usd = (debt/1e18) * price_weth
            collateral_value = weth_value
            collateral_value_usd = usdc_value/1e6
        else:
            collateral_value = usdc_value
            collateral_value_usd = collateral_value/1e6
            debt = get_debt(usdc_lending_pool_address, account)
            debt_usd = (debt/1e6)
    else:
        collateral_value = 0
        collateral_value_usd = 0
        debt_usd = 0

    asset_data_usd["NFT"] = (collateral_value_usd) - usd_value_without_nft

    print({
            'usdc_value': str(usdc_value),
            'weth_value': str(weth_value),
            # 'asset_details': asset_data,
            # 'numeraire': numeraire,
            'collateral_value': str(collateral_value),
            'collateral_value_usd': str(collateral_value_usd),
            'debt_usd': str(debt_usd),
            'asset_details_usd': asset_data_usd
        })
    # Update or create the asset record
    AccountAssets.objects.update_or_create(
        account=account,
        defaults={
            'usdc_value': str(usdc_value),
            'weth_value': str(weth_value),
            # 'asset_details': asset_data,
            # 'numeraire': numeraire,
            'collateral_value': str(collateral_value),
            'collateral_value_usd': str(collateral_value_usd),
            'debt_usd': str(debt_usd),
            'asset_details_usd': asset_data_usd,
            'liquidation_value': liquidation_value,
            'used_margin': used_margin,
            "healthy": healthy
        }
    )
def update_all_data(account):
    usdc_value = get_account_value(account, usdc_address)
    if usdc_value == 0:
        weth_value = 0
    else:
        weth_value = get_account_value(account, weth_address)
    asset_data = call_generate_asset_data(account)
    # collateral_value = get_collateral_value(account)
    
    position_distribution = get_arcadia_account_nft_position(asset_data, w3=web3)
    
    numeraire = get_numeraire_address(account)
    liquidation_value = get_liquidation_value(account)
    used_margin = get_used_margin_value(account)
    healthy = get_health_status(account)

    labels = list(set(asset_data[0]))
    prices = get_price_defillama([f"base:{i}" for i in labels])
    asset_data_usd = defaultdict(int)
    
    position_distribution_usd = defaultdict(int)
    listed_asset_usd = 0
    
    for asset in position_distribution:
        p = prices[f"base:{asset}"]
        if p != 0:
            usd = position_distribution[asset] / (10 ** p["decimals"]) * (p["price"])
            position_distribution_usd[asset] = usd
            listed_asset_usd += usd
            
    usd_value_without_nft = 0
    for i, asset in enumerate(asset_data[0]):
        p = prices[f"base:{asset}"]
        if p != 0:
            usd = asset_data[2][i] / (10 ** p["decimals"]) * (p["price"])
            asset_data_usd[asset] = usd
            usd_value_without_nft += usd
    
    
    if usdc_value != 0:
        if numeraire.lower() == weth_address.lower():
            price_weth = (weth_value / 1e18) / (usdc_value / 1e6)
            price_weth = 1/price_weth
            # collateral_value_usd = (collateral_value / 1e18) * price_weth
            debt = get_debt(weth_lending_pool_address, account)
            debt_usd = (debt/1e18) * price_weth
            collateral_value = weth_value
            collateral_value_usd = usdc_value/1e6
        else:
            collateral_value = usdc_value
            collateral_value_usd = collateral_value/1e6
            debt = get_debt(usdc_lending_pool_address, account)
            debt_usd = (debt/1e6)
    else:
        collateral_value = 0
        collateral_value_usd = 0
        debt_usd = 0

    asset_data_usd["NFT"] = (collateral_value_usd) - usd_value_without_nft
    position_distribution_usd["others"] = (collateral_value_usd) - listed_asset_usd

    print({
            'usdc_value': str(usdc_value),
            'weth_value': str(weth_value),
            'asset_details': asset_data,
            'numeraire': numeraire,
            'collateral_value': str(collateral_value),
            'collateral_value_usd': str(collateral_value_usd),
            'debt_usd': str(debt_usd),
            'asset_details_usd': asset_data_usd
        })
    # Update or create the asset record
    AccountAssets.objects.update_or_create(
        account=account,
        defaults={
            'usdc_value': str(usdc_value),
            'weth_value': str(weth_value),
            'asset_details': asset_data,
            'position_distribution': position_distribution,
            'position_distribution_usd': position_distribution_usd,
            'numeraire': numeraire,
            'collateral_value': str(collateral_value),
            'collateral_value_usd': str(collateral_value_usd),
            'debt_usd': str(debt_usd),
            'asset_details_usd': asset_data_usd,
            'liquidation_value': liquidation_value,
            'used_margin': used_margin,
            "healthy": healthy
        }
    )

def chain_to_pydantic(chain: Chain):
    chain_dict = chain.__dict__
    chain_dict["rpc_url"] = chain_dict["rpc"]
    chain_dict["explorer_url"] = chain_dict["explorer"]
    chain_dict["name"] = chain_dict["chain_name"]
    return ArcadiaChain(**chain_dict)

def erc20_to_pydantic(asset: ERC20 | UniswapLPPosition):
    chain = chain_to_pydantic(asset.chain)
    response = asset.__dict__
    response["chain"] = chain
    if isinstance(asset, UniswapLPPosition):
        response["token0"] = erc20_to_pydantic(asset.token0)
        response["token1"] = erc20_to_pydantic(asset.token1)
        response["name"] = asset.name
        response["symbol"] = asset.symbol
        return SimCoreUniswapLPPosition(**response)
    return Asset(**response)

def get_risk_factors(web3, creditor, asset_addresses, asset_ids, contract_address="0xd0690557600eb8Be8391D1d97346e2aab5300d5f"):
    # ABI for the getRiskFactors function
    abi = [
        {
            "constant": True,
            "inputs": [
                {"name": "creditor", "type": "address"},
                {"name": "assetAddresses", "type": "address[]"},
                {"name": "assetIds", "type": "uint256[]"}
            ],
            "name": "getRiskFactors",
            "outputs": [
                {"name": "collateralFactors", "type": "uint16[]"},
                {"name": "liquidationFactors", "type": "uint16[]"}
            ],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    # Convert the contract address to a checksum address
    contract_address = Web3.to_checksum_address(contract_address)
    
    # Create a contract instance
    contract = web3.eth.contract(address=contract_address, abi=abi)
    
    # Call the getRiskFactors function
    collateral_factors, liquidation_factors = contract.functions.getRiskFactors(
        Web3.to_checksum_address(creditor),
        [Web3.to_checksum_address(addr) for addr in asset_addresses],
        asset_ids
    ).call()
    
    return collateral_factors, liquidation_factors