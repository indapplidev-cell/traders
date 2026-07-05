# ML38.10.44 — Read-only Evaluator Payload Reproduction

## Purpose

ML38.10.43 proved that feature identities, setup quality, regime context, and production labels are DB-backed and readable without writes. It also proved that entry-path quality, stop-pressure risk, and the recovery-guard decision existed only in evaluator memory. This stage adds diagnostic-only adapters that reproduce those timestamp-keyed values from explicitly supplied read-only inputs.

## Implementation

- DB-backed values from ML38.10.43: `setup_quality_score`, regime fields in `ml_features.features_json`, `ml_labels.direction_label`, and label-row identity.
- Previously in-memory-only values: `entry_path_quality_score`, `stop_pressure_risk_score`, and `recovery_guard_decision`.
- Added read-only helpers for source auditing, EPQ reproduction, stop-pressure reproduction, recovery-guard reproduction, payload boards, timestamp joins, readiness summaries, and decisions.
- Reused `EntryPathQualityFilter.score_rows` and `ProfitAwareEvaluatorV2._simulate_trade`; evaluator behavior was not changed.
- Added diagnostic blocks: `read_only_evaluator_payload_reproduction_audit`, `evaluator_payload_source_audit`, `payload_reproduction_board`, `timestamp_payload_join_board`, `reproduced_mask_value_summary`, `cascade_readiness_after_reproduction`, and `ml38_10_44_reproduction_decision`.
- Reporter/analyzer compact propagation and compact archive preservation were extended for the new blocks.

## Files changed

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Files added

- `app/diagnostics/evaluator_payload_reproduction.py`
- `tests/test_ml38_10_44_read_only_evaluator_payload_reproduction.py`
- `tests/test_stage_ml38_10_44_report.py`
- `reports/stage_ml38_10_44_read_only_evaluator_payload_reproduction_report.md`

## Verification

- `python -m py_compile` on the approved diagnostic, analyzer, reporter, pruner, and runner files.
- `python -m pytest tests/test_ml38_10_44_read_only_evaluator_payload_reproduction.py`
- `python -m pytest tests/test_stage_ml38_10_44_report.py`
- Full pytest was not run pending explicit user approval after targeted checks.

## Safety confirmation

- Runtime training was not run.
- Clean/fast/quick/sequence/full commands were not run; this includes clean, cleanup-commit-only, quick-quality, fast-debug, sequence, and full/runtime training paths.
- No database writes were performed.
- ml_labels was not written.
- Labels, label builders, gates, and model logic were not changed.
- Evaluator behavior was not changed.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifact was created or committed.
