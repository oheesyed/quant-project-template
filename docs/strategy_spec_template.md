# Strategy Spec Template

Use one copy of this template per strategy. Keep it versioned with code so research,
backtests, and live behavior can be explained and replayed.

## 1) Strategy Identity

- Strategy name:
- Version:
- Owner:
- Last updated:
- Status (`research` | `paper` | `live`):

## 2) Objective + Universe

- Objective (alpha thesis in plain language):
- Tradable universe:
- Session/timezone assumptions:
- Bar timeframe:

## 3) Inputs + Data Contract

- Data source: `ibkr` historical bars via `tws_client`
- Request parameters (`symbol`, `contract_id`, `exchange`, `duration`, `bar_size`, `what_to_show`, `use_rth`):
- Run-scoped dataset fingerprint + manifest path (`data/artifacts/runs/<run_id>/dataset_manifest.json`):
- Data cleaning rules (dedupe, missing values, sorting):

## 4) Signal Rules

- Features used:
- Entry rules:
- Exit rules:
- Regime filters:
- Warmup / minimum history:

## 5) Position Sizing + Risk

- Target notional:
- Max absolute position:
- Gross/net constraints:
- Stop/kill-switch conditions:

## 6) Execution + Timing Assumptions

- Anti-lookahead rule: signals from bars through `t-1`, fills at `t`.
- Fill model assumptions:
- Order type assumptions:
- Latency assumptions:

## 7) Cost + Slippage Assumptions

- Commission model:
- Slippage model:
- Borrow/financing assumptions:
- Known omitted costs:

## 8) Experiment Tracking

- Run ID convention:
- Required artifacts (`config_snapshot.yaml`, `params.json`, `metrics.json`, `trades.csv`, `equity_curve.csv`):

## 9) Validation + Monitoring

- In-sample / out-of-sample plan:
- Stress scenarios:
- Live monitoring metrics:
- Drift checks:

## 10) Failure Modes + Open Risks

- What can break first:
- Detection:
- Mitigation / fallback:
