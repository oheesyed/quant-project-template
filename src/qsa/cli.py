from __future__ import annotations

import argparse

from qsa.backtest.run import run_backtest
from qsa.live.runner import run_live


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qsa", description="Quant Strategy App CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    backtest = sub.add_parser("backtest", help="Run backtest scaffold.")
    backtest.add_argument("--config", default="configs/dev.yaml")

    live = sub.add_parser("live", help="Run live scaffold.")
    live.add_argument("--config", default="configs/paper.yaml")
    live.add_argument("--dry-run", action="store_true")

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "backtest":
        print(run_backtest(config_path=args.config))
        return
    print(run_live(config_path=args.config, dry_run=args.dry_run))

