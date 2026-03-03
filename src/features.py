from __future__ import annotations
import pandas as pd
import numpy as np

def pct_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change()

def momentum(prices: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    """
    Simple momentum: (P_t / P_{t-L}) - 1
    """
    return prices / prices.shift(lookback_days) - 1.0

def clean_universe(prices: pd.DataFrame, min_history_days: int) -> pd.DataFrame:
    """
    Drop tickers without enough history to compute features reliably.
    """
    ok = (prices.notna().sum(axis=0) >= min_history_days)
    return prices.loc[:, ok]