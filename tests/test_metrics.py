import pandas as pd
import numpy as np
from src.metrics import max_drawdown

def test_max_drawdown_simple():
    idx = pd.date_range("2020-01-01", periods=5, freq="D")
    equity = pd.Series([1.0, 1.2, 0.9, 1.1, 1.3], index=idx)
    dd = max_drawdown(equity)
    # peak 1.2 -> trough 0.9 is -25%
    assert np.isclose(dd, -0.25)