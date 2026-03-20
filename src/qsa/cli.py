from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qsa", description="Quant Strategy App CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    backtest = sub.add_parser("backtest", help="Run backtest scaffold.")
    backtest.add_argument("--config", default="configs/dev.yaml")
    backtest.add_argument("--initial-cash", type=float, default=100_000.0)
    backtest.add_argument("--plot", action="store_true")

    live = sub.add_parser("live", help="Run live scaffold.")
    live.add_argument("--config", default="configs/paper.yaml")
    live.add_argument("--dry-run", action="store_true")
    live.add_argument("--symbol")

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "backtest":
        result = run_backtest(
            config_path=args.config,
            initial_cash=args.initial_cash,
            plot=args.plot,
        )
        print(json.dumps(result, indent=2))
        return
    result = asyncio.run(
        run_live(config_path=args.config, dry_run=args.dry_run, symbol=args.symbol)
    )
    print(json.dumps(asdict(result), indent=2))
