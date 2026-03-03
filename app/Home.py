import sys
from pathlib import Path

# Add project root to path so src/ can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.config import DEFAULT_TICKERS, BENCHMARK
from src.data import load_prices
from src.features import momentum, clean_universe
from src.strategies import top_quantile_equal_weight
from src.backtest import backtest_long_only
from src.metrics import cagr, ann_vol, sharpe, max_drawdown, avg_turnover

st.set_page_config(page_title="Factor Backtest Lab", layout="wide")

st.title("Factor Backtest Lab")
st.caption("Momentum factor research + long-only backtest (for education / portfolio project).")

with st.sidebar:
    st.header("Universe")
    tickers_text = st.text_area("Tickers (comma-separated)", value=",".join(DEFAULT_TICKERS), height=120)
    tickers = [t.strip().upper() for t in tickers_text.split(",") if t.strip()]

    st.header("Dates")
    start = st.date_input("Start", value=pd.to_datetime("2018-01-01")).strftime("%Y-%m-%d")
    end = st.date_input("End", value=pd.to_datetime("2025-12-31")).strftime("%Y-%m-%d")

    st.header("Strategy")
    lookback = st.selectbox("Momentum lookback (trading days)", [63, 126, 252], index=2)
    top_q = st.slider("Hold top quantile", min_value=0.05, max_value=0.50, value=0.20, step=0.05)
    rebalance = st.selectbox("Rebalance", ["M", "W"], index=0)
    cost_bps = st.slider("Transaction cost (bps)", 0.0, 50.0, 10.0, 1.0)

    run = st.button("Run backtest", type="primary")

if not run:
    st.info("Set parameters in the sidebar and click **Run backtest**.")
    st.stop()

all_tickers = sorted(set(tickers + [BENCHMARK]))
data = load_prices(all_tickers, start=start, end=end)
prices = data.adj_close

# Separate benchmark
bench = prices[[BENCHMARK]].dropna()
prices_u = prices.drop(columns=[BENCHMARK], errors="ignore")

# Clean universe to ensure enough history for momentum
prices_u = clean_universe(prices_u, min_history_days=lookback + 10)
prices_u = prices_u.dropna(how="all")

if prices_u.shape[1] < 3:
    st.error("Not enough tickers with sufficient history. Try a later start date or more tickers.")
    st.stop()

# Build factor score + weights
score = momentum(prices_u, lookback_days=lookback)
target_w = top_quantile_equal_weight(score, quantile=top_q)

# Backtest
bt = backtest_long_only(prices=prices_u, target_weights=target_w, rebalance=rebalance, cost_bps=cost_bps)
equity = bt["equity"]
pret = bt["portfolio_return_net"]
turnover = bt["turnover"]
rb_mask = bt["rebalance_dates"]

# Benchmark equity
bench_ret = bench[BENCHMARK].pct_change().fillna(0.0).reindex(equity.index).fillna(0.0)
bench_eq = (1.0 + bench_ret).cumprod()

# Metrics
kpi = {
    "CAGR": cagr(equity),
    "Vol": ann_vol(pret),
    "Sharpe": sharpe(pret),
    "Max Drawdown": max_drawdown(equity),
    "Avg Turnover / Rebalance": avg_turnover(turnover, rb_mask),
}

# Layout
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("CAGR", f"{kpi['CAGR']*100:.2f}%")
c2.metric("Vol", f"{kpi['Vol']*100:.2f}%")
c3.metric("Sharpe", f"{kpi['Sharpe']:.2f}")
c4.metric("Max Drawdown", f"{kpi['Max Drawdown']*100:.2f}%")
c5.metric("Avg Turnover", f"{kpi['Avg Turnover / Rebalance']:.2f}")

st.divider()

# Equity curve (Plotly)
fig_eq = go.Figure()
fig_eq.add_trace(go.Scatter(x=equity.index, y=equity.values, name="Strategy (net)"))
fig_eq.add_trace(go.Scatter(x=bench_eq.index, y=bench_eq.values, name=f"Benchmark ({BENCHMARK})"))
fig_eq.update_layout(
    title="Equity Curve",
    xaxis_title="Date",
    yaxis_title="Growth of $1",
    height=450,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_eq, use_container_width=True)

# Drawdown
def drawdown(series: pd.Series) -> pd.Series:
    peak = series.cummax()
    return series / peak - 1.0

dd = drawdown(equity)
dd_b = drawdown(bench_eq)

fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(x=dd.index, y=dd.values, name="Strategy DD"))
fig_dd.add_trace(go.Scatter(x=dd_b.index, y=dd_b.values, name=f"{BENCHMARK} DD"))
fig_dd.update_layout(
    title="Drawdown",
    xaxis_title="Date",
    yaxis_title="Drawdown",
    height=350,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_dd, use_container_width=True)

st.divider()

# Holdings snapshot
weights = bt["weights"]
last_w = weights.iloc[-1].sort_values(ascending=False)
holdings = last_w[last_w > 0].to_frame("weight")
holdings.index.name = "ticker"

colA, colB = st.columns([1, 1])

with colA:
    st.subheader("Current Holdings (last date)")
    st.dataframe(holdings.style.format({"weight": "{:.2%}"}), use_container_width=True)

with colB:
    st.subheader("Turnover (rebalance days)")
    t_rb = turnover[turnover > 0]
    st.dataframe(t_rb.tail(15).to_frame("turnover").style.format({"turnover": "{:.2f}"}), use_container_width=True)