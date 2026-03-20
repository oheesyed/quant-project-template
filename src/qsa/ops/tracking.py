from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from qsa.config.settings import Settings
from qsa.schemas.artifacts import RunContext


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def start_run(settings: Settings, *, config_path: str, initial_cash: float) -> RunContext:
    run_id = f"{_utc_stamp()}-{uuid.uuid4().hex[:8]}"
    run_dir = settings.data_dir / "artifacts" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    config_src = Path(config_path)
    if config_src.exists():
        (run_dir / "config_snapshot.yaml").write_text(config_src.read_text())

    metadata = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "initial_cash": float(initial_cash),
        "settings": settings.model_dump(mode="json"),
    }
    _write_json(run_dir / "params.json", metadata)
    return RunContext(run_id=run_id, run_dir=run_dir)


def save_dataset_artifacts(
    run_dir: Path,
    *,
    dataset_id: str,
    bars_frame: pd.DataFrame,
    manifest: dict[str, Any],
) -> dict[str, str]:
    run_bars_path = run_dir / "bars.csv"
    run_manifest_path = run_dir / "dataset_manifest.json"
    bars_frame.to_csv(run_bars_path, index=False)

    run_manifest = dict(manifest)
    run_manifest["bars_path"] = str(run_bars_path)
    _write_json(run_manifest_path, run_manifest)

    dataset_meta = {
        "dataset_id": dataset_id,
        "bars_path": str(run_bars_path),
        "manifest_path": str(run_manifest_path),
    }

    params_path = run_dir / "params.json"
    params_payload = _read_json(params_path)
    params_payload["dataset"] = dataset_meta
    _write_json(params_path, params_payload)
    return dataset_meta


def save_metrics(run_dir: Path, metrics: dict[str, Any]) -> None:
    _write_json(run_dir / "metrics.json", metrics)


def save_series_artifacts(
    run_dir: Path,
    *,
    equity_curve: list[dict[str, Any]],
    trades: list[dict[str, Any]],
) -> None:
    pd.DataFrame(equity_curve).to_csv(run_dir / "equity_curve.csv", index=False)
    pd.DataFrame(trades).to_csv(run_dir / "trades.csv", index=False)
