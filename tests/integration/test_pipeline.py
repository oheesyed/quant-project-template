from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

from qsa.backtest.run import run_backtest
from qsa.data import pipeline as data_pipeline
from qsa.live import runner


class _FakeBroker:
    def __init__(self, host: str, port: int, client_id: int, account: str) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account

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
        for idx in range(45):
            close = 100 + idx
            rows.append(
                {
                    "time": start + timedelta(days=idx),
                    "open": close - 0.3,
                    "high": close + 0.7,
                    "low": close - 0.8,
                    "close": close,
                    "volume": 2_000 + idx,
                }
            )
        return pd.DataFrame(rows)

    def get_position(self, symbol: str) -> float:
        del symbol
        return 0.0

    def get_account_data(self) -> dict[str, float | None]:
        return {
            "account_balance": 100_000.0,
            "account_equity": 100_000.0,
            "maintenance_margin": 0.0,
            "free_margin": 100_000.0,
        }

    async def place_market_order(
        self,
        symbol: str,
        quantity: float,
        price_hint: float | None = None,
    ) -> str:
        del symbol, quantity, price_hint
        return "fake-order-id"


def _write_isolated_config(tmp_path: Path, template_path: str) -> str:
    template = Path(template_path)
    cfg = yaml.safe_load(template.read_text())
    data_root = tmp_path / "data"
    cfg["data"]["root"] = str(data_root)
    out_path = tmp_path / template.name
    out_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return str(out_path)


def test_backtest_then_live_dry_run_pipeline(tmp_path: Path) -> None:
    data_pipeline.TWS_Wrapper_Client = _FakeBroker  # type: ignore[assignment]
    dev_config = _write_isolated_config(tmp_path, "configs/dev.yaml")
    paper_config = _write_isolated_config(tmp_path, "configs/paper.yaml")
    backtest = run_backtest(dev_config, initial_cash=100_000.0)
    runner.TWS_Wrapper_Client = _FakeBroker
    live = asyncio.run(runner.run_live(paper_config, dry_run=True, symbol="TEST"))
    assert backtest["status"] == "ok"
    assert live["status"] == "ok"
