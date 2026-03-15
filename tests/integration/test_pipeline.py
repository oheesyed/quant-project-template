from __future__ import annotations

import asyncio

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def test_backtest_then_live_dry_run_pipeline() -> None:
    backtest = run_backtest("configs/dev.yaml")
    live = asyncio.run(run_live("configs/paper.yaml", dry_run=True))
    assert backtest["status"] == "ok"
    assert live["status"] == "ok"
