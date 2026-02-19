from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qsa.data.schemas import Bar
from qsa.strategies.base import StrategySignal


@dataclass(frozen=True)
class MomentumParams:
    lookback: int = 15
    entry_threshold: float = 0.05
    exit_threshold: float = 0.0


class MomentumStrategy:
    def __init__(self, params: MomentumParams) -> None:
        self.params = params

    def generate_signal(self, bars: Sequence[Bar], current_position: float) -> StrategySignal:
        if len(bars) < self.params.lookback + 1:
            return StrategySignal(target_position=current_position, reason="insufficient_history")

        latest = bars[-1].close
        anchor = bars[-1 - self.params.lookback].close
        if anchor <= 0:
            return StrategySignal(target_position=current_position, reason="invalid_anchor")

        momentum = latest / anchor - 1.0
        if current_position == 0:
            if momentum > self.params.entry_threshold:
                return StrategySignal(target_position=1.0, reason="long_entry")
            if momentum < -self.params.entry_threshold:
                return StrategySignal(target_position=-1.0, reason="short_entry")
            return StrategySignal(target_position=0.0, reason="flat")

        if current_position > 0 and momentum <= self.params.exit_threshold:
            return StrategySignal(target_position=0.0, reason="long_exit")
        if current_position < 0 and momentum >= -self.params.exit_threshold:
            return StrategySignal(target_position=0.0, reason="short_exit")
        return StrategySignal(target_position=current_position, reason="hold")

