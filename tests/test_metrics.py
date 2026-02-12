from __future__ import annotations

import pandas as pd

from backtest.event_driven import max_drawdown


def test_max_drawdown_example() -> None:
    equity = pd.Series([100, 120, 90, 110, 80], dtype=float)
    # peak = [100, 120, 120, 120, 120]
    # dd = [0, 0, -0.25, -0.08333..., -0.33333...]
    assert max_drawdown(equity) == equity.min() / 120 - 1.0

