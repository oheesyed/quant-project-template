from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    # src/data/paths.py -> src/data -> src -> repo
    return Path(__file__).resolve().parents[2]


def resolve_data_dir(data_dir: Path) -> Path:
    p = data_dir
    if not p.is_absolute():
        p = (repo_root() / p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_artifact_run_dir(data_dir: Path, run_id: str) -> Path:
    base = resolve_data_dir(data_dir)
    run_dir = base / "artifacts" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

