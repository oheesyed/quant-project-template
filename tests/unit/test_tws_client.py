from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.last_order: Any = None

    def placeOrder(self, contract: object, order: object) -> SimpleNamespace:
        del contract
        self.last_order = order
        return SimpleNamespace(order=SimpleNamespace(orderId=7))


def test_market_order_binds_configured_account() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        account="DU1234567",
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    result = asyncio.run(
        client.send_market_order(contract=object(), action="BUY", quantity=1)
    )

    assert result == {"order_id": 7}
    assert fake_ib.last_order.account == "DU1234567"
