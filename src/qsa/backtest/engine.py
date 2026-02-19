from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qsa.data.schemas import Bar


@dataclass(frozen=True)
class BacktestSummary:
    bars: int
    note: str


def run_engine(bars: Sequence[Bar]) -> BacktestSummary:
    return BacktestSummary(bars=len(bars), note="Template engine scaffold.")

