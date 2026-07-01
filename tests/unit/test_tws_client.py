from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self._trades: list[object] = []

    def placeOrder(self, contract: object, order: object) -> object:
        order.orderId = 123
        trade = SimpleNamespace(
            contract=contract,
            order=order,
            orderStatus=SimpleNamespace(status="Submitted"),
        )
        self._trades.append(trade)
        return trade

    def trades(self) -> list[object]:
        return self._trades


def test_place_market_order_uses_configured_contract_and_account() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1", port=7497, client_id=11, account="DU1234567"
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    order_id = asyncio.run(
        client.place_market_order(
            symbol="AAPL",
            quantity=3.0,
            contract_id=265598,
            exchange="SMART",
        )
    )

    assert order_id == "ibkr:AAPL:3.0000:123"
    trade = fake_ib.trades()[0]
    assert getattr(trade.contract, "symbol") == "AAPL"
    assert getattr(trade.contract, "conId") == 265598
    assert getattr(trade.order, "account") == "DU1234567"
    assert getattr(trade.order, "totalQuantity") == 3


def test_place_market_order_rejects_fractional_quantity() -> None:
    client = TWS_Wrapper_Client(
        host="127.0.0.1", port=7497, client_id=11, account="DU1234567"
    )
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]

    with pytest.raises(ValueError, match="whole number of shares"):
        asyncio.run(client.place_market_order(symbol="AAPL", quantity=3.5))

    assert fake_ib.trades() == []
