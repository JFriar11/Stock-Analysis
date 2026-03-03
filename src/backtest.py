from __future__ import annotations
import pandas as pd
import numpy as np

def month_end_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index=index, data=1)
    me = s.resample("M").last().index
    # align to actual trading dates by taking last available <= calendar month end
    out = []
    for d in me:
        eligible = index[index <= d]
        if len(eligible) > 0:
            out.append(eligible[-1])
    return pd.DatetimeIndex(sorted(set(out)))

def backtest_long_only(
    prices: pd.DataFrame,
    target_weights: pd.DataFrame,
    rebalance: str = "M",
    cost_bps: float = 10.0,
) -> dict[str, pd.DataFrame | pd.Series]:
    """
    Long-only, fully invested portfolio with transaction costs on turnover at rebalance dates.
    - prices: Adj close (daily)
    - target_weights: desired weights each day (we'll sample at rebalance dates)
    - cost_bps: cost applied to turnover (e.g. 10 bps = 0.10%)
    """
    prices = prices.sort_index()
    rets = prices.pct_change().fillna(0.0)

    # Determine rebalance schedule
    if rebalance.upper() == "M":
        rb_dates = month_end_dates(prices.index)
    elif rebalance.upper() == "W":
        rb_dates = prices.resample("W-FRI").last().index
        rb_dates = pd.DatetimeIndex([prices.index[prices.index <= d][-1] for d in rb_dates if (prices.index <= d).any()])
        rb_dates = pd.DatetimeIndex(sorted(set(rb_dates)))
    else:
        raise ValueError("rebalance must be 'M' or 'W'")

    # Use target weights on rebalance dates; forward-fill between rebalances
    tw_rb = target_weights.reindex(rb_dates).fillna(0.0)
    tw = tw_rb.reindex(prices.index).ffill().fillna(0.0)

    # Ensure weights sum to 1 on days where there are holdings; otherwise stay in cash
    wsum = tw.sum(axis=1)
    tw = tw.div(wsum.replace(0, np.nan), axis=0).fillna(0.0)

    # Compute turnover at rebalance dates: sum(|w_new - w_old|)
    # Use weights from previous trading day as "old"
    turnover = pd.Series(index=prices.index, data=0.0)
    cost = pd.Series(index=prices.index, data=0.0)

    prev_w = pd.Series(index=prices.columns, data=0.0)
    rb_set = set(rb_dates)

    for dt in prices.index:
        if dt in rb_set:
            new_w = tw.loc[dt]
            to = float((new_w - prev_w).abs().sum())
            turnover.loc[dt] = to
            # cost applied to portfolio value that day; approximate as cost_bps/10000 * turnover
            cost.loc[dt] = (cost_bps / 10000.0) * to
            prev_w = new_w

    # Portfolio daily return: sum_i w_{t-1,i} * r_{t,i} minus cost on rebalance days
    w_lag = tw.shift(1).fillna(0.0)
    port_ret_gross = (w_lag * rets).sum(axis=1)
    port_ret_net = port_ret_gross - cost

    equity = (1.0 + port_ret_net).cumprod()
    out = {
        "weights": tw,
        "turnover": turnover,
        "cost": cost,
        "portfolio_return_gross": port_ret_gross,
        "portfolio_return_net": port_ret_net,
        "equity": equity,
        "rebalance_dates": pd.Series(index=rb_dates, data=True),
    }
    return out