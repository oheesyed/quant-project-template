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
    broker: str
    ib_host: str
    ib_port: int
    ib_client_id: int
    ib_account: str
    data_source: str
    ib_symbol: str
    ib_contract_id: int
    ib_exchange: str
    ib_duration: str
    ib_bar_size: str
    ib_what_to_show: str
    ib_use_rth: int
    strategy_lookback: int = Field(gt=0)
    strategy_entry_threshold: float = Field(ge=0.0)
    strategy_exit_threshold: float
    max_abs_position: float = Field(gt=0.0)
    target_notional: float = Field(gt=0.0)
    allow_leverage: bool
    max_gross_leverage: float = Field(gt=0.0)
    stop_on_nonpositive_equity: bool


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
        "broker": execution.get("broker", getenv("QSA_BROKER", "ibkr")),
        "ib_host": str(execution.get("host", getenv("QSA_IB_HOST", "127.0.0.1"))),
        "ib_port": int(execution.get("port", getenv("QSA_IB_PORT", 7497))),
        "ib_client_id": int(execution.get("client_id", getenv("QSA_IB_CLIENT_ID", 11))),
        "ib_account": str(execution.get("account", getenv("QSA_IB_ACCOUNT", ""))),
        "data_source": str(data.get("source", getenv("QSA_DATA_SOURCE", "ibkr"))),
        "ib_symbol": str(data.get("ib_symbol", getenv("QSA_IB_SYMBOL", "DEMO"))),
        "ib_contract_id": int(data.get("ib_contract_id", getenv("QSA_IB_CONTRACT_ID", 0))),
        "ib_exchange": str(data.get("ib_exchange", getenv("QSA_IB_EXCHANGE", "SMART"))),
        "ib_duration": str(data.get("ib_duration", getenv("QSA_IB_DURATION", "90 D"))),
        "ib_bar_size": str(data.get("ib_bar_size", getenv("QSA_IB_BAR_SIZE", "1 day"))),
        "ib_what_to_show": str(data.get("ib_what_to_show", getenv("QSA_IB_WHAT_TO_SHOW", "TRADES"))),
        "ib_use_rth": int(data.get("ib_use_rth", getenv("QSA_IB_USE_RTH", 1))),
        "strategy_lookback": int(strategy.get("lookback", 15)),
        "strategy_entry_threshold": float(strategy.get("entry_threshold", 0.05)),
        "strategy_exit_threshold": float(strategy.get("exit_threshold", 0.0)),
        "max_abs_position": float(risk.get("max_abs_position", 200)),
        "target_notional": float(risk.get("target_notional", 1_000)),
        "allow_leverage": risk.get("allow_leverage", False),
        "max_gross_leverage": float(risk.get("max_gross_leverage", 1.0)),
        "stop_on_nonpositive_equity": risk.get("stop_on_nonpositive_equity", True),
    }
    return Settings.model_validate(raw)

