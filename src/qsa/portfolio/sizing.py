from __future__ import annotations


def size_from_notional(price: float, notional: float) -> float:
    if price <= 0:
        return 0.0
    return notional / price


def shares_for_unit_signal(price: float, notional: float, signal: float) -> float:
    return size_from_notional(price=price, notional=notional) * signal

