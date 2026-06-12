# Stage ML32 - Feature Engineering and Regime-Specific Labels

Stage ML32 completed.

ML31 still rejected all candidates because label-grid expansion alone did not fix the core issues: collapse pressure remained, walk-forward stayed unstable, and the best candidate still failed profit-aware and gap-quality gates.

ML32 adds regime feature diagnostics so research can inspect label balance and feature quality by regime. This feature engineering layer supports degraded mode when regime data is unavailable and a regime-aware mode when `fv2_regime` feature flags are present.

ML32 adds feature group quality scoring across price_action, volatility, volume, trend, momentum, regime, and unknown groups. This makes it easier to see which feature families are weak before running another experiment cycle.

ML32 also adds regime-specific labels through a planning layer, not a breaking integration into the current label builder. The new regime label planner and regime experiment planner prepare ML33 for trend_up, trend_down, range, high_volatility, low_volatility, and unknown segments.

ML32 adds a feature leakage guard for obvious future-looking names such as `future`, `target`, `label`, and `next`.

Safe additive features were planned rather than added to the real builder. The project already covers part of the requested family through current returns, range, and slope features, so the remaining additive schema changes are deferred to ML33 to avoid unnecessary feature-schema churn in ML32.

Preview commands:

```powershell
python -m app.cli.commands regime-feature-diagnostics-preview
python -m app.cli.commands feature-group-quality-preview
python -m app.cli.commands regime-label-config-preview
python -m app.cli.commands regime-experiment-plan-preview
python -m app.cli.commands feature-leakage-guard-preview
```

Why traders-core is still not connected:

- ML32 is still a standalone research step
- no accepted research candidate was produced in ML31
- live, orders, and auto activation remain disabled by design

Safety remains unchanged:

- no traders-core
- no live
- no orders
- no auto activation

Next stage:

- ML33 - run feature/regime-aware experiments
