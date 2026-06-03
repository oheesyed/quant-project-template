from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.orders: list[Any] = []

    def placeOrder(self, contract: object, order: object) -> object:
        del contract
        self.orders.append(order)
        return SimpleNamespace(order=SimpleNamespace(orderId=42))


def test_market_order_sets_configured_account() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        account="DU1234567",
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    result = asyncio.run(
        client.send_market_order(contract=object(), action="BUY", quantity=5)
    )

    assert result == {"order_id": 42}
    assert fake_ib.orders[0].account == "DU1234567"
