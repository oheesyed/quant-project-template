from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

"""Example strategy module.

Use this as a starting point for your own strategy:
1) copy this file to `src/strategies/<your_strategy>.py`
2) customize `Params`
3) customize `decide_target_position(...)`
"""


@dataclass(frozen=True)
class Params:
    """Example params for a simple momentum strategy."""

    lookback: int = 15
    entry_th: float = 0.05
    qty: int = 100


# Backwards-compatible alias for older imports.
MomentumParams = Params


def decide_target_position(ohlc: pd.DataFrame, position: int, p: Params) -> int:
    """
    Example momentum decision logic.

    Inputs:
    - ohlc: DataFrame with at least an 'open' column, ordered by time ascending.
    - position: current position (shares), e.g. -qty / 0 / +qty.
    - p: strategy parameters.

    Output:
    - desired *target position* for the next bar: -qty / 0 / +qty.
    """
    if ohlc is None or len(ohlc) < p.lookback + 1:
        return position

    mom = (ohlc.iloc[-1]["open"] - ohlc.iloc[-1 - p.lookback]["open"]) / p.lookback
    mom = round(float(mom), 2)

    # Entry (only when flat)
    if mom > p.entry_th and position == 0:
        return +p.qty
    if mom < -p.entry_th and position == 0:
        return -p.qty

    # Exit when momentum flips sign
    if mom <= 0 and position > 0:
        return 0
    if mom >= 0 and position < 0:
        return 0

    return position
