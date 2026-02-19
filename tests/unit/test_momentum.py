from __future__ import annotations

from datetime import datetime, timedelta

from qsa.data.schemas import Bar
from qsa.strategies.momentum import MomentumParams, MomentumStrategy


def _bars() -> list[Bar]:
    now = datetime(2025, 1, 1)
    return [
        Bar(time=now + timedelta(days=i), open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000)
        for i in range(25)
    ]


def test_momentum_enters_long_on_positive_trend() -> None:
    strategy = MomentumStrategy(MomentumParams(lookback=10, entry_threshold=0.03, exit_threshold=0.0))
    signal = strategy.generate_signal(_bars(), current_position=0.0)
    assert signal.target_position == 1.0
