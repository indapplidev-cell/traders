# Stage ML33 - Feature/Regime-Aware Experiments

Stage ML33 completed.

ML32 diagnostics were useful, but they were not enough alone because they still lived mostly as standalone previews and planning outputs. ML33 adds a real feature/regime-aware experiment cycle that attaches feature diagnostics, regime diagnostics, feature leakage checks, and a regime experiment plan to each experiment run.

The new feature/regime-aware runner can:

- show a preview of available base and regime configs
- execute dry-run mode
- execute sample-mode
- execute a limited real mode by reusing the existing label-grid runner internally
- write experiment logs, event streams, diagnostics, candidate files, and summary reports

Diagnostics attached to experiment output:

- feature diagnostics
- feature group quality
- regime diagnostics
- feature leakage
- regime experiment plan

Real regime training is still degraded in ML33. The runner attaches regime planning and diagnostics, but regime-specific labels are not yet wired directly into the current label builder, so the result explicitly reports `regime_training_applied: false`.

How to run:

```powershell
python -m app.cli.commands feature-regime-experiment-preview

python -m app.cli.commands feature-regime-experiment-run `
  --symbol BTCUSDT `
  --interval 15m `
  --start-date 2025-01-01 `
  --dry-run

python -m app.cli.commands feature-regime-experiment-run `
  --symbol BTCUSDT `
  --interval 15m `
  --start-date 2025-01-01 `
  --sample-mode
```

How to analyze:

```powershell
python -m app.cli.commands feature-regime-results-analyze --latest
```

Why traders-core is still not connected:

- ML33 remains a standalone research step
- feature/regime diagnostics can still report weak signal or leakage risk
- regime-specific training is not yet fully integrated

Safety remains unchanged:

- no traders-core
- no live
- no orders
- no auto activation

Next stage:

- ML34 - if no improvement, implement actual feature builder additions and regime integration
- ML34 - if improvement appears, validate the best candidate on more symbols and timeframes
