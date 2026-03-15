from __future__ import annotations

from typing import Any

from qsa.config.settings import load_settings
from qsa.data.vendors.csv_vendor import CsvDataClient
from qsa.execution.tws_client import TWS_Wrapper_Client
from qsa.portfolio.risk import clamp_target_position
from qsa.portfolio.sizing import shares_for_unit_signal
from qsa.strategies.momentum import MomentumParams, MomentumStrategy


async def run_live(config_path: str, dry_run: bool, symbol: str = "DEMO") -> dict[str, Any]:
    settings = load_settings(config_path)
    bars = CsvDataClient().load_bars(settings.csv_path)
    if not bars:
        raise ValueError("No bars loaded for live runner.")

    strategy = MomentumStrategy(
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
        current_position = broker.get_position(symbol)
        signal = strategy.generate_signal(bars, current_position=current_position)
        last_price = bars[-1].close
        raw_target = shares_for_unit_signal(last_price, settings.target_notional, signal.target_position)
        target_position = clamp_target_position(raw_target, settings.max_abs_position)
        delta = target_position - current_position

        order_id = "dry-run"
        if not dry_run and delta != 0:
            order_id = await broker.place_market_order(symbol=symbol, quantity=delta, price_hint=last_price)

        return {
            "status": "ok",
            "env": settings.app_env,
            "run_type": "live",
            "execution_mode": settings.mode,
            "config": config_path,
            "broker": settings.broker,
            "data_dir": str(settings.data_dir),
            "cache_dir": str(settings.cache_dir),
            "dry_run": dry_run,
            "symbol": symbol,
            "signal_reason": signal.reason,
            "target_position": round(target_position, 4),
            "delta": round(delta, 4),
            "order_id": order_id,
        }
    finally:
        await broker.disconnect()
