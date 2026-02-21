from __future__ import annotations

from typing import Any

from qsa.config.settings import load_settings


def run_live(config_path: str, dry_run: bool) -> dict[str, Any]:
    settings = load_settings(config_path)
    return {
        "status": "ok",
        "env": settings.app_env,
        "run_type": "live",
        "execution_mode": settings.mode,
        "config": config_path,
        "broker": settings.broker,
        "data_dir": str(settings.data_dir),
        "cache_dir": str(settings.cache_dir),
        "dry_run": dry_run,
        "message": "Template scaffold: wire broker adapter, market-data feed, and strategy loop for live or paper execution.",
    }
