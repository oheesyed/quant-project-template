from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from qsa.schemas.data import Bar


@dataclass(frozen=True)
class StrategySignal:
    target_position: float
    action: str = ""


class Strategy(Protocol):
    def generate_signal(self, bars: Sequence[Bar], current_position: float) -> StrategySignal:
        ...

