from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str = getenv("APP_ENV", "dev")
    log_level: str = getenv("QSA_LOG_LEVEL", "INFO")
    data_dir: Path = Path(getenv("QSA_DATA_DIR", "./data"))
    broker: str = getenv("QSA_BROKER", "ibkr")

