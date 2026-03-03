from __future__ import annotations
import pandas as pd
import numpy as np

TRADING_DAYS = 252

def cagr(equity: pd.Series) -> float:
    equity = equity.dropna()
    if len(equity) < 2:
        return float("nan")
    start = equity.index[0]
    end = equity.index[-1]
    years = (end - start).days / 365.25
    if years <= 0:
        return float("nan")
    return float(equity.iloc[-1] ** (1 / years) - 1)

def ann_vol(daily_ret: pd.Series) -> float:
    r = daily_ret.dropna()
    if r.empty:
        return float("nan")
    return float(r.std(ddof=1) * np.sqrt(TRADING_DAYS))

def sharpe(daily_ret: pd.Series, rf_annual: float = 0.0) -> float:
    r = daily_ret.dropna()
    if r.empty:
        return float("nan")
    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS) - 1
    ex = r - rf_daily
    denom = ex.std(ddof=1)
    if denom == 0 or np.isnan(denom):
        return float("nan")
    return float(ex.mean() / denom * np.sqrt(TRADING_DAYS))

def max_drawdown(equity: pd.Series) -> float:
    e = equity.dropna()
    if e.empty:
        return float("nan")
    peak = e.cummax()
    dd = e / peak - 1.0
    return float(dd.min())

def avg_turnover(turnover: pd.Series, rebalance_mask: pd.Series | None = None) -> float:
    t = turnover.dropna()
    if t.empty:
        return float("nan")
    if rebalance_mask is not None:
        idx = rebalance_mask.index
        t = t.reindex(idx).fillna(0.0)
    # report average turnover per rebalance event
    nonzero = t[t > 0]
    return float(nonzero.mean()) if len(nonzero) else 0.0