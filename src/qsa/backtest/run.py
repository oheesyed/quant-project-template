from __future__ import annotations

from typing import Any

from qsa.backtest.engine import run_engine
from qsa.config.settings import load_settings
from qsa.data.vendors.csv_vendor import CsvDataClient
from qsa.strategies.momentum import MomentumParams, MomentumStrategy


def run_backtest(config_path: str, initial_cash: float = 100_000.0) -> dict[str, Any]:
    settings = load_settings(config_path)
    if settings.data_source != "csv":
        raise ValueError(f"Unsupported data source for example branch: {settings.data_source}")

    bars = CsvDataClient().load_bars(settings.csv_path)
    strategy = MomentumStrategy(
        MomentumParams(
            lookback=settings.strategy_lookback,
            entry_threshold=settings.strategy_entry_threshold,
            exit_threshold=settings.strategy_exit_threshold,
        )
    )
    summary = run_engine(
        bars,
        strategy=strategy,
        initial_cash=initial_cash,
        target_notional=settings.target_notional,
        max_abs_position=settings.max_abs_position,
    )
    return {
        "status": "ok",
        "env": settings.app_env,
        "run_type": "backtest",
        "execution_mode": settings.mode,
        "config": config_path,
        "broker": settings.broker,
        "data_dir": str(settings.data_dir),
        "cache_dir": str(settings.cache_dir),
        "bars": summary.bars,
        "trades": summary.trades,
        "total_return": round(summary.total_return, 6),
        "max_drawdown": round(summary.max_drawdown, 6),
        "sharpe": round(summary.sharpe, 6),
        "final_equity": round(summary.final_equity, 2),
    }
