# quant-strategy-app (`momentum-example` branch)

This branch contains a fuller runnable momentum implementation on top of the template
architecture. The `main` branch remains strategy-agnostic.

## Quickstart

```bash
uv sync --group dev
uv run pytest
uv run qsa backtest --config configs/dev.yaml
uv run qsa live --config configs/paper.yaml --dry-run --symbol DEMO
```

## What is implemented here

- Momentum strategy in `src/qsa/strategies/momentum.py`
- Event-driven style backtest engine in `src/qsa/backtest/engine.py`
- Backtest metrics in `src/qsa/backtest/metrics.py`
- Live runner with paper-style IBKR adapter stub in `src/qsa/live/runner.py`
- Shared risk and sizing logic in `src/qsa/portfolio/`
- CSV vendor path and sample dataset (`tests/fixtures/sample_ohlc.csv`)

## Project layout

```text
quant-strategy-app/
  configs/
  docs/
  src/qsa/
  tests/
  data/
```

