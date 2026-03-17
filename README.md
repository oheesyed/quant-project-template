# quant-strategy-app

## Quickstart

```bash
uv sync --group dev
uv run pytest
uv run qsa backtest --config configs/dev.yaml
uv run qsa backtest --config configs/dev.yaml --plot
uv run qsa live --config configs/paper.yaml --dry-run --symbol AAPL
```

Backtest artifacts are written to `data/artifacts/runs/<run_id>/`, including
`bars.csv`, `dataset_manifest.json`, `metrics.json`, `trades.csv`, and
`equity_curve.csv`.
When `--plot` is enabled, the run directory also includes `equity_curve.png`,
`drawdown.png`, and `equity_with_trades.png`.

