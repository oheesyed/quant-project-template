# Beginner Guide

This guide explains how the template works, which files matter first, what gets
produced when you run it, and where to make your first strategy edits.

## 1) What this app does

At a high level:

1. Load config and settings.
2. Pull IBKR historical bars.
3. Clean the dataset and stamp a run-local dataset fingerprint.
4. Run strategy logic inside the backtest engine.
5. Apply position sizing, risk clamps, and trading costs.
6. Save run outputs for inspection.

You can run two modes:

- `backtest`: simulate historical performance.
- `live`: compute a live target and optionally place an order.

## 2) Start here (first files to read)

Read these in order:

1. `src/qsa/cli.py` - command entrypoint (`backtest` and `live`).
2. `src/qsa/backtest/run.py` - backtest orchestration.
3. `src/qsa/backtest/engine.py` - simulation loop and metrics.
4. `src/qsa/strategies/momentum_example.py` - example strategy logic.
5. `src/qsa/data/pipeline.py` - IBKR ingest, cleaning, run-scoped dataset metadata.
6. `src/qsa/ops/tracking.py` - run artifact persistence.
7. `src/qsa/config/settings.py` - YAML/env config mapping.

## 3) How backtest flow works

`qsa backtest` follows this path:

1. `cli.py` parses args and calls `run_backtest()`.
2. `run.py` loads settings and starts a run directory.
3. `pipeline.py` fetches IBKR bars, cleans them, hashes them, and returns bars.
4. `momentum_example.py` generates target positions from bar history.
5. `engine.py` simulates fills with anti-lookahead timing:
   - signal uses bars through `t-1`
   - trade executes at `t`
6. `tracking.py` writes run artifacts (`params.json`, `metrics.json`, CSVs).

## 4) Why each main module exists

- `config/settings.py`
  - Converts YAML + env vars into one validated `Settings` object.
- `data/pipeline.py`
  - Keeps data handling separate from strategy logic.
  - Enforces deterministic cleaning before simulation.
- `strategies/`
  - Contains signal generation logic only.
- `portfolio/sizing.py` and `portfolio/risk.py`
  - Turns strategy intent into an executable, bounded position.
- `backtest/engine.py`
  - Owns simulation semantics and performance math.
- `ops/tracking.py`
  - Persists outputs so results are inspectable after each run.

## 5) What outputs look like

Each backtest creates a run directory:

- `data/artifacts/runs/<run_id>/config_snapshot.yaml`
- `data/artifacts/runs/<run_id>/params.json`
- `data/artifacts/runs/<run_id>/metrics.json`
- `data/artifacts/runs/<run_id>/bars.csv`
- `data/artifacts/runs/<run_id>/dataset_manifest.json`
- `data/artifacts/runs/<run_id>/trades.csv`
- `data/artifacts/runs/<run_id>/equity_curve.csv`
- `data/artifacts/runs/<run_id>/equity_curve.png` (when run with `--plot`)
- `data/artifacts/runs/<run_id>/drawdown.png` (when run with `--plot`)
- `data/artifacts/runs/<run_id>/equity_with_trades.png` (when run with `--plot`)

Typical `metrics.json` fields:

- `run_id`
- `bars`, `trades`
- `total_return`, `max_drawdown`, `sharpe`
- `final_equity`
- `total_commission`, `total_slippage`

Typical `trades.csv` fields:

- `signal_time`, `trade_time`
- `delta`, `target_position`, `price`, `notional`
- `commission`, `slippage`
- `reason`

Typical `equity_curve.csv` fields:

- `time`
- `equity`
- `position`

## 6) First customization path (recommended)

If you are new, only change these first:

1. `configs/dev.yaml` (lookback, thresholds, risk values, IBKR request fields).
2. `src/qsa/strategies/momentum_example.py` (signal rules).

When updating YAML, make sure `execution` (including account details), `strategy`,
and `risk` sections match your own broker setup and trading objectives.

Leave engine/data/tracking unchanged until you can run:

- one clean backtest
- one dry-run live command
- one artifact review pass (`metrics.json`, `trades.csv`, `equity_curve.csv`)

## 7) What you should edit vs usually leave alone

This template is designed so you can personalize a small set of files without
rewiring the framework.

Edit these to personalize your setup:

- `src/qsa/strategies/momentum_example.py`
  - Change entry/exit logic, feature math, and signal reasons.
- `configs/dev.yaml`
  - Tune strategy/risk values for research runs.
- `configs/paper.yaml`
  - Set paper-trading defaults for dry runs.
- `src/qsa/strategies/`
  - Add your own strategy module (for example, `mean_reversion.py`) when ready.
- `docs/strategy_spec_template.md` (optional but recommended)
  - Copy it and fill out your assumptions before or during iteration.

Usually leave these alone at first:

- `src/qsa/backtest/engine.py` (execution semantics, anti-lookahead, metrics loop)
- `src/qsa/data/pipeline.py` (IBKR ingestion and data cleaning contract)
- `src/qsa/ops/tracking.py` (run artifact shape and persistence)
- `src/qsa/config/settings.py` (validated config model and env mapping)
- `src/qsa/cli.py` (entrypoint wiring)

Only edit those core files when you have a specific reason, such as adding a new
order model, changing data source logic, or extending app capabilities.

## 8) Practical beginner to-do list

1. Run baseline checks:
   - `uv run pytest`
   - `uv run qsa backtest --config configs/dev.yaml`
   - (optional charts) `uv run qsa backtest --config configs/dev.yaml --plot`
2. Review artifacts from that run:
   - `metrics.json`
   - `trades.csv`
   - `equity_curve.csv`
3. Personalize your first strategy:
   - edit `src/qsa/strategies/momentum_example.py`, keep changes small
4. Tune config for that strategy:
   - update thresholds/risk fields in `configs/dev.yaml`
5. (Optional) Fill out a strategy spec:
   - copy `docs/strategy_spec_template.md` into a strategy-specific doc under `docs/`
6. Re-run and compare outputs:
   - check if trade count, drawdown, and total return moved in expected directions
7. When stable, test dry-run live path:
   - `uv run qsa live --config configs/paper.yaml --dry-run --symbol AAPL`

## 9) Common beginner mistakes

- Editing many layers at once (strategy + engine + data + tracking).
- Judging strategy quality from one metric only.
- Forgetting to inspect `trades.csv` when results look surprising.
- Changing config values without rerunning tests.

## 10) Minimal workflow loop

Use this loop while learning:

1. Adjust strategy/config.
2. Run `uv run pytest`.
3. Run `uv run qsa backtest --config configs/dev.yaml`.
4. Inspect run outputs in `data/artifacts/runs/<run_id>/`.
5. Repeat with one small change at a time.
