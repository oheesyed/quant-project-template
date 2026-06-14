from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.submitted_order: Any | None = None

    def placeOrder(self, contract: Any, order: Any) -> Any:
        del contract
        self.submitted_order = order
        return SimpleNamespace(order=SimpleNamespace(orderId=123))


def test_send_market_order_attaches_configured_account() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        account="DU1234567",
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]
    contract = TWS_Wrapper_Client.get_contract("AAPL", contract_id=0, exchange="SMART")

    result = asyncio.run(client.send_market_order(contract, action="BUY", quantity=1))

    assert result == {"order_id": 123}
    assert fake_ib.submitted_order is not None
    assert fake_ib.submitted_order.account == "DU1234567"
