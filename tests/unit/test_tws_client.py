from __future__ import annotations

import asyncio
from typing import Any

import pytest

from qsa.execution.tws_client import TWS_Wrapper_Client


class _StubClient(TWS_Wrapper_Client):
    def __init__(self) -> None:
        self.sent_quantity: int | None = None

    async def send_market_order(
        self, contract: Any, action: str, quantity: int, tif: str = "DAY"
    ) -> dict[str, int]:
        del contract, action, tif
        self.sent_quantity = quantity
        return {"order_id": 7}

    def get_order_by_id(self, order_id: int) -> dict[str, Any] | None:
        del order_id
        return {"status": "Submitted"}


def test_place_market_order_rejects_fractional_quantity() -> None:
    client = _StubClient()
    with pytest.raises(ValueError, match="whole-share"):
        asyncio.run(client.place_market_order("AAPL", 1.5))
    assert client.sent_quantity is None


def test_place_market_order_sends_whole_quantity() -> None:
    client = _StubClient()
    order_id = asyncio.run(client.place_market_order("AAPL", -3.0))
    assert order_id == "ibkr:AAPL:-3:7"
    assert client.sent_quantity == 3
