from __future__ import annotations


class IbkrBrokerAdapter:
    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def place_market_order(self, symbol: str, quantity: float) -> str:
        return f"ibkr-placeholder:{symbol}:{quantity}"

