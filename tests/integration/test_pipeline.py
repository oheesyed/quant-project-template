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


def test_backtest_then_live_dry_run_pipeline() -> None:
    backtest = run_backtest("configs/dev.yaml", initial_cash=100_000.0)
    runner.TWS_Wrapper_Client = _FakeBroker
    live = asyncio.run(runner.run_live("configs/paper.yaml", dry_run=True, symbol="TEST"))
    assert backtest["status"] == "ok"
    assert live["status"] == "ok"
