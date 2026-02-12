from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ibkr_host: str = Field(default="127.0.0.1", validation_alias="IBKR_HOST")
    ibkr_port: int = Field(default=7497, validation_alias="IBKR_PORT")
    ibkr_client_id: int = Field(default=0, validation_alias="IBKR_CLIENT_ID")
    ibkr_account: str = Field(default="", validation_alias="IBKR_ACCOUNT")

    data_dir: Path = Field(default=Path("./data"), validation_alias="DATA_DIR")

