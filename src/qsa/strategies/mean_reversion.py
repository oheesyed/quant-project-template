from __future__ import annotations

from typing import Sequence

from qsa.data.schemas import Bar
from qsa.strategies.base import StrategySignal


def generate_signal(bars: Sequence[Bar], current_position: float) -> StrategySignal:
    """Template starter strategy; replace with project-specific logic."""
    _ = bars
    return StrategySignal(target_position=current_position, reason="placeholder")

