# ML38.10.42 — Per-row Production Mask Join Audit

## Why this stage follows ML38.10.41

ML38.10.41 established exact split parity for 6,481 feature rows, but it also showed that the ML38.10.39 recompute used an unresolved denominator: production directional count was 74 while the representative recompute directional count was 6,902. Split parity is OK; production per-row mask values and the production label-row denominator remain incomplete.

This stage adds a diagnostic-only, read-only availability and cascade audit. It does not alter label semantics or production selection behavior.

## Source discovery result

- `setup_quality_score` exists on `ml_labels`/dataset rows and can be joined read-only by symbol, interval, and candle timestamp when production label rows are supplied.
- Regime flags exist per row in `ml_features.features_json` for regime feature versions.
- `entry_path_quality_score` and `stop_pressure_risk_score` are computed in evaluator/training flows, but no persisted per-feature or per-label column was found.
- Recovery-guard behavior is computed in the profit-aware exit evaluator; no persisted per-row decision column was found.
- Production label identity is the composite of symbol, interval, candle timestamp, horizon, and label version. The compact evidence does not expose those rows.
- Bad-dates metadata is a research-only repair probe and is excluded from production tradable parity.

## Diagnostic blocks added

- `per_row_production_mask_join_audit`
- `mask_source_discovery_board`
- `per_row_mask_join_board`
- `mask_cascade_count_board`
- `missing_per_row_sources`
- `next_extractor_requirements`
- `production_mask_join_decision`

Missing concrete values degrade to `MISSING_PER_ROW_SOURCE`; counts remain null after the first unavailable cascade step. The next stage needs read-only timestamp-keyed extractors for the missing score/decision streams.

## Files changed

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Tests added

- `tests/test_ml38_10_42_per_row_production_mask_join_audit.py`
- `tests/test_stage_ml38_10_42_report.py`

## Verification

The allowed `py_compile` command and the two targeted pytest files are the verification scope. Final command results are recorded in the task handoff after execution.

## Scope confirmations

- Runtime training was not run.
- clean/fast/quick/sequence/full were not run; this includes `clean_traders_ml.py`, cleanup-commit-only, quick-quality, fast-debug, `run_clean_fast_quick_sequence.py`, and runtime/full training.
- DB writes were not performed.
- ml_labels was not written.
- Labels, label builders, gates, and model logic were not changed.
- Runtime configs were not added.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifacts were added.
