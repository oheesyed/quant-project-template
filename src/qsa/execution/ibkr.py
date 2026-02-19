from __future__ import annotations


class IbkrBrokerAdapter:
    def __init__(self) -> None:
        self._connected = False
        self._positions: dict[str, float] = {}

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def get_position(self, symbol: str) -> float:
        return float(self._positions.get(symbol, 0.0))

    def place_market_order(self, symbol: str, quantity: float, price_hint: float | None = None) -> str:
        if not self._connected:
            raise RuntimeError("Broker is not connected.")
        self._positions[symbol] = self.get_position(symbol) + quantity
        px = "na" if price_hint is None else f"{price_hint:.2f}"
        return f"ibkr-paper:{symbol}:{quantity:.4f}:{px}"

