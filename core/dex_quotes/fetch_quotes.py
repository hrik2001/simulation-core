import time
import itertools
import numpy as np
from .utils import compute_sampling_points
from .quote_requests import kyperswap, paraswap, cowswap

from .price_fetcher import get_current_price
from .DTO import TOKEN_DTOs
from core.models import DexQuote, DexQuotePair

MAXIMUM_PRICE_IMPACT = 0.99 # stop requesting quotes above this amount
SLEEP_TIME_BETWEEN_REQUESTS = 1.1 # seconds

def kyperswap_job(network = None, num_samples = 30):

    stopping_criteria = 0 

    if network is not None:
        print(f'{network}')

        asset_permutations = DexQuotePair.objects.filter(src_asset__chain__chain_name__iexact=network, ingest=True)

        for permutation in asset_permutations:
            sell_token = permutation.src_asset
            buy_token = permutation.dst_asset

            for amount in compute_sampling_points(sell_token, buy_token, num_samples):
                try:
                    new_row = kyperswap.get_quote(
                        src_token=sell_token.contract_address, 
                        src_decimals=sell_token.decimals, 
                        dest_token=buy_token.contract_address, 
                        dest_decimals=buy_token.decimals, 
                        usd_amount=amount, 
                        market_price=get_current_price(sell_token.contract_address, network.lower()),
                        network_id=sell_token.chain.chain_id,
                    )

                    record = DexQuote(pair=permutation, **new_row)
                    record.save()

                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                if new_row.get('price_impact', 0) > MAXIMUM_PRICE_IMPACT: 
                    break
                else:
                    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)

def paraswap_job(network = None, num_samples = 30):

    stopping_criteria = 0 
    if network is not None:
        print(f'{network}')

        asset_permutations = DexQuotePair.objects.filter(src_asset__chain__chain_name__iexact=network, ingest=True)

        for permutation in asset_permutations:
            sell_token = permutation.src_asset
            buy_token = permutation.dst_asset

            for amount in compute_sampling_points(sell_token, buy_token, num_samples):
                try:
                    new_row = paraswap.get_quote(
                        src_token=sell_token.contract_address, 
                        src_decimals=sell_token.decimals, 
                        dest_token=buy_token.contract_address, 
                        dest_decimals=buy_token.decimals, 
                        usd_amount=amount, 
                        market_price=get_current_price(sell_token.contract_address, network.lower()),
                        network_id=sell_token.chain.chain_id,
                    )

                    record = DexQuote(pair=permutation, **new_row)
                    record.save()

                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                if new_row.get('price_impact', 0) > MAXIMUM_PRICE_IMPACT: 
                    break
                else:
                    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)

def cowswap_job(network = None, num_samples = 30):

    stopping_criteria = 0 
    if network is not None:
        print(f'{network}')

        asset_permutations = DexQuotePair.objects.filter(src_asset__chain__chain_name__iexact=network, ingest=True)

        for permutation in asset_permutations:
            sell_token = permutation.src_asset
            buy_token = permutation.dst_asset

            for amount in compute_sampling_points(sell_token, buy_token, num_samples):
                try:
                    new_row = cowswap.get_quote(
                        src_token=sell_token.contract_address, 
                        src_decimals=sell_token.decimals, 
                        dest_token=buy_token.contract_address, 
                        dest_decimals=buy_token.decimals, 
                        src_usd_amount=amount, 
                        src_price=get_current_price(sell_token.contract_address, network.lower()),
                        dst_price=get_current_price(buy_token.contract_address, network.lower()),
                        network_id=sell_token.chain.chain_id,
                    )

                    record = DexQuote(pair=permutation, **new_row)
                    record.save()

                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                if new_row.get('price_impact', 0) > MAXIMUM_PRICE_IMPACT: 
                    break
                else:
                    time.sleep(SLEEP_TIME_BETWEEN_REQUESTS)
