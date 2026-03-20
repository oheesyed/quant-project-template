from __future__ import annotations

import asyncio
from dataclasses import dataclass

from qsa.config.settings import load_settings
from qsa.data.pipeline import fetch_ibkr_bars_async
from qsa.execution.tws_client import TWS_Wrapper_Client
from qsa.portfolio.risk import clamp_target_position
from qsa.portfolio.sizing import shares_for_unit_signal
from qsa.strategies.momentum_example import MomentumExampleStrategy, MomentumParams


@dataclass(frozen=True)
class LiveRunResult:
    status: str
    env: str
    run_type: str
    execution_mode: str
    config: str
    broker: str
    data_dir: str
    dry_run: bool
    symbol: str
    signal_action: str
    target_position: float
    delta: float
    gross_leverage_estimate: float
    account_equity: float | None
    leverage_blocked: bool
    equity_stop_blocked: bool
    order_id: str


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


async def _resolve_account_equity(
    broker: TWS_Wrapper_Client, *, attempts: int = 3, wait_s: float = 0.2
) -> float | None:
    for attempt in range(attempts):
        account_data = broker.get_account_data()
        account_equity = account_data.get("account_equity")
        if account_equity is not None:
            return float(account_equity)
        if attempt < attempts - 1:
            await asyncio.sleep(wait_s)
    return None


async def run_live(
    config_path: str, dry_run: bool, symbol: str = "AAPL"
) -> LiveRunResult:
    settings = load_settings(config_path)
    bars = await fetch_ibkr_bars_async(settings)
    if not bars:
        raise ValueError("No bars loaded for live runner.")

    strategy = MomentumExampleStrategy(
        MomentumParams(
            lookback=settings.strategy_lookback,
            entry_threshold=settings.strategy_entry_threshold,
            exit_threshold=settings.strategy_exit_threshold,
        )
    )
    broker = TWS_Wrapper_Client(
        host=settings.ib_host,
        port=settings.ib_port,
        client_id=settings.ib_client_id,
        account=settings.ib_account,
    )
    await broker.connect()
    try:
        configured_account = settings.ib_account.strip()
        managed_accounts = broker.get_managed_accounts()
        if not dry_run:
            if not configured_account:
                raise RuntimeError(
                    "execution.account is required for non-dry-run live execution."
                )
            if managed_accounts and configured_account not in managed_accounts:
                raise RuntimeError(
                    f"Configured execution.account '{configured_account}' is not in managed "
                    f"accounts: {managed_accounts}."
                )

        current_position = broker.get_position(symbol)
        current_unit = _position_unit(current_position)
        signal = strategy.generate_signal(bars, current_position=current_unit)
        last_price = bars[-1].close
        account_equity = await _resolve_account_equity(broker)
        if not dry_run and account_equity is None:
            raise RuntimeError(
                f"Unable to resolve account_equity for execution.account "
                f"'{configured_account}'."
            )
        equity_proxy = (
            float(account_equity)
            if account_equity is not None
            else settings.target_notional
        )
        leverage_blocked = False
        equity_stop_blocked = False

        if signal.target_position == current_unit:
            # Hold means no trade in beginner-friendly execution mode.
            target_position = current_position
        else:
            raw_target = shares_for_unit_signal(
                last_price, settings.target_notional, signal.target_position
            )
            candidate_target = clamp_target_position(
                raw_target, settings.max_abs_position
            )
            is_entry_or_flip = (
                signal.target_position != 0.0 and signal.target_position != current_unit
            )
            if (
                settings.stop_on_nonpositive_equity
                and equity_proxy <= 0
                and is_entry_or_flip
            ):
                target_position = current_position
                equity_stop_blocked = True
            elif not settings.allow_leverage and is_entry_or_flip:
                candidate_leverage = _gross_leverage(
                    candidate_target, last_price, equity_proxy
                )
                if candidate_leverage > settings.max_gross_leverage:
                    target_position = current_position
                    leverage_blocked = True
                else:
                    target_position = candidate_target
            else:
                target_position = candidate_target
        delta = target_position - current_position

        order_id = "dry-run"
        if not dry_run and delta != 0:
            order_id = await broker.place_market_order(
                symbol=symbol, quantity=delta, price_hint=last_price
            )

        return LiveRunResult(
            status="ok",
            env=settings.app_env,
            run_type="live",
            execution_mode=settings.mode,
            config=config_path,
            broker=settings.broker,
            data_dir=str(settings.data_dir),
            dry_run=dry_run,
            symbol=symbol,
            signal_action=signal.action,
            target_position=round(target_position, 4),
            delta=round(delta, 4),
            gross_leverage_estimate=round(
                _gross_leverage(target_position, last_price, equity_proxy), 6
            ),
            account_equity=account_equity,
            leverage_blocked=leverage_blocked,
            equity_stop_blocked=equity_stop_blocked,
            order_id=order_id,
        )
    finally:
        await broker.disconnect()
