## IBKR

This repo assumes you run TWS or IB Gateway on the host machine.

- Default host/port: `127.0.0.1:7497`
- If running code inside Docker on macOS, use `host.docker.internal` to reach the host.

Configure via `.env` (copy from `.env.example`).

### Current IBKR path in this repo

- Backtesting with IBKR bars uses:
  - `app/backtest.py --source ibkr`
  - `src/services/tws_client.py` (`TWS_Wrapper_Client`)
- This path requests historical bars from IBKR, then runs the local event-driven
  backtest engine in `src/backtest/event_driven.py`.

### Live trading status

- `app/live.py` is a template script and currently imports broker adapter modules
  from `src/brokers/` that are not part of this simplified codebase.
- To run live trading, either:
  - implement the missing broker adapter modules, or
  - refactor `app/live.py` to use `src/services/tws_client.py` directly.

### Notes

- **Market data permissions**: if you don't have subscriptions, use delayed mode in the broker request call.
- **Ports**: paper trading ports differ; update `IBKR_PORT` accordingly.

