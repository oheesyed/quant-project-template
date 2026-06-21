from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.placed_contract: Any | None = None
        self.placed_order: Any | None = None

    def placeOrder(self, contract: Any, order: Any) -> SimpleNamespace:
        self.placed_contract = contract
        self.placed_order = order
        return SimpleNamespace(order=SimpleNamespace(orderId=123))

    def trades(self) -> list[Any]:
        return []


def test_place_market_order_scopes_order_to_account_and_contract() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1",
        port=7497,
        client_id=11,
        account="DU1234567",
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    order_id = asyncio.run(
        client.place_market_order(
            symbol="AAPL",
            quantity=2.9,
            contract_id=265598,
            exchange="SMART",
        )
    )

    assert order_id == "ibkr:AAPL:2.9000:123"
    assert getattr(fake_ib.placed_order, "account") == "DU1234567"
    assert getattr(fake_ib.placed_contract, "conId") == 265598
    assert getattr(fake_ib.placed_contract, "symbol") == "AAPL"
