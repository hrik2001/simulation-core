from dataclasses import dataclass, field

from web3 import Web3, HTTPProvider
import pandas as pd
from requests import get

from core.models import Chain
from curve.simuliq.models.protocol import ProtocolDTO

# chain: ChainDTO
# protocol: str

LD_ABI = [{"stateMutability":"view","type":"function","name":"liquidation_discount","inputs":[],"outputs":[{"name":"arg_0","type":"uint256"}]}]
AMM_ABI = [{"stateMutability":"view","type":"function","name":"get_base_price","inputs":[],"outputs":[{"name":"arg_0","type":"uint256"}]},
           {"stateMutability":"view","type":"function","name":"A","inputs":[],"outputs":[{"name":"arg_0","type":"uint256"}]}]

def compute_health_yellow_sl_efficiency(debt, 
                                        collateral, 
                                        oracle_price, 
                                        base_price, 
                                        start_band, 
                                        finish_band, 
                                        A, 
                                        liq_discount, 
                                        soft_liq_efficiency):
    
    # Compute the range and band data
    bands = abs(finish_band - start_band + 1)
    band_collateral = float(collateral) / float(bands)
    total_discounted_value = 0
    new_collateral_value = 0
    new_crvusd_value = 0

    # Iterate through each band to calculate the discounted value in bands
    for i in range(start_band, finish_band + 1):
        x_min = base_price * ((A - 1) / A)**(i + 1)
        x_max = base_price * ((A - 1) / A)**i
        avg_sell_price = (x_max + x_min) / 2
        
        if oracle_price <= x_min:
            # Adjust collateral for soft liquidation losses
            effective_band_collateral = band_collateral * soft_liq_efficiency
            collat_value = avg_sell_price * effective_band_collateral
            discounted_collat_value = collat_value * (1 - liq_discount / 100)
            new_crvusd_value += collat_value
        
        else:
            effective_band_collateral = band_collateral
            collat_value = avg_sell_price * effective_band_collateral
            discounted_collat_value = collat_value * (1 - liq_discount / 100)
            new_collateral_value += band_collateral
            
        total_discounted_value += discounted_collat_value

    # Calculate healthYellow
    health_yellow = (total_discounted_value / debt - 1) * 100
    return health_yellow, new_collateral_value, new_crvusd_value
    
    
    
@dataclass()
class CurveMintMarketDTO(ProtocolDTO):
    # First declare the parent class fields that will be passed to super().__init__()
    chain: Chain
    protocol: str
    
    # Then declare the class-specific fields
    address: str
    llamma: str
    collateral_token_symbol: str
    collateral_token_address: str
    borrow_token_symbol: str
    borrow_token_address: str
    
    A: float = field(init=False)
    base_price: float = field(init=False)
    liq_discount: float = field(init=False)
    
    def __post_init__(self):
        super().__init__(chain=self.chain, protocol=self.protocol)  # Initialize parent class
        self.base_price, self.A = self.get_base_price_and_amp()
        self.liq_discount = self.get_liquidation_discount()
    
    def __repr__(self):
        return f"Curve Mint Market Object: Collateral {self.collateral_token_symbol} | Borrow: {self.borrow_token_symbol}"
    
    
    def get_liquidation_discount(self, block_number=None):
        if not self.chain.rpc:
            raise ValueError(f"RPC URL is not set for {self.chain.chain_name}")
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.address), abi=LD_ABI)
            contract_function = getattr(contract.functions, "liquidation_discount")
            
            if block_number is not None:
                data = contract_function().call(block_identifier=int(block_number))
            else:
                data = contract_function().call()
            
            return data/10**18
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
    def get_base_price_and_amp(self, block_number=None):
        if not self.chain.rpc:
            raise ValueError(f"RPC URL is not set for {self.chain.chain_name}")
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.llamma), abi=AMM_ABI)
            contract_function = getattr(contract.functions, "get_base_price")
            
            if block_number is not None:
                data = contract_function().call(block_identifier=int(block_number))
            else:
                data = contract_function().call()
            
            base_price = data/10**18
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
    
        try:
            W3 = Web3(HTTPProvider(self.chain.rpc))
            contract = W3.eth.contract(address=Web3.to_checksum_address(self.llamma), abi=AMM_ABI)
            contract_function = getattr(contract.functions, "A")
            
            if block_number is not None:
                data = contract_function().call(block_identifier=int(block_number))
            else:
                data = contract_function().call()
            
            A = data
        except Exception as e:
            raise Exception(f'Error querying smart contract: {e}')
        
        return base_price, A
    
    def get_users(self):
        """
        Fetch users data for a specific crvUSD market
        
        Parameters:
        -----------
        controller_address : str
            The controller address to fetch users for
        chain : str
            The blockchain network (default: "ethereum")
        page : int
            Page number for pagination (default: 1)
        per_page : int
            Number of results per page (default: 100)
        
        Returns:
        --------
        pd.DataFrame
            DataFrame containing user data
        """
        network = self.chain.chain_name.lower()
        
        url = f"https://prices.curve.fi/v1/crvusd/users/{network}/{self.address}/users"
        params = {}
        
        response = get(url, params=params)
        response.raise_for_status()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.json()['data'])
        
        # Convert 'last' column to datetime
        df['last'] = pd.to_datetime(df['last'])

        # Get the max date
        max_date = df['last'].max()

        # Filter rows within last 24 hours
        users_df_24h = df[df['last'] >= (max_date - pd.Timedelta(hours=24))]

        return users_df_24h

    
    def fetch_user_snapshots(self, user: str) -> pd.DataFrame:
        """
        Fetch snapshot data for a specific user in a crvUSD market.
        
        Parameters:
        -----------
        user : str
            The user address to fetch snapshots for
        controller : str
            The controller address
        chain : str
            The blockchain network (default: "ethereum")
        page : int
            Page number for pagination (default: 1)
        per_page : int
            Number of results per page (default: 1)
        
        Returns:
        --------
        pd.DataFrame
            DataFrame containing snapshot data
        """
        network = self.chain.chain_name.lower()
        
        url = f"https://prices.curve.fi/v1/crvusd/users/{network}/{user}/{self.address}/snapshots"
        params = {
            "page": 1,
            "per_page": 1
        }

        print(url, params)
        response = get(url, params=params)
        response.raise_for_status()
        
        # Convert to DataFrame
        df = pd.DataFrame(response.json()['data'])
        
        return df
    
    def get_user_position_data(self) -> pd.DataFrame:
        
        users_df_24h = self.get_users()
        
        user_snapshots = []

        for user in users_df_24h['user']:
            user_df = self.fetch_user_snapshots(user)
            user_snapshots.append(user_df)

        # Combine all user snapshots into a single DataFrame
        all_user_snapshots_df = pd.concat(user_snapshots, ignore_index=True)
        
        return all_user_snapshots_df

    
    
    

    def compute_price_for_max_hard_liq_row(self, row, soft_liq_efficiency):
        
        start_band = row['n1']
        finish_band = row['n2']
        collateral = row['collateral']
        liq_discount = self.liq_discount
        base_price = self.base_price
        A = self.A
        
        debt = row['debt']
        
        # Compute the range and band data
        bands = abs(finish_band - start_band + 1)
        band_collateral = float(collateral) / float(bands)
        avg_price = []

        # Iterate through each band to calculate the discounted value in bands
        for i in range(start_band-1, finish_band + 1):
            
            price_dict = {}
            
            x_min = base_price * ((A - 1) / A)**(i + 1)
            x_max = base_price * ((A - 1) / A)**i
            avg_sell_price = (x_max + x_min) / 2
            
            price_dict['price'] = avg_sell_price
            
            health_yellow, new_collateral_value, new_crvusd_value = compute_health_yellow_sl_efficiency(debt,
                                                                                                        collateral,
                                                                                                        avg_sell_price,
                                                                                                        base_price,
                                                                                                        start_band,
                                                                                                        finish_band,
                                                                                                        A,
                                                                                                        liq_discount,
                                                                                                        soft_liq_efficiency)
            
            price_dict['health'] = health_yellow
            price_dict['new_collateral_value'] = new_collateral_value
            price_dict['new_crvusd_value'] = new_crvusd_value
            
            # Append the price dictionary to the list
            avg_price.append(price_dict)
            
        # Find dictionaries with health < 0
        negative_health_prices = [price_dict for price_dict in avg_price if price_dict['health'] < 0]

        # If no prices with negative health found, return None for all values
        if not negative_health_prices:
            return None, None, None, None 

        # Find the dictionary with maximum new_collateral_value among negative health entries
        max_price_dict = max(negative_health_prices, key=lambda x: x['new_collateral_value'])

        # Return the values from the found dictionary
        max_price = max_price_dict['price']
        max_collateral_value = max_price_dict['new_collateral_value']
        max_crvusd_value = max_price_dict['new_crvusd_value']
        health = max_price_dict['health']

        return max_price, max_collateral_value, max_crvusd_value, health
        
        # return avg_price
        
        
    def compute_price_for_max_hard_liq(self, 
                                 df_users,
                                 soft_liq_efficiency):
    
        return_list = []
        
        for _, row in df_users.iterrows():
            debt = row['debt']
            return_dict = {}
            
            max_price, max_collateral_value, max_crvusd_value, health = self.compute_price_for_max_hard_liq_row(row, soft_liq_efficiency)
            if max_price is not None:  # Add validation for None values
                return_dict['index'] = _
                return_dict['max_price'] = max_price
                return_dict['max_collateral_value'] = max_collateral_value
                return_dict['debt'] = debt - max_crvusd_value
                return_dict['health'] = health
                
                return_dict['debt_raw'] = debt
                return_dict['max_crvusd_value'] = max_crvusd_value
                
                return_list.append(return_dict)
            
        return_df = pd.DataFrame(return_list)
        
        # Store the raw data before grouping
        return_df_raw = return_df.copy()
        
        # Group by max_price and sum both max_collateral_value and debt
        return_df_grouped = return_df.groupby('max_price').agg({
            'max_collateral_value': 'sum',
            'debt': 'sum'
        }).reset_index()
        
        return return_df_grouped, return_df_raw  # Return both DataFrames
    
    
    
    
    
    
@dataclass()
class CurveLendingLongDTO(ProtocolDTO):
    
    pass

@dataclass()
class CurveLendingShortDTO(ProtocolDTO):
    
    pass