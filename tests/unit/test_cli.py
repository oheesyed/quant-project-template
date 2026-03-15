from __future__ import annotations

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def test_backtest_returns_mode() -> None:
    result = run_backtest(config_path="configs/dev.yaml")
    assert result["run_type"] == "backtest"
    assert "message" in result


def test_live_dry_run_returns_mode() -> None:
    import asyncio

    result = asyncio.run(run_live(config_path="configs/paper.yaml", dry_run=True))
    assert result["run_type"] == "live"
    assert result["dry_run"] is True

