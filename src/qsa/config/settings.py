from __future__ import annotations

from os import getenv
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Strict app settings loaded from YAML + env fallback."""

    model_config = ConfigDict(strict=True, extra="forbid")

    app_env: str
    mode: Literal["backtest", "paper", "live"]
    log_level: str
    data_dir: Path
    cache_dir: Path
    broker: str
    ib_host: str
    ib_port: int
    ib_client_id: int
    ib_account: str
    data_source: str
    csv_path: Path
    strategy_lookback: int = Field(gt=0)
    strategy_entry_threshold: float = Field(ge=0.0)
    strategy_exit_threshold: float
    max_abs_position: float = Field(gt=0.0)
    target_notional: float = Field(gt=0.0)


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
    strategy = cfg.get("strategy", {})
    risk = cfg.get("risk", {})
    raw = {
        "app_env": app.get("env", getenv("APP_ENV", "dev")),
        "mode": execution.get("mode", getenv("QSA_MODE", "paper")),
        "log_level": app.get("log_level", getenv("QSA_LOG_LEVEL", "INFO")),
        "data_dir": Path(str(data.get("root", getenv("QSA_DATA_DIR", "./data")))),
        "cache_dir": Path(str(data.get("cache_dir", getenv("QSA_CACHE_DIR", "./data/processed/cache")))),
        "broker": execution.get("broker", getenv("QSA_BROKER", "ibkr")),
        "ib_host": str(execution.get("host", getenv("QSA_IB_HOST", "127.0.0.1"))),
        "ib_port": int(execution.get("port", getenv("QSA_IB_PORT", 7497))),
        "ib_client_id": int(execution.get("client_id", getenv("QSA_IB_CLIENT_ID", 11))),
        "ib_account": str(execution.get("account", getenv("QSA_IB_ACCOUNT", ""))),
        "data_source": str(data.get("source", "csv")),
        "csv_path": Path(str(data.get("csv_path", "./tests/fixtures/sample_ohlc.csv"))),
        "strategy_lookback": int(strategy.get("lookback", 15)),
        "strategy_entry_threshold": float(strategy.get("entry_threshold", 0.05)),
        "strategy_exit_threshold": float(strategy.get("exit_threshold", 0.0)),
        "max_abs_position": float(risk.get("max_abs_position", 200)),
        "target_notional": float(risk.get("target_notional", 20_000)),
    }
    return Settings.model_validate(raw)

