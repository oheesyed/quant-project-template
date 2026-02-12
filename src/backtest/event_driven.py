from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    initial_cash: float
    final_equity: float
    total_return: float
    max_drawdown: float
    round_trips: int
    fills: int
    win_rate: float | None
    trades: list[dict]
    equity_curve: pd.DataFrame


class StrategyParams(Protocol):
    lookback: int


StrategyDecisionFn = Callable[[pd.DataFrame, int, Any], int]


def max_drawdown(equity: pd.Series) -> float:
    """
    Calculate max drawdown of an equity curve.
    dd_t = (equity_t / peak_t) - 1.0
    max_drawdown = min(dd_t)
    """
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def run_event_driven_bar_backtest(
    ohlc: pd.DataFrame,
    *,
    decide_target_position: StrategyDecisionFn,
    params: StrategyParams,
    initial_cash: float = 100_000.0,
) -> BacktestResult:
    """
    Event-driven bar backtest:
    - decision at bar close t using data up to t
    - fill at next bar open (t+1)
    """
    df = ohlc.copy()
    df = df.sort_values("time").reset_index(drop=True)

    cash = float(initial_cash)
    position = 0  # shares
    pending_delta = 0  # shares to trade at next open

    trades: list[dict] = []
    equity_points: list[dict] = []

    # Round-trip PnL tracking (assumes strategy can go flat between runs)
    open_trade: dict | None = None  # {'dir': 'LONG'|'SHORT', 'qty': int, 'entry_price': float, 'entry_time': datetime}
    closed_pnls: list[float] = []

    for i in range(len(df)):
        bar_time = df.loc[i, "time"]
        bar_open = float(df.loc[i, "open"])
        bar_close = float(df.loc[i, "close"])

        # Apply fill at this bar's open (from decision at previous close).
        if pending_delta != 0:
            fill_qty = int(pending_delta)
            fill_side = "BUY" if fill_qty > 0 else "SELL"
            fill_price = bar_open

            cash -= fill_qty * fill_price
            prev_pos = position
            position += fill_qty

            trades.append(
                {
                    "time": bar_time,
                    "side": fill_side,
                    "qty": abs(fill_qty),
                    "price": fill_price,
                    "pos_before": prev_pos,
                    "pos_after": position,
                }
            )

            # Round-trip accounting
            if prev_pos == 0 and position != 0:
                open_trade = {
                    "dir": "LONG" if position > 0 else "SHORT",
                    "qty": abs(position),
                    "entry_price": fill_price,
                    "entry_time": bar_time,
                }
            elif open_trade and position == 0:
                if open_trade["dir"] == "LONG":
                    pnl = (fill_price - open_trade["entry_price"]) * open_trade["qty"]
                else:
                    pnl = (open_trade["entry_price"] - fill_price) * open_trade["qty"]
                closed_pnls.append(float(pnl))
                open_trade = None

            pending_delta = 0

        # Mark-to-market at close.
        equity = cash + position * bar_close
        equity_points.append(
            {
                "time": bar_time,
                "cash": cash,
                "position": position,
                "close": bar_close,
                "equity": equity,
            }
        )

        # Decide at close, schedule fill for next open.
        if i >= params.lookback and i < len(df) - 1:
            window = df.iloc[: i + 1]
            target = decide_target_position(window, position=position, p=params)
            pending_delta = int(target - position)

    equity_curve = pd.DataFrame(equity_points)
    final_equity = float(equity_curve["equity"].iloc[-1]) if not equity_curve.empty else float(initial_cash)
    total_return = final_equity / float(initial_cash) - 1.0
    max_dd = max_drawdown(equity_curve["equity"]) if not equity_curve.empty else 0.0

    wins = sum(1 for x in closed_pnls if x > 0)
    round_trips = len(closed_pnls)
    win_rate = (wins / round_trips) if round_trips > 0 else None

    return BacktestResult(
        initial_cash=float(initial_cash),
        final_equity=final_equity,
        total_return=float(total_return),
        max_drawdown=float(max_dd),
        round_trips=round_trips,
        fills=len(trades),
        win_rate=win_rate,
        trades=trades,
        equity_curve=equity_curve,
    )

