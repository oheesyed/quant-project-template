from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from qsa.backtest.costs import estimate_commission, estimate_slippage
from qsa.backtest.metrics import annualized_sharpe, max_drawdown, total_return
from qsa.portfolio.risk import clamp_target_position
from qsa.portfolio.sizing import shares_for_unit_signal
from qsa.schemas.data import Bar
from qsa.strategies.base import Strategy


@dataclass(frozen=True)
class BacktestSummary:
    bars: int
    trades: int
    total_return: float
    max_drawdown: float
    sharpe: float
    final_equity: float
    total_commission: float
    total_slippage: float
    equity_curve: list[dict[str, float | str]]
    trades_log: list[dict[str, float | str]]


def _position_unit(position_shares: float) -> float:
    if position_shares > 0:
        return 1.0
    if position_shares < 0:
        return -1.0
    return 0.0


def _gross_leverage(position_shares: float, price: float, equity: float) -> float:
    if equity <= 0:
        return 0.0 if position_shares == 0 else float("inf")
    return abs(position_shares * price) / equity


def run_engine(
    bars: Sequence[Bar],
    *,
    strategy: Strategy,
    initial_cash: float,
    target_notional: float,
    max_abs_position: float,
    allow_leverage: bool = False,
    max_gross_leverage: float = 1.0,
    stop_on_nonpositive_equity: bool = True,
    commission_per_share: float = 0.005,
    slippage_bps: float = 5.0,
) -> BacktestSummary:
    """Run the backtest engine.

    Args:
        bars: Sequence of Bar objects representing the historical price data.
        strategy: Strategy instance to use for generating signals.
        initial_cash: Initial cash balance.
        target_notional: Target notional value for each trade.
        max_abs_position: Maximum absolute position size in shares.
        allow_leverage: Whether to allow leverage in trades.
        max_gross_leverage: Maximum gross leverage allowed.
        stop_on_nonpositive_equity: Whether to stop trading when equity becomes non-positive.
        commission_per_share: Per-share commission fee.
        slippage_bps: Slippage in basis points (bps).

    Returns:
        BacktestSummary: Summary of the backtest results.
    """
    if not bars:
        return BacktestSummary(
            0,
            0,
            0.0,
            0.0,
            0.0,
            initial_cash,
            0.0,
            0.0,
            [],
            [],
        )

    cash = initial_cash
    position = 0.0
    trades = 0
    equity_curve: list[float] = []
    returns: list[float] = []
    total_commission = 0.0
    total_slippage = 0.0
    equity_points: list[dict[str, float | str]] = []
    trade_rows: list[dict[str, float | str]] = []
    trading_stopped = False

    # Hard anti-lookahead: signal uses history through t-1 and fills at t.
    for idx in range(1, len(bars)):
        bar = bars[idx]
        signal_bar = bars[idx - 1]
        equity_before = cash + (position * bar.close)

        if stop_on_nonpositive_equity and equity_before <= 0 and not trading_stopped:
            if position != 0:
                liquidation_delta = -position
                liquidation_notional = liquidation_delta * bar.close
                liquidation_fee = estimate_commission(liquidation_delta, per_share=commission_per_share)
                liquidation_slip = estimate_slippage(liquidation_notional, slippage_bps=slippage_bps)
                cash -= liquidation_notional + liquidation_fee + liquidation_slip
                position = 0.0
                trades += 1
                total_commission += liquidation_fee
                total_slippage += liquidation_slip
                equity_after_liquidation = cash
                trade_rows.append(
                    {
                        "signal_time": signal_bar.time.isoformat(),
                        "trade_time": bar.time.isoformat(),
                        "action": "equity_stop_liquidation",
                        "delta": round(liquidation_delta, 6),
                        "target_position": 0.0,
                        "price": round(bar.close, 6),
                        "notional": round(liquidation_notional, 6),
                        "trade_notional": round(liquidation_notional, 6),
                        "commission": round(liquidation_fee, 6),
                        "slippage": round(liquidation_slip, 6),
                        "cash": round(cash, 6),
                        "equity": round(equity_after_liquidation, 6),
                        "gross_leverage": 0.0,
                    }
                )
            trading_stopped = True

        current_unit = _position_unit(position)
        if trading_stopped:
            target_position = position
            signal_action = "equity_stop_blocked"
        else:
            signal = strategy.generate_signal(bars[:idx], current_position=current_unit)
            signal_action = signal.action
            if signal.target_position == current_unit:
                # Keep share count unchanged while holding direction.
                target_position = position
            else:
                raw_target = shares_for_unit_signal(bar.close, target_notional, signal.target_position)
                candidate_target = clamp_target_position(raw_target, max_abs_position=max_abs_position)
                is_entry_or_flip = signal.target_position != 0.0 and signal.target_position != current_unit
                if not allow_leverage and is_entry_or_flip:
                    candidate_leverage = _gross_leverage(candidate_target, bar.close, equity_before)
                    if candidate_leverage > max_gross_leverage:
                        target_position = position
                        signal_action = "leverage_cap_blocked"
                    else:
                        target_position = candidate_target
                else:
                    target_position = candidate_target
        delta = target_position - position

        if delta != 0:
            notional = delta * bar.close
            fee = estimate_commission(delta, per_share=commission_per_share)
            slip = estimate_slippage(notional, slippage_bps=slippage_bps)
            cash -= notional + fee + slip
            position = target_position
            trades += 1
            total_commission += fee
            total_slippage += slip
            trade_rows.append(
                {
                    "signal_time": signal_bar.time.isoformat(),
                    "trade_time": bar.time.isoformat(),
                    "action": signal_action,
                    "delta": round(delta, 6),
                    "target_position": round(target_position, 6),
                    "price": round(bar.close, 6),
                    "notional": round(notional, 6),
                    "trade_notional": round(notional, 6),
                    "commission": round(fee, 6),
                    "slippage": round(slip, 6),
                    "cash": round(cash, 6),
                    "equity": round(cash + (position * bar.close), 6),
                    "gross_leverage": round(_gross_leverage(position, bar.close, cash + (position * bar.close)), 6),
                }
            )

        equity = cash + (position * bar.close)
        if equity_curve:
            prev = equity_curve[-1]
            if prev != 0:
                returns.append(equity / prev - 1.0)
        equity_curve.append(equity)
        equity_points.append(
            {
                "time": bar.time.isoformat(),
                "equity": round(equity, 6),
                "position": round(position, 6),
            }
        )

    final_equity = equity_curve[-1] if equity_curve else initial_cash
    return BacktestSummary(
        bars=max(len(bars) - 1, 0),
        trades=trades,
        total_return=total_return(initial_cash, final_equity),
        max_drawdown=max_drawdown(equity_curve),
        sharpe=annualized_sharpe(returns),
        final_equity=final_equity,
        total_commission=total_commission,
        total_slippage=total_slippage,
        equity_curve=equity_points,
        trades_log=trade_rows,
    )

