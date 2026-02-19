from __future__ import annotations

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def test_backtest_then_live_dry_run_pipeline() -> None:
    backtest = run_backtest("configs/dev.yaml", initial_cash=100_000.0)
    live = run_live("configs/paper.yaml", dry_run=True, symbol="TEST")
    assert backtest["status"] == "ok"
    assert live["status"] == "ok"
