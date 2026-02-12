from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from backtest.event_driven import BacktestResult, run_event_driven_bar_backtest
from config.settings import Settings
from data.paths import ensure_artifact_run_dir
from strategies.momentum_example import MomentumParams, decide_target_position
from utils.run_id import new_run_id


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run momentum backtest from CSV or IBKR historical bars.")
    p.add_argument("--source", choices=["csv", "ibkr"], default="csv")

    p.add_argument("--csv", type=Path, default=None, help="Path to OHLC CSV (required for --source csv).")

    p.add_argument("--symbol", default="ASML")
    p.add_argument("--contract-id", type=int, default=117902840)
    p.add_argument("--exchange", default="NASDAQ")
    p.add_argument("--duration", default="1 Y")
    p.add_argument("--bar-size", default="1 day")
    p.add_argument("--use-rth", type=int, default=1, choices=[0, 1])

    p.add_argument("--lookback", type=int, default=15)
    p.add_argument("--entry-th", type=float, default=0.05)
    p.add_argument("--qty", type=int, default=100)
    p.add_argument("--initial-cash", type=float, default=100_000.0)
    return p


def _read_csv_ohlc(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    ohlc = pd.read_csv(csv_path)
    required = {"time", "open", "close"}
    missing = sorted(required - set(ohlc.columns))
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    ohlc = ohlc.copy()
    ohlc["time"] = pd.to_datetime(ohlc["time"])
    return ohlc.sort_values("time").reset_index(drop=True)


def _read_ibkr_ohlc(
    *,
    settings: Settings,
    symbol: str,
    contract_id: int,
    exchange: str,
    duration: str,
    bar_size: str,
    use_rth: int,
) -> pd.DataFrame:
    # Lazy import so CSV mode works without ibapi installed.
    from services.tws_client import TWS_Wrapper_Client

    client = TWS_Wrapper_Client(
        host=settings.ibkr_host,
        port=settings.ibkr_port,
        client_id=settings.ibkr_client_id,
        ib_account=settings.ibkr_account,
    )
    try:
        contract = client.get_contract(symbol=symbol, contract_id=contract_id, exchange=exchange)
        client.request_historical_data(
            contract=contract,
            duration=duration,
            bar_size=bar_size,
            keep_up_to_date=False,
            use_rth=use_rth,
        )

        ready = client.wait_for_historical_data(symbol=symbol, timeframe=bar_size, timeout_s=60.0)
        if not ready:
            raise TimeoutError(f"Timed out waiting for IBKR historical data: {symbol} {bar_size}")

        ohlc = client.get_ohlc_data(symbol=symbol, timeframe=bar_size)
        if ohlc is None or ohlc.empty:
            raise RuntimeError("No OHLC data returned by IBKR.")

        ohlc = ohlc.copy()
        if not pd.api.types.is_datetime64_any_dtype(ohlc["time"]):
            ohlc["time"] = pd.to_datetime(ohlc["time"])
        return ohlc.sort_values("time").reset_index(drop=True)
    finally:
        client.disconnect()


def _write_artifacts(
    *,
    run_dir: Path,
    summary: dict[str, object],
    result: BacktestResult,
    ohlc: pd.DataFrame,
) -> None:
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (run_dir / "trades.json").write_text(json.dumps(result.trades, indent=2, default=str) + "\n")
    result.equity_curve.to_csv(run_dir / "equity_curve.csv", index=False)
    ohlc.to_csv(run_dir / "ohlc.csv", index=False)


def main() -> None:
    args = _build_parser().parse_args()
    settings = Settings()

    run_id = new_run_id(prefix="momentum_backtest")
    run_dir = ensure_artifact_run_dir(settings.data_dir, run_id)

    params = MomentumParams(lookback=args.lookback, entry_th=args.entry_th, qty=args.qty)

    if args.source == "csv":
        if args.csv is None:
            raise ValueError("--csv is required when --source csv")
        ohlc = _read_csv_ohlc(args.csv)
    else:
        ohlc = _read_ibkr_ohlc(
            settings=settings,
            symbol=args.symbol,
            contract_id=args.contract_id,
            exchange=args.exchange,
            duration=args.duration,
            bar_size=args.bar_size,
            use_rth=args.use_rth,
        )

    res = run_event_driven_bar_backtest(
        ohlc,
        decide_target_position=decide_target_position,
        params=params,
        initial_cash=args.initial_cash,
    )

    summary: dict[str, object] = {
        "run_id": run_id,
        "source": args.source,
        "params": params.__dict__,
        "initial_cash": res.initial_cash,
        "final_equity": res.final_equity,
        "total_return": res.total_return,
        "max_drawdown": res.max_drawdown,
        "fills": res.fills,
        "round_trips": res.round_trips,
        "win_rate": res.win_rate,
        "bars": len(ohlc),
    }
    if args.source == "csv":
        summary["csv"] = str(args.csv)
    else:
        summary.update(
            {
                "symbol": args.symbol,
                "contract_id": args.contract_id,
                "exchange": args.exchange,
                "duration": args.duration,
                "bar_size": args.bar_size,
                "use_rth": args.use_rth,
            }
        )

    _write_artifacts(run_dir=run_dir, summary=summary, result=res, ohlc=ohlc)

    print("\n=== Momentum Backtest ===")
    print(f"Artifacts: {run_dir}")
    print(f"Source: {args.source}  Bars: {len(ohlc)}")
    print(f"Lookback: {params.lookback}  EntryTh: {params.entry_th}  Qty: {params.qty}")
    print(f"InitialCash: {res.initial_cash:,.2f}")
    print(f"FinalEquity: {res.final_equity:,.2f}")
    print(f"TotalReturn: {res.total_return*100:.2f}%")
    print(f"MaxDrawdown: {res.max_drawdown*100:.2f}%")
    print(f"Fills: {res.fills}  RoundTrips: {res.round_trips}  WinRate: {res.win_rate}")


if __name__ == "__main__":
    main()
