#!/usr/bin/env python3
import requests
from web3 import Web3, HTTPProvider


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


def task_update_usde_data():
    last_known_block_identifier = None

def main():
    web3 = Web3(HTTPProvider("https://ethereum.blockpi.network/v1/rpc/0d2baa6393853e0ecebc7db7ee0dcb1486ac8212"))


    last_known_block = latest_block["number"] - 1000
    old_block = web3.eth.get_block(last_known_block)

    for block_number in range(last_known_block + 1, latest_block + 1):
        block = web3.eth.get_block(block_number)

        print("hash", block["hash"].hex())
        print("parent hash", block["parentHash"].hex())
        print("usde supply", usde_contract.functions.totalSupply().call(block_identifier=block_number))
        print("susde supply", susde_contract.functions.totalSupply().call(block_identifier=block_number))
        print("usde staked", susde_contract.functions.totalAssets().call(block_identifier=block_number))
        print()

    print("latest", latest_block["timestamp"], price_defillama("ethereum", USDE_ADDRESS, latest_block["timestamp"]))
    print("old", old_block["timestamp"], price_defillama("ethereum", USDE_ADDRESS, old_block["timestamp"]))


if __name__ == '__main__':
    main()
