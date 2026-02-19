from __future__ import annotations

from typing import Protocol


class BrokerAdapter(Protocol):
    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def get_position(self, symbol: str) -> float:
        ...

    def place_market_order(self, symbol: str, quantity: float, price_hint: float | None = None) -> str:
        ...

