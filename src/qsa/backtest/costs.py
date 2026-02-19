from __future__ import annotations


def estimate_commission(shares: float, per_share: float = 0.0) -> float:
    return abs(shares) * per_share

