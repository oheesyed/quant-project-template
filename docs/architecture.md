## Architecture

This document describes how the app runs end-to-end across config, data ingestion,
signal generation, execution simulation, and artifact persistence.

## System overview

- CLI entrypoint dispatches to `backtest` and `live` run paths.
- Data comes from IBKR historical requests and is normalized in a pipeline.
- Strategies output target intent; portfolio modules turn intent into bounded position size.
- Backtest applies anti-lookahead timing and cost/slippage assumptions.
- Each run persists core artifacts for later inspection.

## Boundary model

- Runners: `backtest` and `live` orchestrate execution loops.
- Shared core modules: strategy, portfolio risk/sizing, IBKR data pipeline/cache.
- Execution integration: IBKR TWS client (`execution/tws_client.py`).
- Metrics: backtest metrics plus live run output fields.

## Package map

```text
src/qsa/
  cli.py
  config/settings.py
  data/{schemas.py,cache.py,pipeline.py}
  strategies/{base.py,momentum_example.py}
  portfolio/{risk.py,sizing.py}
  backtest/{engine.py,costs.py,metrics.py,run.py}
  execution/tws_client.py
  live/runner.py
  ops/{logging.py,tracking.py}
```

## Project layout

```text
quant-strategy-app/
  configs/
  docs/
  src/qsa/
  tests/
  data/
```

## Runtime flow

1. CLI loads settings (including strategy/risk/cost assumptions) and dispatches to `backtest` or `live`.
2. Backtest path builds a run-scoped dataset snapshot from IBKR bars via `data/pipeline.py`.
3. Strategy produces target intent; sizing/risk clamps final position.
4. Backtest engine enforces anti-lookahead timing (signals at t-1, fills at t), applies costs/slippage, and computes summary metrics.
5. Tracking persists run artifacts under `data/artifacts/runs/<run_id>/`.
6. Live path fetches recent IBKR bars, computes target delta, and (unless `--dry-run`) sends a market order through `TWS_Wrapper_Client`.

## Backtest artifacts

Each backtest writes a run directory under `data/artifacts/runs/<run_id>/` with:

- `config_snapshot.yaml`
- `params.json`
- `metrics.json`
- `trades.csv`
- `equity_curve.csv`

