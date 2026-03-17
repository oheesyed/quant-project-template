from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

from qsa.backtest.run import run_backtest
from qsa.data import pipeline as data_pipeline


class _FakeBroker:
    def __init__(self, host: str, port: int, client_id: int, account: str) -> None:
        del host, port, client_id, account

    @staticmethod
    def get_contract(symbol: str, contract_id: int, exchange: str) -> dict[str, object]:
        return {"symbol": symbol, "contract_id": contract_id, "exchange": exchange}

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def request_historical_data(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        return None

    async def wait_for_historical_data(self, symbol: str, timeframe: str, timeout_s: float = 30.0) -> bool:
        del symbol, timeframe, timeout_s
        return True

    def get_ohlc_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        del symbol, timeframe
        start = datetime(2025, 1, 1)
        rows: list[dict[str, object]] = []
        for idx in range(40):
            close = 95 + idx
            rows.append(
                {
                    "time": start + timedelta(days=idx),
                    "open": close - 0.1,
                    "high": close + 0.8,
                    "low": close - 1.2,
                    "close": close,
                    "volume": 900 + idx,
                }
            )
        return pd.DataFrame(rows)


def _write_isolated_config(tmp_path: Path, template_path: str) -> str:
    template = Path(template_path)
    cfg = yaml.safe_load(template.read_text())
    data_root = tmp_path / "data"
    cfg["data"]["root"] = str(data_root)
    out_path = tmp_path / template.name
    out_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return str(out_path)


def test_backtest_persists_run_artifacts(tmp_path: Path) -> None:
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/dev.yaml")
    result = run_backtest(config_path, initial_cash=100_000.0)
    run_dir = Path(result["run_dir"])

    assert (run_dir / "config_snapshot.yaml").exists()
    assert (run_dir / "params.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "trades.csv").exists()
    assert (run_dir / "equity_curve.csv").exists()
    assert (run_dir / "bars.csv").exists()
    assert (run_dir / "dataset_manifest.json").exists()
    assert not (run_dir / "dataset_reference.json").exists()
    assert not (run_dir / "dataset_manifest_snapshot.json").exists()

    metrics = json.loads((run_dir / "metrics.json").read_text())
    assert metrics["run_id"] == result["run_id"]
    assert metrics["dataset_id"]
    assert Path(metrics["dataset_bars_path"]).exists()
    assert Path(metrics["dataset_manifest_path"]).exists()
    assert Path(metrics["dataset_bars_path"]).parent == run_dir
    assert Path(metrics["dataset_manifest_path"]).parent == run_dir

    params = json.loads((run_dir / "params.json").read_text())
    assert params["dataset"]["dataset_id"] == metrics["dataset_id"]
    assert params["dataset"]["bars_path"] == metrics["dataset_bars_path"]
    assert params["dataset"]["manifest_path"] == metrics["dataset_manifest_path"]
    assert "plot_files" not in metrics
    assert not (run_dir / "equity_curve.png").exists()
    assert not (run_dir / "drawdown.png").exists()
    assert not (run_dir / "equity_with_trades.png").exists()


def test_backtest_with_plot_creates_chart_artifacts(tmp_path: Path) -> None:
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/dev.yaml")
    result = run_backtest(config_path, initial_cash=100_000.0, plot=True)
    run_dir = Path(result["run_dir"])

    assert "plot_files" in result
    plot_files = result["plot_files"]
    assert isinstance(plot_files, dict)
    for key in ("equity_curve", "drawdown", "equity_with_trades"):
        path = Path(plot_files[key])
        assert path.exists()
        assert path.parent == run_dir
        assert path.stat().st_size > 0


def test_backtest_writes_dataset_artifacts_inside_run_dir(tmp_path: Path) -> None:
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    config_path = _write_isolated_config(tmp_path, "configs/dev.yaml")
    result = run_backtest(config_path, initial_cash=100_000.0)

    run_dir = Path(result["run_dir"])
    manifest_payload = json.loads((run_dir / "dataset_manifest.json").read_text())
    assert "source_manifest_path" not in manifest_payload
    assert Path(manifest_payload["bars_path"]).parent == run_dir
