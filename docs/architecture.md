## Architecture

This template is structured around a few boundaries. The point is to keep *strategy logic* clean and reusable,
while isolating all the messy stuff (broker APIs, IO, runtime loops) into small, swappable pieces.

### First-principles split

#### Strategy (what should we do?)
- **Goal**: given information about the world (prices, positions, account state), output a decision.
- **Shape**: pure functions / dataclasses; no network, no threads, no broker SDK imports.
- **Where**: `src/strategies/`

Examples of strategy outputs:
- target position (e.g. +100 shares, 0 shares, -50 shares)
- target orders (if you later choose to model orders explicitly)

#### Execution (runners) (how do we run the strategy?)
- **Goal**: orchestrate a loop:
  - fetch inputs (bars / quotes / positions)
  - call strategy
  - translate decision into actions (simulate fills in backtest, place orders in live)
  - record results (equity curve, trades, artifacts)
- **Where**:
  - `app/` (official runner scripts / entrypoints)
  - `src/backtest/` (generic backtest engine implementation)

Think of a runner as the thing that makes a strategy *actually run* in a particular environment.

#### Adapters (how do we talk to external systems?)
- **IBKR/TWS client adapter**: talks to IBKR/TWS and exposes convenience methods
  for contract creation, market data, historical bars, and orders.
  - **Where**: `src/services/tws_client.py`
- **Data adapter**: reads/writes artifacts and (later) market data sources.
  - **Where**: `src/data/`

### Repo layout (what lives where)
- `src/strategies/`: pure decision logic
- `src/backtest/`: backtest engine + metrics
- `src/services/`: external service adapters (currently IBKR/TWS client)
- `src/data/`: artifact paths + conventions (and later: data ingestion)
- `src/config/`: settings / configuration (env-driven)
- `src/utils/`: small shared utilities
- `app/`: **official runner scripts** (entrypoints). These are meant to be executed.
- `playground/`: scratch experiments (not “official”)

### Repo skeleton (tree)

```text
quant-project-template/
  app/                    # official runners (entrypoints you execute)
  data/                   # output artifacts (usually git-ignored)
  docker/                 # dev container / compose
  docs/                   # documentation
  playground/             # scratch area / experiments
  project_basic_example/  # legacy reference project (source material)
  src/                    # library code (importable modules)
    backtest/             # backtest engine + metrics
    services/             # external service adapters (IBKR/TWS client)
    config/               # config + settings
    data/                 # artifact paths + data conventions
    strategies/           # strategy logic (pure)
    utils/                # small utilities
  tests/                  # fast regression tests (optional but useful)
  .env.example            # example environment config
  pyproject.toml          # deps + tooling (uv groups, ruff, mypy, pytest)
```

Rule of thumb:
- if it’s **reusable**, it goes in `src/`
- if it’s **something you run**, it goes in `app/`
- if it’s **an experiment**, it goes in `playground/`

### Data flow (typical)

1. runner asks a broker/data adapter for bars/quotes/positions
2. runner calls a strategy (pure decision logic)
3. runner either:
   - simulates fills (backtest), or
   - places real orders (live)
4. runner writes artifacts to `data/artifacts/<run_id>/...`

### Current entrypoints

- `app/backtest.py`: momentum backtest runner with two data sources:
  - `--source csv` for local OHLC files
  - `--source ibkr` for IBKR historical bars via `src/services/tws_client.py`
- `app/live.py`: live-loop template; currently references `brokers.*` adapter modules
  that are not present in this simplified codebase.

