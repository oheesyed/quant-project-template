from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")


def generate_run_plots(run_dir: Path) -> dict[str, str]:
    equity_path = run_dir / "equity_curve.csv"
    trades_path = run_dir / "trades.csv"
    metrics_path = run_dir / "metrics.json"
    _require_file(equity_path)
    _require_file(trades_path)
    _require_file(metrics_path)

    metrics = json.loads(metrics_path.read_text())
    run_id = str(metrics.get("run_id", run_dir.name))

    equity_df = pd.read_csv(equity_path)
    if equity_df.empty:
        raise ValueError(f"Equity curve has no rows: {equity_path}")
    equity_df["time"] = pd.to_datetime(equity_df["time"], errors="coerce")
    equity_df = equity_df.dropna(subset=["time", "equity"]).reset_index(drop=True)
    if equity_df.empty:
        raise ValueError(f"Equity curve has no valid time/equity rows: {equity_path}")

    equity_series = equity_df["equity"].astype(float)
    drawdown_series = (equity_series / equity_series.cummax()) - 1.0

    trades_df = pd.read_csv(trades_path)
    if not trades_df.empty:
        trades_df["trade_time"] = pd.to_datetime(trades_df["trade_time"], errors="coerce")
        trades_df = trades_df.dropna(subset=["trade_time", "delta"]).reset_index(drop=True)
        if not trades_df.empty:
            trades_df["delta"] = trades_df["delta"].astype(float)
            trades_df = trades_df.merge(
                equity_df[["time", "equity"]].rename(
                    columns={"time": "trade_time", "equity": "equity_at_trade"}
                ),
                on="trade_time",
                how="left",
            )

    equity_plot_path = run_dir / "equity_curve.png"
    drawdown_plot_path = run_dir / "drawdown.png"
    trade_overlay_path = run_dir / "equity_with_trades.png"

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity_df["time"], equity_series, color="tab:blue", linewidth=1.5)
    ax.set_title(f"Equity Curve ({run_id})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(equity_plot_path, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.plot(equity_df["time"], drawdown_series, color="tab:red", linewidth=1.3)
    ax.fill_between(equity_df["time"], drawdown_series, 0.0, color="tab:red", alpha=0.15)
    ax.set_title(f"Drawdown ({run_id})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Drawdown")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(drawdown_plot_path, dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity_df["time"], equity_series, color="tab:blue", linewidth=1.3, label="Equity")
    if not trades_df.empty:
        buys = trades_df[(trades_df["delta"] > 0) & trades_df["equity_at_trade"].notna()]
        sells = trades_df[(trades_df["delta"] < 0) & trades_df["equity_at_trade"].notna()]
        if not buys.empty:
            ax.scatter(
                buys["trade_time"],
                buys["equity_at_trade"],
                marker="^",
                color="tab:green",
                s=28,
                label="Buy/Increase",
            )
        if not sells.empty:
            ax.scatter(
                sells["trade_time"],
                sells["equity_at_trade"],
                marker="v",
                color="tab:orange",
                s=28,
                label="Sell/Decrease",
            )
    ax.set_title(f"Equity With Trades ({run_id})")
    ax.set_xlabel("Time")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.2)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(trade_overlay_path, dpi=140)
    plt.close(fig)

    return {
        "equity_curve": str(equity_plot_path),
        "drawdown": str(drawdown_plot_path),
        "equity_with_trades": str(trade_overlay_path),
    }
