from __future__ import annotations


def total_return(initial_equity: float, final_equity: float) -> float:
    if initial_equity == 0:
        return 0.0
    return final_equity / initial_equity - 1.0

