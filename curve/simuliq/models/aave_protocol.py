from dataclasses import dataclass

from web3 import Web3, HTTPProvider
import pandas as pd
from requests import get, post
import time
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, Union
from functools import lru_cache
import logging

from dune_client.client import DuneClient
from dune_client.query import QueryBase

from curve.simuliq.models.chain import RateLimitExceededException

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


SUPPLY_ABI = [{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]
ABI_AAVE_POOL = [
    {
        "inputs": [
            {
                "internalType": "address",
                "name": "asset",
                "type": "address"
            }
        ],
        "name": "getReserveData",
        "outputs": [
            {
                "components": [
                    {
                        "components": [
                            {
                                "internalType": "uint256",
                                "name": "data",
                                "type": "uint256"
                            }
                        ],
                        "internalType": "struct DataTypes.ReserveConfigurationMap",
                        "name": "configuration",
                        "type": "tuple"
                    },
                    {
                        "internalType": "uint128",
                        "name": "liquidityIndex",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "currentLiquidityRate",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "variableBorrowIndex",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "currentVariableBorrowRate",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "currentStableBorrowRate",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint40",
                        "name": "lastUpdateTimestamp",
                        "type": "uint40"
                    },
                    {
                        "internalType": "uint16",
                        "name": "id",
                        "type": "uint16"
                    },
                    {
                        "internalType": "address",
                        "name": "aTokenAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "address",
                        "name": "stableDebtTokenAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "address",
                        "name": "variableDebtTokenAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "address",
                        "name": "interestRateStrategyAddress",
                        "type": "address"
                    },
                    {
                        "internalType": "uint128",
                        "name": "accruedToTreasury",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "unbacked",
                        "type": "uint128"
                    },
                    {
                        "internalType": "uint128",
                        "name": "isolationModeTotalDebt",
                        "type": "uint128"
                    }
                ],
                "internalType": "struct DataTypes.ReserveDataLegacy",
                "name": "arg_0",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },{"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getUserEMode","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"internalType":"uint8","name":"id","type":"uint8"}],"name":"getEModeCategoryCollateralConfig","outputs":[{"components":[{"internalType":"uint16","name":"ltv","type":"uint16"},{"internalType":"uint16","name":"liquidationThreshold","type":"uint16"},{"internalType":"uint16","name":"liquidationBonus","type":"uint16"}],"internalType":"struct DataTypes.CollateralConfig","name":"","type":"tuple"}],"stateMutability":"view","type":"function"}
]
BATCH_DATA_PROVIDER_ABI = [{"inputs":[{"internalType":"address","name":"proxyContractAddress","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[{"internalType":"address[]","name":"addresses","type":"address[]"}],"name":"batchUserEMode","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address[]","name":"addresses","type":"address[]"},{"internalType":"address","name":"tokenAddress","type":"address"}],"name":"checkBalances","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"}],"stateMutability":"view","type":"function"}]
AAVE_DATA_PROVIDER_ABI = [
    {
        "inputs": [],
        "name": "getAllReservesTokens",
        "outputs": [
            {
                "components": [
                    {"internalType": "string", "name": "symbol", "type": "string"},
                    {"internalType": "address", "name": "tokenAddress", "type": "address"}
                ],
                "internalType": "struct IPoolDataProvider.TokenData[]",
                "name": "",
                "type": "tuple[]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

def get_current_unix_timestamp() -> int:
    return int(time.time())

TIME_STAMP = get_current_unix_timestamp()

def decode_reserve_configuration(config_value: int) -> Dict[str, Union[float, bool]]:
        config = int(config_value)
        
        def get_bits(start: int, end: int) -> int:
            mask = (1 << (end - start + 1)) - 1
            return (config >> start) & mask
        
        return {
            "ltv": get_bits(0, 15)/10000,
            "liquidationThreshold": get_bits(16, 31)/10000,
            "liquidationBonus": get_bits(32, 47)/10000,
            "decimals": get_bits(48, 55),
            "reserveIsActive": bool(get_bits(56, 56)),
            "reserveIsFrozen": bool(get_bits(57, 57)),
            "borrowingEnabled": bool(get_bits(58, 58)),
            "stableRateBorrowingEnabled": bool(get_bits(59, 59)),
            "assetIsPaused": bool(get_bits(60, 60)),
            "borrowingInIsolationModeEnabled": bool(get_bits(61, 61)),
            "siloedBorrowingEnabled": bool(get_bits(62, 62)),
            "flashLoaningEnabled": bool(get_bits(63, 63)),
            "reserveFactor": get_bits(64, 79)/10000,
            "borrowCap": get_bits(80, 115),
            "supplyCap": get_bits(116, 151),
            "liquidationProtocolFee": get_bits(152, 167)/10000,
            "eModeCategoryId": get_bits(168, 175),
            "unbackedMintCap": get_bits(176, 211),
            "debtCeilingForIsolationMode": get_bits(212, 251),
            "virtualAccountingEnabled": bool(get_bits(252, 252))
        }
        

@dataclass()
class AaveProtocolDTO(ProtocolDTO):
    batch_data_provider_address: Optional[str]
    aave_pool_address: str
    aave_data_provider_address: str
    holder_query_id: Optional[int]
    timestamp: Optional[int] = None

    def __post_init__(self):
        """Perform post-initialization setup."""
        if self.batch_data_provider_address:
            self.batch_data_provider_address = Web3.to_checksum_address(self.batch_data_provider_address)
        if self.aave_pool_address:
            self.aave_pool_address = Web3.to_checksum_address(self.aave_pool_address)
        if self.aave_data_provider_address:
            self.aave_data_provider_address = Web3.to_checksum_address(self.aave_data_provider_address)
        # if self.rpc_url:
        #     self.w3 = Web3(HTTPProvider(self.rpc_url))
        logger.info(f"Initialized Aave Protocol DTO for network: {self.chain.chain}")

    def __repr__(self):
        """Return a string representation of the Aave Protocol DTO instance."""
        return f"Aave Protocol DTO(network={self.chain.chain})"


    def get_reserve_list(self, block_number: Optional[int] = None) -> List[Dict[str, Union[str, int]]]:
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
        if not self.aave_data_provider_address:
            raise ValueError(f"Aave data provider address is not set for {self.chain.chain}")
        
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.aave_data_provider_address), abi=AAVE_DATA_PROVIDER_ABI)
            contract_function = getattr(contract.functions, "getAllReservesTokens")
            
            if block_number is not None:
                data = contract_function().call(block_identifier=int(block_number))
            else:
                data = contract_function().call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
    def get_asset_data(self, asset: str, block_number: Optional[int] = None) -> Dict[str, Union[str, int]]:
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
        if not self.aave_pool_address:
            raise ValueError(f"Aave pool address is not set for {self.chain.chain}")
        
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            asset = Web3.to_checksum_address(asset)
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.aave_pool_address), abi=ABI_AAVE_POOL)
            contract_function = getattr(contract.functions, "getReserveData")
            
            if block_number is not None:
                data = contract_function(asset).call(block_identifier=int(block_number))
            else:
                data = contract_function(asset).call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
        
    
    def get_emode_config(self, block_number: Optional[int] = None) -> Dict[str, Union[str, int]]:
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
        if not self.aave_pool_address:
            raise ValueError(f"Aave pool address is not set for {self.chain.chain}")
        
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.aave_pool_address), abi=ABI_AAVE_POOL)
            contract_function = getattr(contract.functions, "getEModeCategoryCollateralConfig")
            
            if block_number is not None:
                data = contract_function(1).call(block_identifier=int(block_number))
            else:
                data = contract_function(1).call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
        
    
    def get_user_balance(self, user_address_list, asset, block_number=None):
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
        if not self.batch_data_provider_address:
            raise ValueError(f"Batch data provider address is not set for {self.chain.chain}")
        
        user_address_list = [Web3.to_checksum_address(user) for user in user_address_list]
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.batch_data_provider_address), abi=BATCH_DATA_PROVIDER_ABI)
            contract_function = getattr(contract.functions, "checkBalances")
            
            if block_number is not None:
                data = contract_function(user_address_list, asset).call(block_identifier=int(block_number))
            else:
                data = contract_function(user_address_list, asset).call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
    
    def get_supply(self, asset, block_number=None):
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            contract = W3.eth.contract(address=Web3.to_checksum_address(asset), abi=SUPPLY_ABI)
            contract_function = getattr(contract.functions, "totalSupply")
            
            if block_number is not None:
                data = contract_function().call(block_identifier=int(block_number))
            else:
                data = contract_function().call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
    
    def get_emode(self, user_list, block_number=None):
        if not self.chain.rpc_url:
            raise ValueError(f"RPC URL is not set for {self.chain.chain}")
        if not self.batch_data_provider_address:
            raise ValueError(f"Batch data provider address is not set for {self.chain.chain}")
        
        user_list = [Web3.to_checksum_address(user) for user in user_list]
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc_url))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.batch_data_provider_address), abi=BATCH_DATA_PROVIDER_ABI)
            contract_function = getattr(contract.functions, "batchUserEMode")
            
            if block_number is not None:
                data = contract_function(user_list).call(block_identifier=int(block_number))
            else:
                data = contract_function(user_list).call()
            
            return data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
    
    def get_current_price(self, token_address: str) -> Optional[float]:
        """
        Fetches the current price of a token from the Coin Llama API and extracts the price.

        Args:
            token_address (str): The address of the token.

        Returns:
            Optional[float]: The current price of the token or None if an error occurs.
        """
        base_url = "https://coins.llama.fi/prices/current"
        url = f"{base_url}/{self.chain.chain}:{token_address}?searchWidth=12h"
        
        response = get(url)
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitExceededException("Rate limit exceeded.", retry_after=int(retry_after) if retry_after else None)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        price_info = data.get('coins', {}).get(f'{self.chain.chain}:{token_address}', {})
        return price_info.get('price')

    
    def get_aave_supported_asset_data(self) -> pd.DataFrame:
        asset_list = self.get_reserve_list()
        
        data: List[Dict[str, Union[int, str, float]]] = []
        unix_timestamp: int = TIME_STAMP

        for asset in asset_list:
            data_dict: Dict[str, Union[int, str, float]] = {}
            
            reserve_data = self.get_asset_data(asset[1])
            data_dict["timestamp"] = unix_timestamp
            data_dict["symbol"] = asset[0]
            data_dict["price"] = self.get_current_price(asset[1])
            data_dict["assetAddress"] = asset[1]
            data_dict["configuration"] = reserve_data[0][0]

            data_dict["aTokenAddress"] = reserve_data[8]
            data_dict["stableDebtTokenAddress"] = reserve_data[9]
            data_dict["variableDebtTokenAddress"] = reserve_data[10]
            
            decoded_configuration = decode_reserve_configuration(reserve_data[0][0])
            
            data_dict["collateralSupply"] = self.get_supply(reserve_data[8]) / 10**decoded_configuration["decimals"]
            data_dict["debtSupply"] = self.get_supply(reserve_data[10]) / 10**decoded_configuration["decimals"]
            
            data_dict.update(decoded_configuration)
            data.append(data_dict)
            
            data_df = pd.DataFrame(data)
            
        return data_df
    
    
    def get_aave_supported_asset_data_to_csv(self) -> None:
        data_df = self.get_aave_supported_asset_data()
        data_df.to_csv(f'aave_supported_asset_data_{self.chain.chain}_{TIME_STAMP}.csv', index=False)
    
    
    def get_users(self) -> pd.DataFrame:
        if self.holder_query_id is None:
            raise ValueError(f"Holder query ID is not set for {self.chain.chain}")
        
        dune = DuneClient(
            api_key=os.getenv('DUNE_API_KEY'),
            base_url="https://api.dune.com",
            request_timeout=5000 # request will time out after 300 seconds
        )

        query = QueryBase(
            query_id=self.holder_query_id,
            params=[],
        )
        
        users = dune.run_query_dataframe(query)
        # users = dune.get_latest_result_dataframe(query)
        users["timestamp"] = TIME_STAMP

        return users
    
    
    def get_users_to_csv(self) -> None:
        data_df = self.get_users()
        data_df.to_csv(f'user_data_{self.chain.chain}_{TIME_STAMP}.csv', index=False)
    
    # def get_user_position_data(self, users_list, asset_data) -> pd.DataFrame:
    
    #     if isinstance(asset_data, str):
    #         asset_data = json.loads(asset_data)
    #     elif not isinstance(asset_data, list):
    #         raise ValueError(f"Expected asset_data to be a list or JSON string, got {type(asset_data)}")

    #     user_position = []
        
    #     for user in users_list:
    #         user_position_dict = {"user": user}
    #         user_position_dict["timestamp"] = TIME_STAMP
    #         # user_position_dict["emode"] = get_emode(user)
    #         user_position.append(user_position_dict)

    #     emode = self.get_emode(users_list)
    #     for index, user_dict in enumerate(user_position):
    #         user_dict["emode"] = emode[index]     
            
    #     for asset in asset_data:
    #         decimals = asset["decimals"]
            
    #         atoken_symbol = f"a{asset['symbol']}"
    #         dtoken_symbol = f"d{asset['symbol']}"
            
    #         atoken_balance = self.get_user_balance(users_list, asset["aTokenAddress"])
    #         dtoken_balance = self.get_user_balance(users_list, asset["variableDebtTokenAddress"])
            
    #         for index, user_dict in enumerate(user_position):
    #             user_dict[atoken_symbol] = atoken_balance[index] / 10**decimals
    #             user_dict[dtoken_symbol] = dtoken_balance[index] / 10**decimals
                
    #     # Convert this to a dataframe
    #     df_user_position = pd.DataFrame(user_position)
        
    #     return df_user_position
    
    def get_user_position_data(self, asset_data: pd.DataFrame) -> pd.DataFrame:
        users_df = self.get_users()
        
        logger.info(f"Users dataframe shape: {users_df.shape}")
        
        users_list = users_df['user'].tolist()
        
        if not isinstance(asset_data, pd.DataFrame):
            raise ValueError(f"Expected asset_data to be a DataFrame, got {type(asset_data)}")

        user_position = pd.DataFrame({
            "user": users_list,
            "timestamp": TIME_STAMP
        })

        # Get emode for all users at once
        user_position["emode"] = self.get_emode(users_list)

        for _, asset in asset_data.iterrows():
            decimals = asset["decimals"]
            
            atoken_symbol = f"a{asset['symbol']}"
            dtoken_symbol = f"d{asset['symbol']}"
            
            atoken_balance = self.get_user_balance(users_list, asset["aTokenAddress"])
            dtoken_balance = self.get_user_balance(users_list, asset["variableDebtTokenAddress"])
            
            user_position[atoken_symbol] = [balance / 10**decimals for balance in atoken_balance]
            user_position[dtoken_symbol] = [balance / 10**decimals for balance in dtoken_balance]

        return user_position
    
    
    def get_user_position_data_to_csv(self) -> None:
        data_df = self.get_user_position_data()
        data_df.to_csv(f'user_position_data_{self.chain.chain}_{TIME_STAMP}.csv', index=False)
        
        
    def get_user_position_data_optimized(self, users_list, asset_data: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(asset_data, pd.DataFrame):
            raise ValueError(f"Expected asset_data to be a DataFrame, got {type(asset_data)}")

        user_position = pd.DataFrame({
            "user": users_list,
            "timestamp": TIME_STAMP,
            "emode": self.get_emode(users_list)
        })

        for token_type in ['a', 'd']:
            address_col = 'aTokenAddress' if token_type == 'a' else 'variableDebtTokenAddress'
            balances = asset_data.apply(lambda asset: self.get_user_balance(users_list, asset[address_col]), axis=1)
            
            for (_, asset), balance in zip(asset_data.iterrows(), balances):
                symbol = f"{token_type}{asset['symbol']}"
                user_position[symbol] = balance / 10**asset['decimals']

        return user_position
    
    def get_user_position_data_optimized_to_csv(self) -> None:
        data_df = self.get_user_position_data_optimized()
        data_df.to_csv(f'user_position_data_optimized_{self.chain.chain}_{TIME_STAMP}.csv', index=False)
