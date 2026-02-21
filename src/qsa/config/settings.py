from __future__ import annotations

from os import getenv
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    """Strict app settings loaded from YAML + env fallback."""

    model_config = ConfigDict(strict=True, extra="forbid")

    app_env: str
    mode: Literal["backtest", "paper", "live"]
    log_level: str
    data_dir: Path
    cache_dir: Path
    broker: str


def _read_yaml(config_path: Path) -> dict[str, Any]:
    content = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(content, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    return content


def load_settings(config_path: str) -> Settings:
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")

    cfg = _read_yaml(cfg_path)
    app = cfg.get("app", {})
    data = cfg.get("data", {})
    execution = cfg.get("execution", {})

    # Pre-coerce path-like input before strict validation.
    raw = {
        "app_env": app.get("env", getenv("APP_ENV", "dev")),
        "mode": execution.get("mode", getenv("QSA_MODE", "paper")),
        "log_level": app.get("log_level", getenv("QSA_LOG_LEVEL", "INFO")),
        "data_dir": Path(str(data.get("root", getenv("QSA_DATA_DIR", "./data")))),
        "cache_dir": Path(str(data.get("cache_dir", getenv("QSA_CACHE_DIR", "./data/processed/cache")))),
        "broker": execution.get("broker", getenv("QSA_BROKER", "ibkr")),
    }
    return Settings.model_validate(raw)

