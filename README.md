# quant-strategy-app

Strategy-agnostic template for quant research, backtesting, and live execution.

## Quickstart

```bash
uv sync --group dev
uv run pytest
uv run qsa backtest --config configs/dev.yaml
uv run qsa live --config configs/paper.yaml --dry-run
```

## Template scope

- Config parsing and strict settings model
- Backtest and live scaffolds in `src/qsa/backtest/run.py` and `src/qsa/live/runner.py`
- Execution client and IBKR integration points in `src/qsa/execution/`
- Strategy interfaces in `src/qsa/strategies/base.py`

## Project layout

```text
quant-strategy-app/
  configs/
  docs/
  src/qsa/
  tests/
  data/
```

