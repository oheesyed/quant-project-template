from __future__ import annotations


def size_from_notional(price: float, notional: float) -> float:
    if price <= 0:
        return 0.0
    return notional / price

