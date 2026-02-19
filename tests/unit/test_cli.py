from __future__ import annotations

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def test_backtest_scaffold_returns_mode() -> None:
    result = run_backtest(config_path="configs/dev.yaml")
    assert result["mode"] == "backtest"


def test_live_scaffold_returns_mode() -> None:
    result = run_live(config_path="configs/paper.yaml", dry_run=True)
    assert result["mode"] == "live"

