import numpy as np
import pandas as pd
from pandas import DataFrame
from scipy import stats


def score_with_limits(score_this: float,
                      upper_limit: float,
                      lower_limit: float,
                      direction: bool,
                      mid_limit: float = None) -> float:
    """
    Score the market based on the collateral ratio comparison

    Args:
        score_this (float): Value to be scored
        upper_limit (float): Upper boundary for scoring
        lower_limit (float): Lower boundary for scoring
        mid_limit (float): Middle point representing 0.5 score
        direction (bool): If True, higher values get higher scores
                        If False, lower values get higher scores

    Returns:
        float: Score between 0 and 1
    """

    if mid_limit is None:
        mid_limit = (upper_limit + lower_limit) / 2

    if direction:
        if score_this >= upper_limit:
            return 1.0
        elif score_this <= lower_limit:
            return 0.0
        else:
            # Score between lower and mid
            if score_this <= mid_limit:
                return 0.5 * (score_this - lower_limit) / (mid_limit - lower_limit)
            # Score between mid and upper
            else:
                return 0.5 + 0.5 * (score_this - mid_limit) / (upper_limit - mid_limit)
    else:
        if score_this >= upper_limit:
            return 0.0
        elif score_this <= lower_limit:
            return 1.0
        else:
            # Score between lower and mid
            if score_this <= mid_limit:
                return 1.0 - 0.5 * (score_this - lower_limit) / (mid_limit - lower_limit)
            # Score between mid and upper
            else:
                return 0.5 - 0.5 * (score_this - mid_limit) / (upper_limit - mid_limit)

    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))


def score_bad_debt(bad_debt: float,
                   current_debt: float
                   ) -> float:
    """
    Score bad debt ratio with different interpolation methods
    
    Args:
        bad_debt (float): Amount of bad debt
        current_debt (float): Total current debt
        method (str): Interpolation method ('sigmoid', 'exponential', or 'quadratic')
        
    Returns:
        float: Score between 0 and 1
    """    
    # Constants
    IGNORE_THRESHOLD = 0.001  # 0.1% of current debt
    CRITICAL_THRESHOLD = 0.01  # 1% of current debt
    
    # Convert to ratio for easier calculation
    bad_debt_ratio = bad_debt / current_debt if current_debt > 0 else 0
    
    # If below ignore threshold, return perfect score
    if bad_debt_ratio <= IGNORE_THRESHOLD:
        return 1.0
    
    # If above critical threshold, return zero
    if bad_debt_ratio >= CRITICAL_THRESHOLD:
        return 0.0
    
    # Normalize the ratio to [0,1] range for interpolation
    x = (bad_debt_ratio - IGNORE_THRESHOLD) / (CRITICAL_THRESHOLD - IGNORE_THRESHOLD)
    
    return 1 - x * x * x
    
def score_debt_ceiling(recommended_debt_ceiling: float,
                       current_debt_ceiling: float,
                       current_debt: float) -> float:
    if current_debt_ceiling <= recommended_debt_ceiling:
        return 1.0
    elif current_debt <= recommended_debt_ceiling:
        # score between 0.5 and 1
        return 0.5 + 0.5 * ((recommended_debt_ceiling - current_debt) / recommended_debt_ceiling)
    else:
        return 0.0


def analyze_price_drops(ohlc_df: DataFrame, drop_thresholds: list[float]) -> dict:
    """
    Calculate probability of price drops using Garman-Klass volatility estimator

    Returns:
        dict: Probabilities for each threshold
    """
    # Calculate daily returns using all OHLC data
    daily_returns = (ohlc_df['close'] - ohlc_df['open']) / ohlc_df['open']

    # Calculate true range based returns for better volatility estimation
    true_range_pct = (ohlc_df['high'] - ohlc_df['low']) / ohlc_df['open']

    # Combine both metrics for a more complete picture
    all_returns = pd.concat([daily_returns, true_range_pct])

    # Remove outliers beyond 5 standard deviations
    returns_mean = all_returns.mean()
    returns_std = all_returns.std()
    clean_returns = all_returns[np.abs(all_returns - returns_mean) <= (5 * returns_std)]

    # Fit a t-distribution (better for crypto's fat tails)
    params = stats.t.fit(clean_returns)
    df, loc, scale = params

    probabilities = {}
    for index, threshold in enumerate(drop_thresholds):
        # Calculate probability of a drop greater than the threshold
        prob_parametric = stats.t.cdf(-threshold, df, loc, scale)

        # Calculate historical probability
        prob_historical = len(daily_returns[daily_returns <= -threshold]) / len(daily_returns)

        probabilities[f"drop{index + 1}"] = {
            'parametric_probability': float(prob_parametric),
            'historical_probability': float(prob_historical),
            'threshold_pct': float(threshold * 100)
        }

    return probabilities


def calculate_volatility_ratio(ohlc_df: DataFrame) -> tuple[float, float, float]:
    """
    Calculate volatility ratio using 15-day and 60-day rolling windows

    Returns:
        tuple: (15-day volatility, 60-day volatility, ratio of 15d/60d)
    """
    log_hl = np.log(ohlc_df['high'] / ohlc_df['low'])
    log_co = np.log(ohlc_df['close'] / ohlc_df['open'])

    hl_90d = log_hl.pow(2).rolling(window=90).mean()
    co_90d = log_co.pow(2).rolling(window=90).mean()

    hl_30d = log_hl.pow(2).rolling(window=30).mean()
    co_30d = log_co.pow(2).rolling(window=30).mean()

    # Calculate variances for the last point in each window
    variance_90d = (0.5 * hl_90d - (2 * np.log(2) - 1) * co_90d).iloc[-1]
    variance_30d = (0.5 * hl_30d - (2 * np.log(2) - 1) * co_30d).iloc[-1]

    # Convert to daily volatility
    vol_90d = np.sqrt(max(variance_90d, 0))
    vol_30d = np.sqrt(max(variance_30d, 0))

    # Calculate ratio (handle division by zero)
    ratio = vol_30d / vol_90d if vol_90d != 0 else 1.0

    return vol_30d, vol_90d, ratio


def gk_volatility(df):
    """
    Calculate Garman-Klass volatility with proper error handling
    """
    log_hl = np.log(df['high'] / df['low'])
    log_co = np.log(df['close'] / df['open'])

    # Calculate variance
    variance = (0.5 * log_hl.pow(2) - (2 * np.log(2) - 1) * log_co.pow(2)).mean()

    # Handle negative variance
    if variance <= 0:
        return np.nan

    return np.sqrt(variance)


def calculate_recent_gk_beta(asset_df: pd.DataFrame,
                             btc_df: pd.DataFrame) -> float:
    """
    Calculate a single Garman-Klass beta value using the most recent days of data

    Parameters:
    -----------
    asset_df : pd.DataFrame
        DataFrame with asset OHLC data
    index_df : pd.DataFrame
        DataFrame with index OHLC data
    days : int
        Number of recent days to consider (default: 30)

    Returns:
    --------
    float
        Single GK beta value for the period
    """

    # Calculate returns for correlation
    asset_returns = np.log(asset_df['close'] / asset_df['close'].shift(1))
    btc_returns = np.log(btc_df['close'] / btc_df['close'].shift(1))

    # Calculate correlation
    correlation = asset_returns.corr(btc_returns)

    # Calculate volatilities
    asset_gk_vol = gk_volatility(asset_df)
    btc_gk_vol = gk_volatility(btc_df)

    # Calculate GK beta
    gk_beta = correlation * (asset_gk_vol / btc_gk_vol)

    return gk_beta
