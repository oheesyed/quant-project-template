from __future__ import annotations

from datetime import datetime, timedelta
from typing import Sequence

from qsa.backtest.engine import run_engine
from qsa.schemas.data import Bar
from qsa.strategies.base import StrategySignal


class _AlwaysLongStrategy:
    def generate_signal(self, bars: Sequence[Bar], current_position: float) -> StrategySignal:
        del bars, current_position
        return StrategySignal(target_position=1.0, action="always_long")


class _EchoUnitStrategy:
    def generate_signal(self, bars: Sequence[Bar], current_position: float) -> StrategySignal:
        del bars
        if current_position == 0.0:
            return StrategySignal(target_position=1.0, action="enter")
        return StrategySignal(target_position=current_position, action="hold")


def _bars() -> list[Bar]:
    start = datetime(2025, 1, 1)
    values = [100.0, 101.0, 102.0, 103.0]
    result: list[Bar] = []
    for idx, close in enumerate(values):
        result.append(
            Bar(
                time=start + timedelta(days=idx),
                open=close - 0.5,
                high=close + 0.5,
                low=close - 1.0,
                close=close,
                volume=1_000.0,
            )
        )
    return result


def test_engine_enforces_t_minus_1_signal_and_t_trade() -> None:
    bars = _bars()
    summary = run_engine(
        bars,
        strategy=_AlwaysLongStrategy(),
        initial_cash=100_000.0,
        target_notional=10_000.0,
        max_abs_position=1_000.0,
        commission_per_share=0.0,
        slippage_bps=0.0,
    )
    assert summary.trades == 1
    first_trade = summary.trades_log[0]
    assert first_trade["signal_time"] == bars[0].time.isoformat()
    assert first_trade["trade_time"] == bars[1].time.isoformat()


def test_engine_passes_unit_position_to_strategy() -> None:
    start = datetime(2025, 1, 1)
    bars = [
        Bar(time=start + timedelta(days=0), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
        Bar(time=start + timedelta(days=1), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
        Bar(time=start + timedelta(days=2), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
    ]
    summary = run_engine(
        bars,
        strategy=_EchoUnitStrategy(),
        initial_cash=100_000.0,
        target_notional=10_000.0,
        max_abs_position=200.0,
        commission_per_share=0.0,
        slippage_bps=0.0,
    )
    assert summary.trades == 1
    assert summary.trades_log[0]["target_position"] == 100.0
    assert "cash" in summary.trades_log[0]
    assert "equity" in summary.trades_log[0]
    assert "gross_leverage" in summary.trades_log[0]


def test_engine_blocks_entry_when_leverage_cap_exceeded() -> None:
    bars = _bars()
    summary = run_engine(
        bars,
        strategy=_AlwaysLongStrategy(),
        initial_cash=1_000.0,
        target_notional=2_000.0,
        max_abs_position=1_000.0,
        allow_leverage=False,
        max_gross_leverage=1.0,
        commission_per_share=0.0,
        slippage_bps=0.0,
    )
    assert summary.trades == 0
    assert summary.final_equity == 1_000.0


def test_engine_liquidates_and_stops_after_nonpositive_equity() -> None:
    start = datetime(2025, 1, 1)
    bars = [
        Bar(time=start + timedelta(days=0), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
        Bar(time=start + timedelta(days=1), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
        Bar(time=start + timedelta(days=2), open=0.0, high=0.0, low=0.0, close=0.0, volume=1_000.0),
        Bar(time=start + timedelta(days=3), open=100.0, high=100.0, low=100.0, close=100.0, volume=1_000.0),
    ]
    summary = run_engine(
        bars,
        strategy=_AlwaysLongStrategy(),
        initial_cash=1_000.0,
        target_notional=1_000.0,
        max_abs_position=1_000.0,
        allow_leverage=True,
        stop_on_nonpositive_equity=True,
        commission_per_share=0.0,
        slippage_bps=0.0,
    )
    assert summary.trades == 2
    assert summary.trades_log[-1]["action"] == "equity_stop_liquidation"
    assert summary.trades_log[-1]["target_position"] == 0.0
    assert summary.final_equity == 0.0
