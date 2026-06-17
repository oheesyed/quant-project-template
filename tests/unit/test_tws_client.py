from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from qsa.execution.tws_client import TWS_Wrapper_Client


class _FakeIB:
    def __init__(self) -> None:
        self.order: object | None = None

    def placeOrder(self, contract: object, order: object) -> object:
        del contract
        self.order = order
        return SimpleNamespace(order=SimpleNamespace(orderId=7))


def test_send_market_order_preserves_fractional_quantity() -> None:
    client = TWS_Wrapper_Client(host="127.0.0.1", port=7497, client_id=11)
    fake_ib = _FakeIB()
    client.ib = fake_ib  # type: ignore[assignment]
    contract = TWS_Wrapper_Client.get_contract(
        symbol="AAPL", contract_id=265598, exchange="SMART"
    )

    result = asyncio.run(
        client.send_market_order(contract=contract, action="BUY", quantity=0.75)
    )

    assert result == {"order_id": 7}
    assert getattr(fake_ib.order, "totalQuantity") == pytest.approx(0.75)


def test_place_market_order_uses_configured_contract_and_fractional_quantity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TWS_Wrapper_Client(host="127.0.0.1", port=7497, client_id=11)
    seen: dict[str, object] = {}

    async def _fake_send_market_order(
        contract: object, action: str, quantity: float, tif: str = "DAY"
    ) -> dict[str, int]:
        seen["contract"] = contract
        seen["action"] = action
        seen["quantity"] = quantity
        seen["tif"] = tif
        return {"order_id": 123}

    monkeypatch.setattr(client, "send_market_order", _fake_send_market_order)
    monkeypatch.setattr(client, "get_order_by_id", lambda _: {"status": "Submitted"})

    order_id = asyncio.run(
        client.place_market_order(
            symbol="AAPL",
            quantity=0.75,
            contract_id=265598,
            exchange="SMART",
        )
    )

    assert order_id == "ibkr:AAPL:0.7500:123"
    assert seen["action"] == "BUY"
    assert seen["quantity"] == pytest.approx(0.75)
    assert getattr(seen["contract"], "conId") == 265598
    assert getattr(seen["contract"], "exchange") == "SMART"
