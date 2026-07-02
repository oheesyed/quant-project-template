from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.placed_contract: Any | None = None
        self.placed_order: Any | None = None

    def placeOrder(self, contract: Any, order: Any) -> Any:
        self.placed_contract = contract
        self.placed_order = order
        order.orderId = 42
        return SimpleNamespace(order=order, contract=contract)

    def trades(self) -> list[Any]:
        if self.placed_order is None or self.placed_contract is None:
            return []
        return [
            SimpleNamespace(
                order=self.placed_order,
                contract=self.placed_contract,
                orderStatus=SimpleNamespace(status="Submitted"),
            )
        ]


def test_place_market_order_preserves_contract_and_account() -> None:
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
            quantity=2.0,
            contract_id=265598,
            exchange="SMART",
        )
    )

    assert order_id == "ibkr:AAPL:2.0000:42"
    assert fake_ib.placed_contract.symbol == "AAPL"
    assert fake_ib.placed_contract.conId == 265598
    assert fake_ib.placed_contract.exchange == "SMART"
    assert fake_ib.placed_order.totalQuantity == 2
    assert fake_ib.placed_order.account == "DU1234567"


def test_place_market_order_rejects_fractional_quantity() -> None:
    client = TWS_Wrapper_Client(host="127.0.0.1", port=7497, client_id=11)
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    with pytest.raises(ValueError, match="whole number of shares"):
        asyncio.run(client.place_market_order(symbol="AAPL", quantity=1.9))
    assert fake_ib.placed_order is None
