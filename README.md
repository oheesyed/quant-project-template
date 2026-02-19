# quant-strategy-app template

Strategy-agnostic template for building a quant strategy project with one CLI and separate
backtest/live runners.

`main` stays minimal and generic. A concrete strategy implementation belongs in a separate
branch (for this repo: `momentum-example`).

## Quickstart (template branch)

```bash
uv sync --group dev
uv run pytest
uv run qsa backtest
uv run qsa live
```

Both commands are scaffolds on `main` by design.

## Project layout

```text
quant-strategy-app/
  pyproject.toml
  README.md
  .env.example
  .gitignore
  configs/
  docker/
  docs/
  src/qsa/
  tests/
  playground/
  data/
```

## Design goals

- Keep `main` reusable and dependency-light.
- Keep strategy logic under `src/qsa/strategies`.
- Use one CLI (`qsa`) with `backtest` and `live` subcommands.
- Isolate broker/vendor adapters from strategy logic.

## Branch strategy

- `main`: empty template scaffolding.
- `momentum-example`: fuller runnable momentum implementation built from this template.

