# ML38.10.38 — label threshold / horizon sensitivity audit

## Reason and scope

ML38.10.37 found that the current SOLUSDT 15m labels are FLAT about 92%, with directional_count about 74. The majority baseline therefore has strong pressure while the directional sample is below the quick-quality diagnostic minimum. ML38.10.38 adds diagnostic-only evidence about label threshold and horizon sensitivity. It does not rebuild or change runtime labels.

## Diagnostic blocks added

- `label_threshold_horizon_sensitivity_audit`
- `label_recoverability_requirements`
- `next_label_diagnostic_plan`
- `ml38_10_38_label_audit_decision`

The sensitivity board consumes complete precomputed compact rows when available. Otherwise it reports `INSUFFICIENT_COMPACT_FIELDS_FOR_FULL_RECOMPUTE`, lists the required fields and read-only extractor, and provides only future diagnostic grid zones with unknown outcomes.

## Files changed

- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Tests added

- `tests/test_ml38_10_38_label_threshold_horizon_sensitivity_audit.py`
- `tests/test_stage_ml38_10_38_report.py`

## Verification

- `python -m py_compile`: passed for the six authorized Python files.
- `python -m pytest tests/test_ml38_10_38_label_threshold_horizon_sensitivity_audit.py`: passed, 6 tests.
- `python -m pytest tests/test_stage_ml38_10_38_report.py`: passed, 1 test.
- Full pytest: not run; user approval is required after targeted tests.

## Prohibition and safety confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- `clean_traders_ml.py`, cleanup-commit-only, quick-quality, fast-debug, `run_clean_fast_quick_sequence.py`, and runtime/full training were not run.
- labels, label builders, gates, and model logic were not changed.
- no runtime label configuration or lv runtime config was added.
- no gate was softened and no research-only candidate was accepted or made tradable.
- live trading and auto-activation were not changed.
- no runtime JSON, ZIP, or log artifact was created or staged.
