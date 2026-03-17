from __future__ import annotations

from typing import Any

from qsa.backtest.engine import run_engine
from qsa.backtest.plotting import generate_run_plots
from qsa.config.settings import load_settings
from qsa.data.pipeline import build_versioned_dataset
from qsa.ops.logging import configure_logging
from qsa.ops.tracking import (
    save_dataset_artifacts,
    save_metrics,
    save_series_artifacts,
    start_run,
)
from qsa.strategies.momentum_example import MomentumExampleStrategy, MomentumParams


def run_backtest(
    config_path: str,
    initial_cash: float = 100_000.0,
    plot: bool = False,
) -> dict[str, Any]:
    settings = load_settings(config_path)
    configure_logging(settings.log_level)
    run_context = start_run(
        settings,
        config_path=config_path,
        initial_cash=initial_cash,
    )
    dataset = build_versioned_dataset(settings)
    dataset_meta = save_dataset_artifacts(
        run_context.run_dir,
        dataset_id=dataset.dataset_id,
        bars_frame=dataset.bars_frame,
        manifest=dataset.manifest,
    )

    strategy = MomentumExampleStrategy(
        MomentumParams(
            lookback=settings.strategy_lookback,
            entry_threshold=settings.strategy_entry_threshold,
            exit_threshold=settings.strategy_exit_threshold,
        )
    )
    summary = run_engine(
        dataset.bars,
        strategy=strategy,
        initial_cash=initial_cash,
        target_notional=settings.target_notional,
        max_abs_position=settings.max_abs_position,
        allow_leverage=settings.allow_leverage,
        max_gross_leverage=settings.max_gross_leverage,
        stop_on_nonpositive_equity=settings.stop_on_nonpositive_equity,
        commission_per_share=settings.commission_per_share,
        slippage_bps=settings.slippage_bps,
    )
    metrics: dict[str, Any] = {
        "status": "ok",
        "run_id": run_context.run_id,
        "env": settings.app_env,
        "run_type": "backtest",
        "execution_mode": settings.mode,
        "config": config_path,
        "broker": settings.broker,
        "data_dir": str(settings.data_dir),
        "dataset_id": dataset.dataset_id,
        "dataset_bars_path": dataset_meta["bars_path"],
        "dataset_manifest_path": dataset_meta["manifest_path"],
        "bars": summary.bars,
        "trades": summary.trades,
        "total_return": round(summary.total_return, 6),
        "max_drawdown": round(summary.max_drawdown, 6),
        "sharpe": round(summary.sharpe, 6),
        "final_equity": round(summary.final_equity, 2),
        "total_commission": round(summary.total_commission, 6),
        "total_slippage": round(summary.total_slippage, 6),
        "run_dir": str(run_context.run_dir),
    }
    save_series_artifacts(
        run_context.run_dir,
        equity_curve=summary.equity_curve,
        trades=summary.trades_log,
    )
    save_metrics(run_context.run_dir, metrics)
    if plot:
        metrics["plot_files"] = generate_run_plots(run_context.run_dir)
        save_metrics(run_context.run_dir, metrics)
    return metrics
