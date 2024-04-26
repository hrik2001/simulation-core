from web3 import Web3
from core.models import Chain
import requests

usdc_address = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
weth_address = Web3.to_checksum_address("0x4200000000000000000000000000000000000006")

# base = Chain.objects.get(chain_name="Base")

minimal_abi = [
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

web3 = Web3(Web3.HTTPProvider(Chain.objects.get(chain_name="Base").rpc))

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
