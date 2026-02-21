from __future__ import annotations

from typing import Any

from qsa.config.settings import load_settings


def run_backtest(config_path: str) -> dict[str, Any]:
    settings = load_settings(config_path)
    return {
        "status": "ok",
        "env": settings.app_env,
        "run_type": "backtest",
        "execution_mode": settings.mode,
        "config": config_path,
        "broker": settings.broker,
        "data_dir": str(settings.data_dir),
        "cache_dir": str(settings.cache_dir),
        "bars": None,
        "trades": None,
        "total_return": None,
        "max_drawdown": None,
        "sharpe": None,
        "final_equity": None,
        "message": "Template scaffold: wire data, strategy, and backtest engine; replace placeholder metrics with computed values.",
    }
