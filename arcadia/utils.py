from web3 import Web3
from core.models import Chain, ERC20, UniswapLPPosition
from arcadia.models import AccountAssets
import requests
from django.core.cache import cache
from collections import defaultdict
from time import sleep
from arcadia.arcadiasim.models.asset import Asset, SimCoreUniswapLPPosition
from arcadia.arcadiasim.models.chain import Chain as ArcadiaChain

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
    }
]

web3 = Web3(Web3.HTTPProvider(Chain.objects.get(chain_name="Base").rpc))

def get_debt(lending_pool, account):
    contract_address = Web3.to_checksum_address(lending_pool)
    account = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=lending_pool_abi)
    return contract.functions.getOpenPosition(account).call()
# The contract address. Replace with the actual contract address.

# Function to get the account value
def get_account_value(account, numeraire):
    contract_address = Web3.to_checksum_address(account)
    contract = web3.eth.contract(address=contract_address, abi=minimal_abi)
    return contract.functions.getAccountValue(numeraire).call()

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
    collateral_value = get_collateral_value(account)
    # numeraire = get_numeraire_address(account)
    numeraire = asset_record.numeraire

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
            collateral_value_usd = (collateral_value / 1e18) * price_weth
            debt = get_debt(weth_lending_pool_address, account)
            debt_usd = (debt/1e18) * price_weth
        else:
            collateral_value_usd = collateral_value/1e6
            debt = get_debt(usdc_lending_pool_address, account)
            debt_usd = (debt/1e6)
    else:
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
            'asset_details_usd': asset_data_usd
        }
    )
def update_all_data(account):
    usdc_value = get_account_value(account, usdc_address)
    if usdc_value == 0:
        weth_value = 0
    else:
        weth_value = get_account_value(account, weth_address)
    asset_data = call_generate_asset_data(account)
    collateral_value = get_collateral_value(account)
    numeraire = get_numeraire_address(account)

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
            collateral_value_usd = (collateral_value / 1e18) * price_weth
            debt = get_debt(weth_lending_pool_address, account)
            debt_usd = (debt/1e18) * price_weth
        else:
            collateral_value_usd = collateral_value/1e6
            debt = get_debt(usdc_lending_pool_address, account)
            debt_usd = (debt/1e6)
    else:
        collateral_value_usd = 0
        debt_usd = 0

    asset_data_usd["NFT"] = (collateral_value_usd) - usd_value_without_nft

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
            'numeraire': numeraire,
            'collateral_value': str(collateral_value),
            'collateral_value_usd': str(collateral_value_usd),
            'debt_usd': str(debt_usd),
            'asset_details_usd': asset_data_usd
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