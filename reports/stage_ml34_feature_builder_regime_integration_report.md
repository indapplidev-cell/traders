# Stage ML34 Feature Builder Regime Integration Report

Stage ML34 completed.

## Why ML33 degraded

ML33 real run degraded because the feature/regime runner still wrapped the old label-grid flow. The real candidate path kept using `feature_version: fv1`, `regime_training_applied: false`, and sample-style feature diagnostics instead of real dataset-backed diagnostics. BTC/ETH/SOL all stayed rejected because models remained below baseline, collapse signals persisted, walk-forward stayed weak, and `gap_quality` was polluted by trailing incomplete current-day ranges.

## Gap Fix

ML34 fixes the trailing incomplete current-day problem by separating raw `gap_count` from `real_gap_count` and `trailing_incomplete_count`. The updated gap quality summary now exposes `effective_gap_count_for_training`, `gap_severity_for_training`, and `dataset_safe_for_training`, so historical gaps remain visible while trailing incomplete ranges no longer fail the training-safe gate by themselves.

## Features

ML34 adds real additive features to the builder and wires them into `fv2`: `return_6`, `range_pct`, `body_pct`, `upper_wick_pct`, `lower_wick_pct`, `volume_change_pct`, `atr_normalized_move`, `trend_slope_short`, and `trend_slope_medium`. The old `fv1` still works unchanged for backward compatibility, while `fv2` is the preferred feature version for feature/regime-aware runs.

## Real Diagnostics

ML34 adds real feature diagnostics backed by actual dataset rows through `real_feature_diagnostics_service`. Real mode now reports whether real feature diagnostics were actually used, the real row count, and degraded mode explicitly when rows are unavailable. It no longer pretends that a 6-row preview is a real feature diagnostics run.

## Regime Integration

ML34 attaches regime features in the real feature context through `fv2`, including `regime_trend_up`, `regime_trend_down`, `regime_range`, `regime_high_volatility`, `regime_low_volatility`, and `regime_unknown`. Regime features are attached, but regime-specific training is still not applied because the regime-specific label builder is not yet wired into the real training pipeline. The report and preview payloads now expose `regime_features_attached`, `regime_feature_count`, `regime_specific_labeling_available`, `regime_specific_training_applied`, and explicit `missing_requirements`.

## Candidate Selection

The candidate selector now uses training-safe gap fields first: `gap_severity_for_training`, `effective_gap_count_for_training`, and `dataset_safe_for_training`. Trailing incomplete-only gaps can pass the gap gate, while real historical `HIGH` gaps still fail it. Failed gate explanations remain explicit and backward compatible with older reports that only contain raw gap fields.

## Preview Commands

Run:

- `python -m app.cli.commands gap-quality-preview`
- `python -m app.cli.commands real-feature-diagnostics-preview`
- `python -m app.cli.commands feature-regime-integration-preview`
- `python -m app.cli.commands feature-regime-experiment-preview`
- `python -m app.cli.commands feature-engineering-plan-preview`

For a real fv2 smoke:

- `python -m app.cli.commands feature-regime-experiment-run --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --max-configs 1 --feature-version fv2`

## Safety

ML34 keeps the standalone boundaries unchanged:

- no traders-core
- no live
- no orders
- no auto activation

There are no database migrations, no production deploy changes, and no model auto activation.

## Next

ML35 - run real feature/regime-aware BTC/ETH/SOL grid after actual integration.
