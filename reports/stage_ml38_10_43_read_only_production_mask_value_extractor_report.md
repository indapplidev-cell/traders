# ML38.10.43 — Read-only Production Mask Value Extractor

## Why this stage follows ML38.10.42

ML38.10.42 established that the compact ZIP does not contain the complete 6,481-row stream keyed by timestamp and does not contain a complete production label-row stream. Therefore its per-row joins could not run: joined rows stayed at zero and the production mask cascade remained unavailable.

ML38.10.43 adds a diagnostic-only extractor contract for DB-backed streams and explicitly classifies evaluator-only and aggregate-only sources. It does not change labels or production behavior.

## Diagnostic blocks added

- `read_only_production_mask_value_extractor_audit`
- `timestamp_join_key_audit`
- `mask_value_extraction_board`
- `mask_value_availability_summary`
- `production_label_extraction_summary`
- `extractor_blockers`
- `next_join_plan`
- `ml38_10_43_extractor_decision`

The DB-backed extractors use read-only SQLAlchemy `SELECT` statements. They require explicit label-version and horizon filters for a production label stream. Synthetic rows and mocks can exercise all audit builders without a live database.

## Files changed

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Files added

- `app/diagnostics/production_mask_value_extractor.py`
- `tests/test_ml38_10_43_read_only_production_mask_value_extractor.py`
- `tests/test_stage_ml38_10_43_report.py`
- `reports/stage_ml38_10_43_read_only_production_mask_value_extractor_report.md`

## Verification

The allowed `py_compile` command, including the new diagnostic module, and the two targeted pytest files are the verification scope. Command results are recorded in the final task handoff.

## Scope confirmations

- Runtime training was not run.
- clean/fast/quick/sequence/full were not run; this includes `clean_traders_ml.py`, cleanup-commit-only, quick-quality, fast-debug, `run_clean_fast_quick_sequence.py`, and runtime/full training.
- DB writes were not performed.
- ml_labels was not written.
- Labels, label builders, gates, and model logic were not changed.
- Runtime configs were not added.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifacts were added.
