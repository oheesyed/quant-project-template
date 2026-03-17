# Docs

Use this directory for architecture notes, onboarding guides, and strategy design templates.

## Recommended reading order

1. `beginner_guide.md` - practical walkthrough of how files connect, what each module does, and what outputs to inspect first.
2. `architecture.md` - system boundaries, runtime flow, and package-level design.
3. `strategy_spec_template.md` - strategy contract template for documenting assumptions and rules.

## Which doc should I read?

- New to the project: start with `beginner_guide.md`.
- Updating internals or adding modules: use `architecture.md`.
- Designing a new strategy: copy `strategy_spec_template.md` and fill it out.

- `beginner_guide.md`: step-by-step project walkthrough for new users.
- `architecture.md`: module boundaries and execution/data flow.
- `strategy_spec_template.md`: strategy contract for reproducible research and clear assumptions.

Backtest runs save self-contained artifacts under `data/artifacts/runs/<run_id>/` only,
including dataset files (`bars.csv`, `dataset_manifest.json`) and result files.

