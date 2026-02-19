from __future__ import annotations

import argparse
import json

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qsa", description="Quant Strategy App CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    backtest = sub.add_parser("backtest", help="Run momentum backtest example.")
    backtest.add_argument("--config", default="configs/dev.yaml")
    backtest.add_argument("--initial-cash", type=float, default=100_000.0)

    live = sub.add_parser("live", help="Run momentum live loop example (single step).")
    live.add_argument("--config", default="configs/paper.yaml")
    live.add_argument("--dry-run", action="store_true")
    live.add_argument("--symbol", default="DEMO")

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "backtest":
        print(run_backtest(config_path=args.config, initial_cash=args.initial_cash))
        return
    print(run_live(config_path=args.config, dry_run=args.dry_run, symbol=args.symbol))

