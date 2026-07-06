# ML38.10.50 — Full-dataset Prediction Sidecar Export Implementation

## Scope and lineage

This stage follows ML38.10.49 because that stage established the payload contract, leakage guardrails, and compact-retention design, but ML38.10.49 was design-only. Capture/export implementation was not performed there.

ML38.10.50 implements the pure sidecar schema, JSONL writer, summary and schema writers, fail-closed validator, compact whitelist, and reporter/analyzer metadata wiring. It does not generate predictions from project data.

## Execution and safety

- Only synthetic tests were used.
- The real 6481 stream was not created.
- Quick-quality and training were not run. Runtime, clean, fast-debug, sequence, and full training commands were not run.
- Generation or capture on a real run requires separate user approval.
- There were no database writes.
- ml_labels and ml_predictions were not written.
- Labels, label builders, gates, and model logic were unchanged.
- Actual labels are forbidden as a prediction source; `ml_labels.direction_label` cannot substitute for `predicted_label`.
- Full 6481 cascade/outcome remains prohibited until a real stream exists and validates.
- This stage performs no production-like recompute and establishes no tradable edge.
- Live trading and auto-activation were not changed.

## Added files

- `app/experiments/prediction_sidecar_exporter.py`
- `tests/test_ml38_10_50_prediction_sidecar_exporter.py`
- `tests/test_stage_ml38_10_50_report.py`
- `reports/stage_ml38_10_50_full_dataset_prediction_sidecar_export_implementation_report.md`

## Changed files

- `app/experiments/compact_archive_pruner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`

## Tests run

The permitted `py_compile`, ML38.10.50 targeted pytest files, ML38.10.49 regression test, and `git diff --check` are recorded after execution. Full pytest requires separate approval and was not run in this stage before that approval.
