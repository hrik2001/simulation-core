import math
from functools import partial
from numpy import exp


def exponential_function(coefficient, exponent_base, decimals, x):
    # _in = x / 10**decimals
    _in = x
    # return coefficient * math.exp(exponent_base * _in)
    return coefficient * exp(exponent_base * _in)


def linear_function(coefficient, constant, decimals, x):
    # _in = x / 10**decimals
    _in = x
    return coefficient * _in + constant


def no_slippage(x):
    return 0


class SlippageCalculator:
    slippage_functions = {
        # dai
        "0x50c5725949a6f0c72e6c4a641f24049a917db0cb": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(
                exponential_function, 0.165, 2.71e-06, 18
            ),
            "0x4200000000000000000000000000000000000006": partial(
                linear_function, 4.36e-07, 2.34e-03, 18
            ),
        },
        # comp
        # "0x9e1028F5F1D5eDE59748FFceE5532509976840E0": {
        #     "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(exponential_function, 0.0102, 1.69E-06, 18),
        #     "0x4200000000000000000000000000000000000006": partial(exponential_function, 0.0102, 1.69E-06, 18),
        # },
        # weth
        "0x4200000000000000000000000000000000000006": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(
                exponential_function, 0.0429, 6.18e-03, 18
            ),
            "0x4200000000000000000000000000000000000006": partial(no_slippage),
        },
        # usdc
        "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(no_slippage),
            "0x4200000000000000000000000000000000000006": partial(
                exponential_function, 0.0356, 3.95e-06, 6
            ),
        },
        # cbeth
        "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(
                exponential_function, 0.0424, 9.75e-03, 18
            ),
            "0x4200000000000000000000000000000000000006": partial(
                exponential_function, 0.0264, 8.78e-03, 18
            ),
        },
        # reth
        "0xb6fe221fe9eef5aba221c348ba20a1bf5e73624c": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(
                exponential_function, 0.0292, 0.0172, 18
            ),
            "0x4200000000000000000000000000000000000006": partial(
                exponential_function, 0.0113, 0.0209, 18
            ),
        },
        # usdbc
        "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca": {
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913": partial(
                exponential_function, 0.0102, 1.69e-06, 6
            ),
            "0x4200000000000000000000000000000000000006": partial(
                exponential_function, 0.0808, 2.56e-06, 6
            ),
        },
    }

    def __init__(self):
        pass

    def get_slippage(self, token_in, token_out, amount):
        lower_token_in = token_in.lower()
        lower_token_out = token_out.lower()
        if lower_token_in in self.slippage_functions:
            if lower_token_out in self.slippage_functions[lower_token_in]:
                return self.slippage_functions[lower_token_in][lower_token_out](amount)
            else:
                return 0
                # raise Exception(f"Token {token_out} not found in slippage functions for token {token_in}")
        else:
            return 0
            # raise Exception(f"Token {token_in} not found in slippage functions")


if __name__ == "__main__":
    slippage_config = SlippageCalculator()

    def test_slippage():
        slippage_dai_usdc = slippage_config.get_slippage(
            "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            1000 * 1e18,
        )

        slippage_dai_weth = slippage_config.get_slippage(
            "0x50c5725949a6f0c72e6c4a641f24049a917db0cb",
            "0x4200000000000000000000000000000000000006",
            1000 * 1e18,
        )

        slippage_weth_usdc = slippage_config.get_slippage(
            "0x4200000000000000000000000000000000000006",
            "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
            10 * 1e18,
        )

        slippage_weth_weth = slippage_config.get_slippage(
            "0x4200000000000000000000000000000000000006",
            "0x4200000000000000000000000000000000000006",
            10 * 1e18,
        )

        slippage_usdc_usdc = slippage_config.get_slippage(
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            10 * 1e6,
        )

        slippage_usdc_weth = slippage_config.get_slippage(
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            "0x4200000000000000000000000000000000000006",
            10 * 1e6,
        )
        slippage_cbeeth_usdc = slippage_config.get_slippage(
            "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            10 * 1e18,
        )
        slippage_cbeeth_weth = slippage_config.get_slippage(
            "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
            "0x4200000000000000000000000000000000000006",
            10 * 1e18,
        )
        slippage_reteth_usdc = slippage_config.get_slippage(
            "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c",
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            10 * 1e18,
        )
        slippage_reteth_weth = slippage_config.get_slippage(
            "0xB6fe221Fe9EeF5aBa221c348bA20A1Bf5e73624c",
            "0x4200000000000000000000000000000000000006",
            10 * 1e18,
        )
        slippage_usdbc_usdc = slippage_config.get_slippage(
            "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            10 * 1e6,
        )
        slippage_usdbc_weth = slippage_config.get_slippage(
            "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
            "0x4200000000000000000000000000000000000006",
            10 * 1e6,
        )

        assert slippage_dai_usdc == 0.1654477564359401
        assert slippage_dai_weth == 0.002776
        assert slippage_weth_usdc == 0.04563485670473372
        assert slippage_weth_weth == 0
        assert slippage_usdc_usdc == 0
        assert slippage_usdc_weth == 0.03560140622777282
        assert slippage_cbeeth_usdc == 0.04674224512228503
        assert slippage_cbeeth_weth == 0.028822721300791394
        assert slippage_reteth_usdc == 0.03468019272984606
        assert slippage_reteth_weth == 0.013926628483391879
        assert slippage_usdbc_usdc == 0.01020017238145662
        assert slippage_usdbc_weth == 0.08080206850647677

    test_slippage()
