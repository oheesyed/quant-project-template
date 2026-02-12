## app/ (runners)

This directory contains **official runner scripts** (entrypoints).

- **Goal**: "what you execute" lives here.
- **Non-goal**: library code. Keep reusable code under `src/`.

Typical usage:

```bash
uv run python app/backtest.py --source ibkr --symbol ASML --contract-id 117902840 --exchange NASDAQ
uv run python app/live.py
```

