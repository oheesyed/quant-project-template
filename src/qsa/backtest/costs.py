from __future__ import annotations


def estimate_commission(shares: float, per_share: float = 0.0) -> float:
    return abs(shares) * per_share


def estimate_slippage(notional: float, slippage_bps: float = 1.0) -> float:
    return abs(notional) * (slippage_bps / 10_000.0)

