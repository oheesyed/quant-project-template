## quant-project-template

Quant project template skeleton for:

- research + strategy iteration (`/playground`, `/docs`)
- broker adapters (`/src/brokers`)
- backtests (`/src/backtest`)
- runnable scripts / entrypoints (`/app`)
- artifacts (`/data`)

### Quickstart (uv)

```bash
uv sync --group dev --group brokers-ibkr

uv run pytest
uv run python app/backtest.py --source csv --csv data/sample_ohlc.csv
uv run python app/backtest.py --source ibkr --symbol ASML --contract-id 117902840 --exchange NASDAQ
```

### Backtesting your strategy

- Put strategy logic in `src/strategies/<your_strategy>.py`.
- Follow the convention: export `Params` (dataclass) and `decide_target_position(ohlc, position, p)`.
- Copy `app/backtest.py` to `app/<your_strategy>_backtest.py`.
- Change the strategy import in that new app script from `strategies.momentum` to your strategy module.

### Layout

- `src/`: library code (flat, multi-package)
- `app/`: runner scripts (entrypoints)
- `examples/`: reference scripts (optional / legacy)
- `docs/`: documentation
- `docker/`: dev container
- `data/`: outputs (ignored by git; kept via `.gitkeep`)

### Docs

- `docs/getting_started.md`
- `docs/architecture.md`
- `docs/ibkr.md`

