from __future__ import annotations

from math import sqrt
from statistics import mean, pstdev

def total_return(initial_equity: float, final_equity: float) -> float:
    if initial_equity == 0:
        return 0.0
    return final_equity / initial_equity - 1.0


def max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = value / peak - 1.0
        if drawdown < worst:
            worst = drawdown
    return worst


def annualized_sharpe(returns: list[float], periods_per_year: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    vol = pstdev(returns)
    if vol == 0:
        return 0.0
    return (mean(returns) / vol) * sqrt(periods_per_year)

