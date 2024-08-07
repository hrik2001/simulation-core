import time
import itertools
import numpy as np

from .quote_requests import kyperswap, paraswap

from .price_fetcher import get_current_price
from .DTO import TOKEN_DTOs
from core.models import DexQuote

def paraswap_job(
        start_amount = 100,
        end_amount = 50_000_100,
        num_samples = 30,
    ):
    amounts = np.geomspace(start_amount, end_amount, num=num_samples).astype(int).tolist()

    stopping_criteria = 0 



    # Iterate over networks
    for network in TOKEN_DTOs.keys():
        print(f'{network}')

        # Generate asset permutations for a given network 
        asset_permutations = list(itertools.permutations(TOKEN_DTOs[network].values(), 2))

        # Iterate over each permutation
        for permutation in asset_permutations:
            sell_token = permutation[0]
            buy_token = permutation[1]

            # Fetch sell token price 
            price = get_current_price(sell_token.address, sell_token.network.network.lower())

            # Iterate through the generated amounts and fetch quotes
            for amount in amounts:
                # if len(query_amounts) < 2:
                #     query_amounts.append(query_amounts[0])  # Ensure we have two amounts

                # print(f"Fetching Quotes[{sell_token.address} <> {buy_token.address}] || Order Size (USD): {query_amounts}")


                try:
                    # new_row = paraswap.get_quote(
                        # src_token=sell_token.address, 
                        # src_decimals=sell_token.decimals, 
                        # dest_token=buy_token.address, 
                        # dest_decimals=buy_token.decimals, 
                        # usd_amount=query_amounts[0], 
                        # market_price=price,
                        # network_id=sell_token.network.network_id
                    # )



                    new_row2 = kyperswap.get_quote(
                        src_token=sell_token.address, 
                        src_decimals=sell_token.decimals, 
                        dest_token=buy_token.address, 
                        dest_decimals=buy_token.decimals, 
                        usd_amount=amount, 
                        market_price=price,
                        network_id=sell_token.network.network_id
                    )
                    print(new_row2)



                    stopping_criteria = new_row2.get('price_impact', 0)
                    record = DexQuote(**new_row2)
                    record.save()


                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                # Early stopping criteria 
                if stopping_criteria > 0.99: 
                    break
                else:
                    # Sleep for a short duration to avoid hitting the rate limit of the API
                    time.sleep(1.1)  # Adjust the sleep duration if necessary

def kyperswap_job(
        start_amount = 100,
        end_amount = 50_000_100,
        num_samples = 30,
    ):
    amounts = np.geomspace(start_amount, end_amount, num=num_samples).astype(int).tolist()

    stopping_criteria = 0 



    # Iterate over networks
    for network in TOKEN_DTOs.keys():
        print(f'{network}')

        # Generate asset permutations for a given network 
        asset_permutations = list(itertools.permutations(TOKEN_DTOs[network].values(), 2))

        # Iterate over each permutation
        for permutation in asset_permutations:
            sell_token = permutation[0]
            buy_token = permutation[1]

            # Fetch sell token price 
            price = get_current_price(sell_token.address, sell_token.network.network.lower())

            # Iterate through the generated amounts and fetch quotes
            for amount in amounts:
                # if len(query_amounts) < 2:
                #     query_amounts.append(query_amounts[0])  # Ensure we have two amounts

                # print(f"Fetching Quotes[{sell_token.address} <> {buy_token.address}] || Order Size (USD): {query_amounts}")


                try:
                    new_row = paraswap.get_quote(
                        src_token=sell_token.address, 
                        src_decimals=sell_token.decimals, 
                        dest_token=buy_token.address, 
                        dest_decimals=buy_token.decimals, 
                        usd_amount=amount, 
                        market_price=price,
                        network_id=sell_token.network.network_id
                    )



                    # new_row2 = kyperswap.get_quote(
                    #     src_token=sell_token.address, 
                    #     src_decimals=sell_token.decimals, 
                    #     dest_token=buy_token.address, 
                    #     dest_decimals=buy_token.decimals, 
                    #     usd_amount=query_amounts[1], 
                    #     market_price=price,
                    #     network_id=sell_token.network.network_id
                    # )
                    # print(new_row2)



                    stopping_criteria = new_row.get('price_impact', 0)
                    record = DexQuote(**new_row)
                    record.save()


                except Exception as e:
                    print(f"Failed to save entry to DB: {e}")

                # Early stopping criteria 
                if stopping_criteria > 0.99: 
                    break
                else:
                    # Sleep for a short duration to avoid hitting the rate limit of the API
                    time.sleep(1.1)  # Adjust the sleep duration if necessary
