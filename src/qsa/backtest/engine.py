from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qsa.backtest.costs import estimate_commission, estimate_slippage
from qsa.backtest.metrics import annualized_sharpe, max_drawdown, total_return
from qsa.data.schemas import Bar
from qsa.portfolio.risk import clamp_target_position
from qsa.portfolio.sizing import shares_for_unit_signal
from qsa.strategies.momentum import MomentumStrategy


@dataclass(frozen=True)
class BacktestSummary:
    bars: int
    trades: int
    total_return: float
    max_drawdown: float
    sharpe: float
    final_equity: float


def run_engine(
    bars: Sequence[Bar],
    *,
    strategy: MomentumStrategy,
    initial_cash: float,
    target_notional: float,
    max_abs_position: float,
    commission_per_share: float = 0.005,
    slippage_bps: float = 1.0,
) -> BacktestSummary:
    if not bars:
        return BacktestSummary(0, 0, 0.0, 0.0, 0.0, initial_cash)

    cash = initial_cash
    position = 0.0
    trades = 0
    equity_curve: list[float] = []
    returns: list[float] = []

    for idx, bar in enumerate(bars):
        signal = strategy.generate_signal(bars[: idx + 1], current_position=position)
        raw_target = shares_for_unit_signal(bar.close, target_notional, signal.target_position)
        target_position = clamp_target_position(raw_target, max_abs_position=max_abs_position)
        delta = target_position - position

        if delta != 0:
            notional = delta * bar.close
            fee = estimate_commission(delta, per_share=commission_per_share)
            slip = estimate_slippage(notional, slippage_bps=slippage_bps)
            cash -= notional + fee + slip
            position = target_position
            trades += 1

        equity = cash + (position * bar.close)
        if equity_curve:
            prev = equity_curve[-1]
            if prev != 0:
                returns.append(equity / prev - 1.0)
        equity_curve.append(equity)

    final_equity = equity_curve[-1]
    return BacktestSummary(
        bars=len(bars),
        trades=trades,
        total_return=total_return(initial_cash, final_equity),
        max_drawdown=max_drawdown(equity_curve),
        sharpe=annualized_sharpe(returns),
        final_equity=final_equity,
    )

