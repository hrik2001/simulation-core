import math
from web3 import Web3
import web3
from collections import defaultdict

# Function to add or update the dictionary
def add_or_update_dict(dictionary, key, value):
    dictionary[key] += value

def mul_div(a, b, denominator):
    """Replicate Solidity's mulDiv for full precision multiplication and division."""
    return (a * b) // denominator


def sqrt_price_from_price(price):
    return int((price**0.5) * 2**96)


def sqrt_price_x96_to_tick(sqrtPriceX96):
    # Base of the Uniswap tick system
    tick_base = 1.0001

    # Convert sqrtPriceX96 to the actual square root price by dividing by 2^96
    # Note: This step might need adjustment based on how sqrtPriceX96 is represented in your context
    sqrtPrice = sqrtPriceX96 / (2**96)

    # Calculate the tick from the square root price
    # The formula for tick calculation is log(sqrtPrice^2) / log(base), simplified to 2 * log(sqrtPrice) / log(base)
    tick = math.log(sqrtPrice**2) / math.log(tick_base)

    # Return the tick rounded to the nearest integer, as ticks are integer values in Uniswap
    return round(tick)


def get_sqrt_ratio_at_tick(tick):
    MAX_TICK = 887272

    abs_tick = abs(tick)
    if abs_tick > MAX_TICK:
        raise ValueError("Tick value out of bounds")

    ratio = (
        0xFFFCB933BD6FAD37AA2D162D1A594001
        if abs_tick & 0x1
        else 0x100000000000000000000000000000000
    )
    if abs_tick & 0x2:
        ratio = (ratio * 0xFFF97272373D413259A46990580E213A) >> 128
    if abs_tick & 0x4:
        ratio = (ratio * 0xFFF2E50F5F656932EF12357CF3C7FDCC) >> 128
    if abs_tick & 0x8:
        ratio = (ratio * 0xFFE5CACA7E10E4E61C3624EAA0941CD0) >> 128
    if abs_tick & 0x10:
        ratio = (ratio * 0xFFCB9843D60F6159C9DB58835C926644) >> 128
    if abs_tick & 0x20:
        ratio = (ratio * 0xFF973B41FA98C081472E6896DFB254C0) >> 128
    if abs_tick & 0x40:
        ratio = (ratio * 0xFF2EA16466C96A3843EC78B326B52861) >> 128
    if abs_tick & 0x80:
        ratio = (ratio * 0xFE5DEE046A99A2A811C461F1969C3053) >> 128
    if abs_tick & 0x100:
        ratio = (ratio * 0xFCBE86C7900A88AEDCFFC83B479AA3A4) >> 128
    if abs_tick & 0x200:
        ratio = (ratio * 0xF987A7253AC413176F2B074CF7815E54) >> 128
    if abs_tick & 0x400:
        ratio = (ratio * 0xF3392B0822B70005940C7A398E4B70F3) >> 128
    if abs_tick & 0x800:
        ratio = (ratio * 0xE7159475A2C29B7443B29C7FA6E889D9) >> 128
    if abs_tick & 0x1000:
        ratio = (ratio * 0xD097F3BDFD2022B8845AD8F792AA5825) >> 128
    if abs_tick & 0x2000:
        ratio = (ratio * 0xA9F746462D870FDF8A65DC1F90E061E5) >> 128
    if abs_tick & 0x4000:
        ratio = (ratio * 0x70D869A156D2A1B890BB3DF62BAF32F7) >> 128
    if abs_tick & 0x8000:
        ratio = (ratio * 0x31BE135F97D08FD981231505542FCFA6) >> 128
    if abs_tick & 0x10000:
        ratio = (ratio * 0x9AA508B5B7A84E1C677DE54F3E99BC9) >> 128
    if abs_tick & 0x20000:
        ratio = (ratio * 0x5D6AF8DEDB81196699C329225EE604) >> 128
    if abs_tick & 0x40000:
        ratio = (ratio * 0x2216E584F5FA1EA926041BEDFE98) >> 128
    if abs_tick & 0x80000:
        ratio = (ratio * 0x48A170391F7DC42444E8FA2) >> 128

    if tick > 0:
        ratio = (1 << 256) // ratio

    sqrtPriceX96 = (ratio >> 32) + (1 if ratio % (1 << 32) != 0 else 0)
    return sqrtPriceX96


def get_amount0_for_liquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity):
    """Compute the amount of token0 for a given amount of liquidity and price range."""
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    return (
        mul_div(liquidity << 96, sqrtRatioBX96 - sqrtRatioAX96, sqrtRatioBX96)
        // sqrtRatioAX96
    )


def get_amount1_for_liquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity):
    """Compute the amount of token1 for a given amount of liquidity and price range."""
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    return mul_div(liquidity, sqrtRatioBX96 - sqrtRatioAX96, 2**96)


def get_amounts_from_ticks(tickCurrent, tickLower, tickUpper, liquidity):
    sqrtRatioX96 = get_sqrt_ratio_at_tick(tickCurrent)
    sqrtRatioAX96 = get_sqrt_ratio_at_tick(tickLower)
    sqrtRatioBX96 = get_sqrt_ratio_at_tick(tickUpper)

    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    amount0, amount1 = 0, 0
    if sqrtRatioX96 <= sqrtRatioAX96:
        amount0 = get_amount0_for_liquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity)
    elif sqrtRatioX96 < sqrtRatioBX96:
        amount0 = get_amount0_for_liquidity(sqrtRatioX96, sqrtRatioBX96, liquidity)
        amount1 = get_amount1_for_liquidity(sqrtRatioAX96, sqrtRatioX96, liquidity)
    else:
        amount1 = get_amount1_for_liquidity(sqrtRatioAX96, sqrtRatioBX96, liquidity)

    return amount0, amount1



def get_nft_positions_details(nft_contract_address, w3, token_id):
    
    abi = [
        {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "positions",
        "outputs": [
            {"internalType": "uint96", "name": "nonce", "type": "uint96"},
            {"internalType": "address", "name": "operator", "type": "address"},
            {"internalType": "address", "name": "token0", "type": "address"},
            {"internalType": "address", "name": "token1", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
            {"internalType": "int24", "name": "tickLower", "type": "int24"},
            {"internalType": "int24", "name": "tickUpper", "type": "int24"},
            {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
            {
                "internalType": "uint256",
                "name": "feeGrowthInside0LastX128",
                "type": "uint256",
            },
            {
                "internalType": "uint256",
                "name": "feeGrowthInside1LastX128",
                "type": "uint256",
            },
            {"internalType": "uint128", "name": "tokensOwed0", "type": "uint128"},
            {"internalType": "uint128", "name": "tokensOwed1", "type": "uint128"},
        ],
        "stateMutability": "view",
        "type": "function",
        }
    ]
    
    contract_address = Web3.to_checksum_address(nft_contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    try:
        result = contract.functions.positions(token_id).call()
    except web3.exceptions.ContractLogicError:
        return None
    
    details = {
        "nonce": result[0],
        "operator": result[1],
        "token0": result[2],
        "token1": result[3],
        "fee": result[4],
        "tickLower": result[5],
        "tickUpper": result[6],
        "liquidity": result[7],
        "feeGrowthInside0LastX128": result[8],
        "feeGrowthInside1LastX128": result[9],
        "tokensOwed0": result[10],
        "tokensOwed1": result[11],
    }
    
    return details

# def get_uniswap_slot0(pool_address, w3):
    
#     abi = [
#         {
#         "inputs": [],
#         "name": "slot0",
#         "outputs": [
#             {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
#             {"internalType": "int24", "name": "tick", "type": "int24"},
#             {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
#             {
#                 "internalType": "uint16",
#                 "name": "observationCardinality",
#                 "type": "uint16",
#             },
#             {
#                 "internalType": "uint16",
#                 "name": "observationCardinalityNext",
#                 "type": "uint16",
#             },
#             {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
#             {"internalType": "bool", "name": "unlocked", "type": "bool"},
#         ],
#         "stateMutability": "view",
#         "type": "function",
#     }
#     ]
    
#     contract_address = Web3.to_checksum_address(pool_address)
#     contract = w3.eth.contract(address=contract_address, abi=abi)
#     try:
#         result = contract.functions.slot0().call()
#     except web3.exceptions.ContractLogicError:
#         return None
    
#     details = {
#         "sqrtPriceX96": result[0],
#         "tick": result[1],
#         "observationIndex": result[2],
#         "observationCardinality": result[3],
#         "observationCardinalityNext": result[4],
#         "feeProtocol": result[5],
#         "unlocked": result[6]
#     }
    
#     return details

def get_slot0_info(pool_address, w3):
    abi_uniswap = [
        {
            "inputs": [],
            "name": "slot0",
            "outputs": [
                {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                {"internalType": "int24", "name": "tick", "type": "int24"},
                {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
                {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
                {"internalType": "bool", "name": "unlocked", "type": "bool"},
            ],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    
    abi_aerodrome = [
        {
            "inputs": [],
            "name": "slot0",
            "outputs": [
                {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                {"internalType": "int24", "name": "tick", "type": "int24"},
                {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
                {"internalType": "bool", "name": "unlocked", "type": "bool"},
            ],
            "stateMutability": "view",
            "type": "function",
        }
    ]
    
    contract_address = Web3.to_checksum_address(pool_address)
    
    # Try to use the Uniswap ABI
    try:
        contract = w3.eth.contract(address=contract_address, abi=abi_uniswap)
        result = contract.functions.slot0().call()
        return {
            "sqrtPriceX96": result[0],
            "tick": result[1]
        }
    except (web3.exceptions.ContractLogicError, web3.exceptions.BadFunctionCallOutput):
        # If Uniswap ABI fails, use the Aerodrome ABI
        try:
            contract = w3.eth.contract(address=contract_address, abi=abi_aerodrome)
            result = contract.functions.slot0().call()
            return {
                "sqrtPriceX96": result[0],
                "tick": result[1]
            }
        except (web3.exceptions.ContractLogicError, web3.exceptions.BadFunctionCallOutput):
            return None

def get_account_data(account_address, w3):
    
    account_abi = [{
        "inputs": [],
        "name": "generateAssetData",
        "outputs": [
            {
                "internalType": "address[]",
                "name": "assetAddresses",
                "type": "address[]",
            },
            {"internalType": "uint256[]", "name": "assetIds", "type": "uint256[]"},
            {"internalType": "uint256[]", "name": "assetAmounts", "type": "uint256[]"},
        ],
        "stateMutability": "view",
        "type": "function",
    }]
    
    try:
        # Pool contract
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(account_address), 
            abi=account_abi
        )
        data = contract.functions.generateAssetData().call()
        return data
    except Exception as e:
        return f'Error fetching pool_oracle: {e}'
    

def get_position_state_info(contract_address, nft_token_id, w3):
    abi = [
        {
        "inputs": [{"internalType": "uint256", "name": "position", "type": "uint256"}],
        "name": "positionState",
        "outputs": [
            {"internalType": "int24", "name": "tickLower", "type": "int24"},
            {"internalType": "int24", "name": "tickUpper", "type": "int24"},
            {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
            {"internalType": "address", "name": "gauge", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
        }
    ]
    contract_address = Web3.to_checksum_address(contract_address)
    
    contract = w3.eth.contract(address=contract_address, abi=abi)
    result = contract.functions.positionState(nft_token_id).call()
    
    return {
            "tickLower": result[0],
            "tickUpper": result[1],
            "liquidity": result[2],
            "gauge": result[3]
        }
    
    
    
def get_arcadia_account_nft_position(asset_data, w3):
    
    POOL_NFT_MAPPINGS = [
        # Uniswap v3 Pools
        {
            "name": "wETH-USDC",
            "pool": "0xd0b53D9277642d899DF5C87A3966A349A798F224",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x4200000000000000000000000000000000000006",
            "token1": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimal0": 18,
            "decimal1": 6
        },
        {
            "name": "wETH-USDbC",
            "pool": "0x4C36388bE6F416A29C8d8Eee81C771cE6bE14B18",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x4200000000000000000000000000000000000006",
            "token1": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "decimal0": 18,
            "decimal1": 6
        },
        {
            "name": "wETH-wstETH",
            "pool": "0x20E068D76f9E90b90604500B84c7e19dCB923e7e",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x4200000000000000000000000000000000000006",
            "token1": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
            "decimal0": 18,
            "decimal1": 18
        },
        {
            "name": "cbETH-wETH",
            "pool": "0x10648BA41B8565907Cfa1496765fA4D95390aa0d",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
            "token1": "0x4200000000000000000000000000000000000006",
            "decimal0": 18,
            "decimal1": 18
        },
        {
            "name": "USDC-USDbC",
            "pool": "0x06959273E9A65433De71F5A452D529544E07dDD0",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "token1": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "decimal0": 6,
            "decimal1": 6
        },
        {
            "name": "DAI-USDbC",
            "pool": "0x22F9623817F152148B4E080E98Af66FBE9C5AdF8",
            "gauge": "",
            "nft": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1",
            "token0": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
            "token1": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "decimal0": 18,
            "decimal1": 6
        },
        
        # Aerodrome Pools
        {
            "name": "wETH-wstETH",
            "pool": "0x861A2922bE165a5Bd41b1E482B49216b465e1B5F",
            "gauge": "0x2A1f7bf46bd975b5004b61c6040597E1B6117040",
            "nft": "0x827922686190790b37229fd06084350E74485b72",
            "token0": "0x4200000000000000000000000000000000000006",
            "token1": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
            "decimal0": 18,
            "decimal1": 18
        },
        {
            "name": "cbETH-wETH",
            "pool": "0x47cA96Ea59C13F72745928887f84C9F52C3D7348",
            "gauge": "0xF5550F8F0331B8CAA165046667f4E6628E9E3Aac",
            "nft": "0x827922686190790b37229fd06084350E74485b72",
            "token0": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
            "token1": "0x4200000000000000000000000000000000000006",
            "decimal0": 18,
            "decimal1": 18
        },
        {
            "name": "USDC-USDbC",
            "pool": "0x98c7A2338336d2d354663246F64676009c7bDa97",
            "gauge": "0x4a3E1294d7869567B387FC3d5e5Ccf14BE2Bbe0a",
            "nft": "0x827922686190790b37229fd06084350E74485b72",
            "token0": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "token1": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "decimal0": 6,
            "decimal1": 6
        },
        {
            "name": "wETH-USDC",
            "pool": "0xb2cc224c1c9feE385f8ad6a55b4d94E92359DC59",
            "gauge": "0xF33a96b5932D9E9B9A0eDA447AbD8C9d48d2e0c8",
            "nft": "0x827922686190790b37229fd06084350E74485b72",
            "token0": "0x4200000000000000000000000000000000000006",
            "token1": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "decimal0": 18,
            "decimal1": 6
        },
        {
            "name": "AERO-wstETH",
            "pool": "0x565aecF84b5d30a6E79a5CEf3f0dA0Fc4280dEBC",
            "gauge": "0x45F8b8eC9c92D09BA8495074436fD97073423041",
            "nft": "0x827922686190790b37229fd06084350E74485b72",
            "token0": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
            "token1": "0xc1CBa3fCea344f92D9239c08C0568f6F2F0ee452",
            "decimal0": 18,
            "decimal1": 18
        }
    ]
    
    zero_indices = [index for index, value in enumerate(asset_data[1]) if value == 0]
    non_zero_indices = [index for index, value in enumerate(asset_data[1]) if value != 0]

    result = defaultdict(int)

    # Creating a lookup dictionary for quick access with normalized tokens
    pool_lookup = {}
    gauge_lookup = {}

    for pool in POOL_NFT_MAPPINGS:
        nft = pool["nft"].lower()
        token0 = pool["token0"].lower()
        token1 = pool["token1"].lower()
        gauge = pool["gauge"].lower() if pool["gauge"] else ""

        pool_lookup[(nft, token0, token1)] = pool
        if gauge:
            gauge_lookup[gauge] = pool

    for i in zero_indices:
        add_or_update_dict(result, asset_data[0][i], asset_data[2][i])
    
    for i in non_zero_indices:
        staked_slipstream = "0x1Dc7A0f5336F52724B650E39174cfcbbEdD67bF1".lower()
        nft_contract = asset_data[0][i].lower()
        nft_token_id = asset_data[1][i]
        
        if nft_contract == staked_slipstream:
            staked_slipstream_data = get_position_state_info(nft_contract, nft_token_id, w3)
            matching_pool = gauge_lookup.get(staked_slipstream_data['gauge'].lower())
            
            if not matching_pool:
                add_or_update_dict(result, nft_contract, 0)  # No matching pool found
                continue  # Skip to the next iteration
            
            lower_tick = staked_slipstream_data["tickLower"]
            upper_tick = staked_slipstream_data["tickUpper"]
            liquidity = staked_slipstream_data["liquidity"]
            
        else:
            nft_positions_details = get_nft_positions_details(nft_contract_address=nft_contract, w3=w3, token_id=nft_token_id)
            
            if not nft_positions_details:
                add_or_update_dict(result, nft_contract, 0)  # Records the NFT if it does not belong to Uniswap
                continue  # Skip if nft_positions_details could not be fetched
            
            # Extracting and normalizing token0 and token1 from nft_positions_details
            token0 = nft_positions_details["token0"].lower()
            token1 = nft_positions_details["token1"].lower()

            # Finding the matching pool using the lookup dictionary
            matching_pool = pool_lookup.get((nft_contract, token0, token1))
            
            if not matching_pool:
                add_or_update_dict(result, nft_contract, 0)  # No matching pool found
                continue  # Skip to the next iteration
            
            lower_tick = nft_positions_details["tickLower"]
            upper_tick = nft_positions_details["tickUpper"]
            liquidity = nft_positions_details["liquidity"]
            
        slot0 = get_slot0_info(pool_address=matching_pool["pool"], w3=w3)
        if not slot0:
            continue  # Skip if slot0 details could not be fetched
        
        current_tick = slot0["tick"]
        
        amount0, amount1 = get_amounts_from_ticks(current_tick, lower_tick, upper_tick, liquidity)
                
        add_or_update_dict(result, matching_pool["token0"], amount0)
        add_or_update_dict(result, matching_pool["token1"], amount1)
    
    return result
