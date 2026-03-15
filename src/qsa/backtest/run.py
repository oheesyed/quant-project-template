from __future__ import annotations

from typing import Any

from qsa.config.settings import load_settings


def run_backtest(config_path: str, initial_cash: float = 100_000.0) -> dict[str, Any]:
    del initial_cash
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
        "message": "Template scaffold: plug in data loading, strategy, and engine for backtests.",
    }
