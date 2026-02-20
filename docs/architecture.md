## Architecture

`main` intentionally contains a neutral scaffold. Strategy-specific logic belongs in
branch examples (such as `momentum-example`), not in this template baseline.

## Boundary model

- Runners: `backtest` and `live` orchestrate execution loops.
- Shared core modules: strategy, portfolio risk/sizing, data vendors/cache.
- Execution adapters: broker-specific live order gateways.
- Metrics: backtest evaluation metrics plus live operational metrics.

## Package map

```text
src/qsa/
  cli.py
  config/settings.py
  data/{schemas.py,cache.py,vendors/...}
  strategies/base.py
  portfolio/{risk.py,sizing.py}
  backtest/{engine.py,costs.py,metrics.py,run.py}
  execution/{broker_base.py,ibkr.py}
  live/runner.py
  ops/logging.py
```

## Data flow

1. CLI loads settings and dispatches to `backtest` or `live`.
2. Runner fetches market inputs through data vendor/cache adapters.
3. Strategy produces intent and portfolio layer computes final exposure/size.
4. Backtest runner simulates outcomes and emits evaluation metrics.
5. Live runner sends orders through broker adapter and tracks runtime telemetry.

