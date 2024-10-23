
import time
import pandas as pd
import requests

def get_quotes(src, dst, page_size=1000, page_sleep=1) -> pd.DataFrame: 
     
    page = 1
    page_count = -1
    all_quotes = []

    print("retrieving quotes ...")

    while page != page_count+1:
        
        url = f"https://api.llamarisk.com/api/quotes?src={src}&dst={dst}&page={page}&max_rows={page_size}"
        res = requests.get(url, timeout=60)
        res.raise_for_status()

        data = res.json()

        if page_count == -1:
            page_count = data['pagination']['total_pages']

        print(f'processing page {page}/{page_count}')

        quotes = pd.DataFrame(data['quotes'])
        quotes["src"] = quotes["src"].str.lower()
        quotes["dst"] = quotes["dst"].str.lower()
        all_quotes.append(quotes)

        page+=1
        time.sleep(page_sleep)

    if all_quotes:
        combined_quotes = pd.concat(all_quotes)
        combined_quotes = combined_quotes.set_index(["src", "dst"])
        return combined_quotes
    else:
        return pd.DataFrame()