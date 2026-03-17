from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from qsa.backtest.plotting import generate_run_plots


def _write_run_inputs(run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"time": "2025-01-01T00:00:00", "equity": 1000.0, "position": 0.0},
            {"time": "2025-01-02T00:00:00", "equity": 1020.0, "position": 1.0},
            {"time": "2025-01-03T00:00:00", "equity": 1010.0, "position": 0.0},
        ]
    ).to_csv(run_dir / "equity_curve.csv", index=False)
    pd.DataFrame(
        [
            {"trade_time": "2025-01-02T00:00:00", "delta": 1.0},
            {"trade_time": "2025-01-03T00:00:00", "delta": -1.0},
        ]
    ).to_csv(run_dir / "trades.csv", index=False)
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": "test-run"}))


def test_generate_run_plots_creates_expected_pngs(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_run_inputs(run_dir)

    plot_files = generate_run_plots(run_dir)

    assert set(plot_files.keys()) == {"equity_curve", "drawdown", "equity_with_trades"}
    for path_str in plot_files.values():
        path = Path(path_str)
        assert path.exists()
        assert path.stat().st_size > 0


def test_generate_run_plots_raises_when_required_file_missing(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"time": "2025-01-01T00:00:00", "equity": 1000.0, "position": 0.0}]).to_csv(
        run_dir / "equity_curve.csv",
        index=False,
    )
    (run_dir / "metrics.json").write_text(json.dumps({"run_id": "missing-trades"}))

    with pytest.raises(FileNotFoundError):
        generate_run_plots(run_dir)
