from __future__ import annotations

import asyncio
from types import SimpleNamespace

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIb:
    def __init__(self) -> None:
        self.placed_order = None

    def placeOrder(self, contract: object, order: object) -> object:
        del contract
        order.orderId = 42
        self.placed_order = order
        return SimpleNamespace(order=order)


def test_market_order_is_bound_to_configured_account() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        account="DU1234567",
    )
    fake_ib = _FakeIb()
    client.ib = fake_ib  # type: ignore[assignment]
    contract = TWS_Wrapper_Client.get_contract("AAPL", contract_id=0, exchange="SMART")

    result = asyncio.run(
        client.send_market_order(contract=contract, action="BUY", quantity=1)
    )

    assert result == {"order_id": 42}
    assert fake_ib.placed_order.account == "DU1234567"
