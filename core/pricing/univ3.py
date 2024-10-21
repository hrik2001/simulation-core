import math

import web3
from web3 import Web3


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


def get_liquidity_for_amount0(sqrtRatioAX96, sqrtRatioBX96, amount0):
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    intermediate = sqrtRatioAX96 * sqrtRatioBX96 // (2**96)
    return amount0 * intermediate // (sqrtRatioBX96 - sqrtRatioAX96)


def get_liquidity_for_amount1(sqrtRatioAX96, sqrtRatioBX96, amount1):
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    return amount1 * (2**96) // (sqrtRatioBX96 - sqrtRatioAX96)


def liquidity_from_amounts(currentPrice, lowerPrice, upperPrice, amount0, amount1):
    tickCurrent = sqrt_price_x96_to_tick(sqrt_price_from_price(currentPrice))
    tickLower = sqrt_price_x96_to_tick(sqrt_price_from_price(lowerPrice))
    tickUpper = sqrt_price_x96_to_tick(sqrt_price_from_price(upperPrice))

    sqrtRatioX96 = get_sqrt_ratio_at_tick(tickCurrent)
    sqrtRatioAX96 = get_sqrt_ratio_at_tick(tickLower)
    sqrtRatioBX96 = get_sqrt_ratio_at_tick(tickUpper)

    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    if sqrtRatioX96 <= sqrtRatioAX96:
        return get_liquidity_for_amount0(sqrtRatioAX96, sqrtRatioBX96, amount0)
    elif sqrtRatioX96 < sqrtRatioBX96:
        liquidity0 = get_liquidity_for_amount0(sqrtRatioX96, sqrtRatioBX96, amount0)
        liquidity1 = get_liquidity_for_amount1(sqrtRatioAX96, sqrtRatioX96, amount1)
        return min(liquidity0, liquidity1)
    else:
        return get_liquidity_for_amount1(sqrtRatioAX96, sqrtRatioBX96, amount1)


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


# def amounts_from_liquidity(currentPrice, lowerPrice, upperPrice, liquidity):
#     sqrtCurrentPrice = sqrt_price_from_price(currentPrice)
#     sqrtLowerPrice = sqrt_price_from_price(lowerPrice)
#     sqrtUpperPrice = sqrt_price_from_price(upperPrice)
#
#     amount0, amount1 = 0, 0
#     if sqrtCurrentPrice <= sqrtLowerPrice:
#         amount0 = get_amount0_for_liquidity(sqrtLowerPrice, sqrtUpperPrice, liquidity)
#     elif sqrtCurrentPrice < sqrtUpperPrice:
#         amount0 = get_amount0_for_liquidity(sqrtLowerPrice, sqrtUpperPrice, liquidity)
#         amount1 = get_amount1_for_liquidity(sqrtLowerPrice, sqrtCurrentPrice, liquidity)
#     else:
#         amount1 = get_amount1_for_liquidity(sqrtLowerPrice, sqrtUpperPrice, liquidity)
#
#     return amount0, amount1


def get_amounts_from_liquidity(currentPrice, lowerPrice, upperPrice, liquidity):
    """Compute the token0 and token1 value for a given amount of liquidity and prices."""

    tickCurrent = sqrt_price_x96_to_tick(sqrt_price_from_price(currentPrice))
    tickLower = sqrt_price_x96_to_tick(sqrt_price_from_price(lowerPrice))
    tickUpper = sqrt_price_x96_to_tick(sqrt_price_from_price(upperPrice))

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


def find_matching_liquidity(
    total_value,
    upper_price,
    current_price,
    lower_price,
    token0_price,
    token0_decimals_,
    token1_price,
    token1_decimals_,
    tolerance=0.00001,
    max_iterations=10000,
):
    token0_amount = 100000000 * 10**token0_decimals_
    token1_amount = 100000000 * 10**token1_decimals_

    liquidity_guess = liquidity_from_amounts(
        currentPrice=current_price,
        lowerPrice=lower_price,
        upperPrice=upper_price,
        amount0=token0_amount,
        amount1=token1_amount,
    )
    if liquidity_guess == 0:
        liquidity_guess = 1

    for i in range(max_iterations):
        _amount_0, _amount_1 = get_amounts_from_liquidity(
            currentPrice=current_price,
            lowerPrice=lower_price,
            upperPrice=upper_price,
            liquidity=liquidity_guess,
        )

        _current_value_0 = _amount_0 / (10**token0_decimals_) * token0_price
        _current_value_1 = _amount_1 / (10**token1_decimals_) * token1_price
        diff = total_value - (_current_value_0 + _current_value_1)
        diff_fraction = diff / total_value

        if diff_fraction == 1:
            diff_fraction = 0.99999

        # Check if the difference is within the specified tolerance
        if abs(diff_fraction) <= tolerance and diff_fraction >= 0:
            return (
                liquidity_guess,
                _amount_0,
                _amount_1,
                _current_value_0,
                _current_value_1,
                i,
            )

        # Adjust the liquidity guess. This factor can be tuned for better convergence.
        liquidity_old = liquidity_guess
        liquidity_guess = int(liquidity_guess / (1 - diff_fraction))
        if liquidity_guess == liquidity_old - 1:
            liquidity_guess = max(liquidity_guess - 1000, 1000)

    raise Exception("Failed to converge within the maximum number of iterations")


def initiate_liquidity_position(
    _usd_value_invested,
    _token0_price_in_usd,
    _token1_price_in_usd,
    _interval_spread: float = 0.1,
):
    _token0_decimals = 18
    _token1_decimals = 18

    _current_price = (_token0_price_in_usd / _token1_price_in_usd) * 10 ** (
        _token1_decimals - _token0_decimals
    )
    _lower_price = (
        _current_price
        * (1 - _interval_spread)
        * 10 ** (_token1_decimals - _token0_decimals)
    )
    _upper_price = (
        _current_price
        * (1 + _interval_spread)
        * 10 ** (_token1_decimals - _token0_decimals)
    )

    (
        _liquidity_guess,
        _amount_0,
        _amount_1,
        _current_value_0,
        _current_value_1,
        _i,
    ) = find_matching_liquidity(
        _usd_value_invested,
        _upper_price,
        _current_price,
        _lower_price,
        _token0_price_in_usd,
        _token0_decimals,
        _token1_price_in_usd,
        _token1_decimals,
    )
    adjusted_amount_0 = _amount_0 / (10**_token0_decimals)
    adjusted_amount_1 = _amount_1 / (10**_token1_decimals)
    return (
        _liquidity_guess,
        _lower_price,
        _upper_price,
        adjusted_amount_0,
        adjusted_amount_1,
    )


def get_value_of_lp(
    _liquidity_guess,
    _lower_price,
    _upper_price,
    token0_price_in_usd,
    token1_price_in_usd,
):
    _token0_decimals = 18
    _token1_decimals = 18

    _current_price = (token0_price_in_usd / token1_price_in_usd) * 10 ** (
        _token1_decimals - _token0_decimals
    )
    _amount_0, _amount_1 = get_amounts_from_liquidity(
        _current_price, _lower_price, _upper_price, _liquidity_guess
    )
    _current_value_0 = _amount_0 / (10**_token0_decimals) * token0_price_in_usd
    _current_value_1 = _amount_1 / (10**_token1_decimals) * token1_price_in_usd
    _total_value = _current_value_0 + _current_value_1
    return _total_value


# Define the dummy ABI for the positions function
dummy_abi = [
    {
        "constant": True,
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "positions",
        "outputs": [
            {"name": "nonce", "type": "uint96"},
            {"name": "operator", "type": "address"},
            {"name": "token0", "type": "address"},
            {"name": "token1", "type": "address"},
            {"name": "fee", "type": "uint24"},
            {"name": "tickLower", "type": "int24"},
            {"name": "tickUpper", "type": "int24"},
            {"name": "liquidity", "type": "uint128"},
            {"name": "feeGrowthInside0LastX128", "type": "uint256"},
            {"name": "feeGrowthInside1LastX128", "type": "uint256"},
            {"name": "tokensOwed0", "type": "uint128"},
            {"name": "tokensOwed1", "type": "uint128"},
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function",
    }
]


# Define the function to get positions details
def get_positions_details(contract_address, w3, token_id):
    contract_address = Web3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=dummy_abi)
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


if __name__ == "__main__":
    # Test the functions
    usd_value_invested = 10_000
    token0_price_in_usd = 3000
    token1_price_in_usd = 1
    interval_spread = 0.1  # %10

    (
        liquidity_guess,
        lower_price,
        upper_price,
        amount_0,
        amount_1,
    ) = initiate_liquidity_position(
        usd_value_invested,
        token0_price_in_usd,
        token1_price_in_usd,
        interval_spread,
    )

    print(
        f"Initial liquidity guess: {liquidity_guess}, Lower price: {lower_price}, Upper price: {upper_price}, Amount0: {amount_0}, Amount1: {amount_1}"
    )
    total_value_at_t1 = get_value_of_lp(
        liquidity_guess,
        lower_price,
        upper_price,
        token0_price_in_usd,
        token1_price_in_usd,
    )
    print(f"Total value at t1: {total_value_at_t1}")

    token0_price_in_usd_t2 = 1500

    total_value = get_value_of_lp(
        liquidity_guess,
        lower_price,
        upper_price,
        token0_price_in_usd_t2,
        token1_price_in_usd,
    )
    print(
        f"Token0 price at t2: {token0_price_in_usd_t2}, Token1 price at t2: {token1_price_in_usd}"
    )
    print(f"Total value at t2: {total_value}")
