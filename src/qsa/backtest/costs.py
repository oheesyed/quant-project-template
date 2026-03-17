from __future__ import annotations


def estimate_commission(shares: float, per_share: float = 0.0) -> float:
    """Estimate total commission cost given the number of shares traded and per-share fee."""
    return abs(shares) * per_share


def estimate_slippage(notional: float, slippage_bps: float = 1.0) -> float:
    """Estimate total slippage cost for a transaction given notional value and slippage in basis points (bps)."""
    return abs(notional) * (slippage_bps / 10_000.0)

