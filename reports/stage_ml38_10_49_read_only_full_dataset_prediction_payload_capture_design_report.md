# ML38.10.49 — Read-only Full-dataset Prediction Payload Capture Design

## Purpose and evidence boundary

This stage is required because ML38.10.48 showed only a test-only outcome on 42 rows (42 pass / 931 removed from the 973-row test denominator). Its profit status was `PROFIT_OUTCOME_MISSING`; no profit conclusion was made. The full 6481 predicted_label stream is missing, while timestamp-keyed predictions are available only for 973 test rows.

ML38.10.49 is design/read-only only. Capture/export implementation was not performed. It defines the future payload contract, candidate capture points, compact archive retention design, leakage protections, and an implementation plan.

## Added diagnostic blocks

- `read_only_full_dataset_prediction_payload_capture_design_audit`
- `current_prediction_payload_inventory`
- `prediction_generation_path_trace`
- `current_artifact_gap_board`
- `required_full_dataset_prediction_stream_contract`
- `capture_point_options_board`
- `compact_profile_whitelist_design`
- `leakage_and_guardrail_contract`
- `implementation_plan`
- `full_dataset_guardrail`
- `ml38_10_49_payload_capture_design_decision`

The required future contract specifies exactly 6481 unique `symbol+interval+candle_open_time` keys, explicit train/validation/test identity, model and calibration provenance, `predicted_label`, probabilities, confidence, and strict separation of optional actual labels from predictions. The recommended future stage is **ML38.10.50 — full-dataset prediction sidecar export implementation**, subject to separate approval.

## Files changed

- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Files added

- `app/diagnostics/full_dataset_prediction_payload_capture_design.py`
- `tests/test_ml38_10_49_read_only_full_dataset_prediction_payload_capture_design.py`
- `tests/test_stage_ml38_10_49_report.py`
- `reports/stage_ml38_10_49_read_only_full_dataset_prediction_payload_capture_design_report.md`

## Verification

The permitted `py_compile` command for the specified diagnostics/reporting files passed. The design module targeted suite passed with 9 tests, and the stage-report targeted suite passed with 1 test. Full pytest was not run and requires separate user approval after these targeted tests.

## Safety confirmation

- Runtime and training were not run.
- Clean/fast/quick/sequence/full commands were not run.
- No database writes were performed.
- ml_labels and ml_predictions were not written.
- ml_labels.direction_label was not substituted as predicted_label.
- Full 6481 cascade/outcome was not built and remains disallowed.
- This is not a production-like recompute.
- This is not a tradable edge, and no production-ready or tradable-edge claim is made.
- Capture/export implementation was not performed.
- Labels, label builders, gates, and model logic were not changed.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifacts were created for commit.
