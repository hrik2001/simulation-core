"""
Plotting functions for 1inch quotes 
and generated price impact curves.
"""
import sys, os
import numpy as np
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from external_market import ExternalMarket
from sklearn.isotonic import IsotonicRegression

# Add '../core' to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from core.dex_quotes.DTO import TokenDTO

S = 5

def plot_simple(quotes_df, in_token, out_token, timestamp, liquidation_bonus=0.075): 

    if timestamp != None: # only display data for the provided timestamp
        closest_timestamp_value = quotes_df.loc[(quotes_df['timestamp'] - timestamp).abs().idxmin(), 'timestamp'].iloc[0]
        quotes_df = quotes_df[quotes_df['timestamp'] == closest_timestamp_value].sort_values('in_amount')

    quotes_df['price_impact'].clip(lower=0, upper=1)
    quotes_df['in_amount'] = quotes_df['in_amount']/(10**in_token.decimals)
    
    plt.figure(figsize=(10, 6))
    
    for ts in quotes_df['timestamp'].unique(): 
        plt.scatter(quotes_df[quotes_df['timestamp'] == ts]['in_amount'],  
                    quotes_df[quotes_df['timestamp'] == ts]['price_impact'],  
                    label=f'{datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')}', alpha=0.5)

    price_impact = quotes_df['in_amount'].iloc[np.abs(quotes_df['price_impact'] - liquidation_bonus).argmin()]
    plt.axvline(x=price_impact, color='r', linestyle='--', label=f'{liquidation_bonus*100}% price impact = {int(price_impact)}')
        
    plt.xlabel('In Amount') 
    plt.ylabel('Price Impact') 
    plt.xscale('log') 
    plt.title(f'Price Impact vs In Amount for {in_token.symbol} to {out_token.symbol}') 
    plt.grid(True) 
    plt.legend() 
    plt.show()

# pylint: disable=too-many-arguments, too-many-locals
def plot_regression(
    df: pd.DataFrame,
    i: int,
    j: int,
    market: ExternalMarket,
    fn: str | None = None,
    scale: str = "log",
    xlim: float | None = None,
    liquidation_bonus = 0.075
) -> plt.Figure:
    """
    Plot price impact from 1inch quotes against
    predicted price impact from market model.
    """
    in_token = market.coins[i]
    out_token = market.coins[j]

    x = np.geomspace(df["in_amount"].min(), df["in_amount"].max(), 100)
    y = market.price_impact_many(i, j, x) * 100

    f, ax = plt.subplots(figsize=(10, 5))

    price_impact = df['in_amount'].iloc[np.abs(df['price_impact'] - liquidation_bonus).argmin()] / 10**in_token.decimals
    ax.axvline(x=price_impact, color='r', linestyle='--', label=f'{liquidation_bonus*100}% price impact = {int(price_impact)}')

    scatter = ax.scatter(
        df["in_amount"] / 10**in_token.decimals,
        df["price_impact"] * 100,
        c=df["timestamp"],
        s=S,
        label="Quotes",
    )
    ax.plot(x / 10**in_token.decimals, y, label="Prediction", c="indianred", lw=2)
    ax.set_xscale(scale)
    ax.legend()
    ax.set_xlabel(f"Amount in ({in_token.symbol})")
    ax.set_ylabel("Price Impact %")
    ax.set_title(f"{in_token.symbol} -> {out_token.symbol} Price Impact")

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_ticks(cbar.get_ticks())
    cbar.ax.set_yticklabels(pd.to_datetime(cbar.get_ticks(), unit="s").strftime("%Y-%m-%d %H:%M:%S"))
    cbar.set_label("Date")

    if xlim:
        ax.set_xlim(0, xlim)
        ax.set_ylim(0, df[df["in_amount"] < xlim * 10**in_token.decimals]["price_impact"].max()* 100)

    plt.show()


# pylint: disable=too-many-arguments, too-many-locals
def plot_regression_bounded(
    df: pd.DataFrame,
    i: int,
    j: int,
    market: ExternalMarket,
    fn: str | None = None,
    scale: str = "log",
    xlim: float | None = None,
) -> plt.Figure:
    """
    Plot price impact from 1inch quotes against
    predicted price impact from market model with
    lower, central, and upper bound regressions.
    """
    in_token = market.coins[i]
    out_token = market.coins[j]

    x = np.geomspace(df["in_amount"].min(), df["in_amount"].max(), 100)
    y_lower = market.models[i][f"{j}_lower"].predict(x) * 100
    y_central = market.models[i][j].predict(x) * 100
    y_upper = market.models[i][f"{j}_upper"].predict(x) * 100

    f, ax = plt.subplots(figsize=(10, 5))
    scatter = ax.scatter(
        df["in_amount"] / 10**in_token.decimals,
        df["price_impact"] * 100,
        c=df["timestamp"],
        s=20,  # Adjust size as needed
        label="Quotes",
    )
    ax.plot(x / 10**in_token.decimals, y_lower, label="Lower Bound", c="black", lw=2)
    ax.plot(x / 10**in_token.decimals, y_central, label="Prediction", c="indianred", lw=2)
    ax.plot(x / 10**in_token.decimals, y_upper, label="Upper Bound", c="blue", lw=2)
    
    ax.set_xscale(scale)
    ax.legend()
    ax.set_xlabel(f"Amount in ({in_token.symbol})")
    ax.set_ylabel("Price Impact %")
    ax.set_title(f"{in_token.symbol} -> {out_token.symbol} Price Impact")

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.ax.set_yticklabels(pd.to_datetime(cbar.get_ticks(), unit="s").strftime("%Y-%m-%d %H:%M:%S"))
    cbar.set_label("Date")

    if xlim:
        ax.set_xlim(0, xlim)
        ax.set_ylim(0, df[df["in_amount"] < xlim * 10**in_token.decimals]["price_impact"].max()* 100)

    if fn:
        f.savefig(fn, bbox_inches="tight")
        
