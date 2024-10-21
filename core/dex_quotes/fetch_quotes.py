import itertools
import time

import numpy as np

from core.models import DexQuote, DexQuotePair

from .DTO import TOKEN_DTOs
from .price_fetcher import get_current_price
from .quote_requests import kyperswap, paraswap
from .utils import compute_sampling_points


def kyperswap_job(
    network=None,
    num_samples=30,
):
    stopping_criteria = 0

    if network is not None:
        print(f"{network}")

        # asset_permutations = list(itertools.permutations(TOKEN_DTOs[network].values(), 2))
        asset_permutations = DexQuotePair.objects.filter(
            src_asset__chain__chain_name__iexact=network, ingest=True
        )

        for permutation in asset_permutations:
            # sell_token = permutation[0]
            # buy_token = permutation[1]
            sell_token = permutation.src_asset
            buy_token = permutation.dst_asset

            amounts = compute_sampling_points(sell_token, buy_token, num_samples)

            price = get_current_price(sell_token.contract_address, network.lower())

            for amount in amounts:
                try:
                    new_row2 = kyperswap.get_quote(
                        src_token=sell_token.contract_address,
                        src_decimals=sell_token.decimals,
                        dest_token=buy_token.contract_address,
                        dest_decimals=buy_token.decimals,
                        usd_amount=amount,
                        market_price=price,
                        network_id=sell_token.chain.chain_id,
                    )

                    stopping_criteria = new_row2.get("price_impact", 0)
                    record = DexQuote(pair=permutation, **new_row2)
                    record.save()

                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                if stopping_criteria > 0.99:
                    break
                else:
                    time.sleep(1.1)  # Adjust the sleep duration if necessary


def paraswap_job(
    network=None,
    num_samples=30,
):
    stopping_criteria = 0
    if network is not None:
        print(f"{network}")

        asset_permutations = DexQuotePair.objects.filter(
            src_asset__chain__chain_name__iexact=network, ingest=True
        )
        # asset_permutations = list(itertools.permutations(TOKEN_DTOs[network].values(), 2))

        for permutation in asset_permutations:
            # sell_token = permutation[0]
            # buy_token = permutation[1]
            sell_token = permutation.src_asset
            buy_token = permutation.dst_asset

            amounts = compute_sampling_points(sell_token, buy_token, num_samples)

            price = get_current_price(sell_token.contract_address, network.lower())

            for amount in amounts:
                try:
                    new_row = paraswap.get_quote(
                        src_token=sell_token.contract_address,
                        src_decimals=sell_token.decimals,
                        dest_token=buy_token.contract_address,
                        dest_decimals=buy_token.decimals,
                        usd_amount=amount,
                        market_price=price,
                        network_id=sell_token.chain.chain_id,
                    )

                    stopping_criteria = new_row.get("price_impact", 0)
                    record = DexQuote(pair=permutation, **new_row)
                    record.save()

                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                # Early stopping criteria
                if stopping_criteria > 0.99:
                    break
                else:
                    # Sleep for a short duration to avoid hitting the rate limit of the API
                    time.sleep(1.1)  # Adjust the sleep duration if necessary
