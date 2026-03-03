from __future__ import annotations
import os
from dataclasses import dataclass
import pandas as pd
import yfinance as yf

@dataclass(frozen=True)
class PriceData:
    adj_close: pd.DataFrame  # columns=tickers, index=date (DatetimeIndex)

def _cache_path(cache_dir: str, key: str) -> str:
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{key}.parquet")

def load_prices(
    tickers: list[str],
    start: str,
    end: str,
    cache_dir: str = ".cache",
) -> PriceData:
    """
    Returns Adj Close prices (daily) for tickers. Uses a local parquet cache.
    """
    key = f"adjclose_{start}_{end}_" + "_".join(tickers)
    path = _cache_path(cache_dir, key)

    if os.path.exists(path):
        adj = pd.read_parquet(path)
        adj.index = pd.to_datetime(adj.index)
        return PriceData(adj_close=adj)

    df = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        group_by="column",
        threads=True,
    )

    # yfinance returns multi-index columns when multiple tickers
    if isinstance(df.columns, pd.MultiIndex):
        adj = df["Adj Close"].copy()
    else:
        # single ticker case
        adj = df[["Adj Close"]].rename(columns={"Adj Close": tickers[0]})

    adj = adj.dropna(how="all").sort_index()
    adj.to_parquet(path)
    return PriceData(adj_close=adj)