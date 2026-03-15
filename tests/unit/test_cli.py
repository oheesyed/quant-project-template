from __future__ import annotations

import asyncio

from qsa.backtest.run import run_backtest
from qsa.live import runner


class _FakeBroker:
    def __init__(self, host: str, port: int, client_id: int, account: str) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    def get_position(self, symbol: str) -> float:
        del symbol
        return 0.0

    async def place_market_order(
        self,
        symbol: str,
        quantity: float,
        price_hint: float | None = None,
    ) -> str:
        del symbol, quantity, price_hint
        return "fake-order-id"


def test_backtest_returns_mode_and_metrics() -> None:
    result = run_backtest(config_path="configs/dev.yaml")
    assert result["run_type"] == "backtest"
    assert "total_return" in result


def test_live_dry_run_returns_mode() -> None:
    runner.TWS_Wrapper_Client = _FakeBroker
    result = asyncio.run(runner.run_live(config_path="configs/paper.yaml", dry_run=True, symbol="TEST"))
    assert result["run_type"] == "live"
    assert result["order_id"] == "dry-run"

