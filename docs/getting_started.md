## Getting started

### Install (uv)

```bash
uv sync --group dev
```

If you hit import issues with editable installs on Python `3.14.0rc*`,
run commands with `--no-editable`:

```bash
uv run --no-editable pytest
```

### IBKR (optional)

Install the IBKR adapter dependencies:

```bash
uv sync --group dev --group brokers-ibkr
```

Create a `.env`:

```bash
cp .env.example .env
```

### Run runners (official entrypoints)

Runners live in `app/` (these are meant to be executed).

```bash
uv run python app/backtest.py --source csv --csv data/sample_ohlc.csv
uv run python app/backtest.py --source ibkr --symbol ASML --contract-id 117902840 --exchange NASDAQ
```

`app/live.py` is currently a template and expects broker adapter modules under
`src/brokers/` that are not present in this simplified repo.

### Docker dev container (optional)

From repo root:

```bash
docker compose -f docker/compose.yml run --rm dev
```

