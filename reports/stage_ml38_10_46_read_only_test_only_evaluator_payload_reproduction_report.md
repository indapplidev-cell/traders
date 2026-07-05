# ML38.10.46 — Read-only Test-only Evaluator Payload Reproduction Audit

## Purpose

ML38.10.45 located timestamped evaluator predictions only for the test denominator. The usable payload has 973 rows, while the full dataset has 6,481 feature rows and no matching full-dataset `predicted_label` stream. This stage therefore reproduces evaluator values only for the test-only 973 rows. It does not claim or construct a full 6,481-row mask cascade.

The selected read-only source is `reports/probability_diagnostics_ml_candle_mlp_v1_solusdt_15m_h12_lv31_h12_dates_exit45_long_2026_07_04_135506_445150_e354b20040.json`, specifically `calibrated_decision_diagnostics.calibrated_rows`. It has 973 unique `candle_open_time` rows and prioritizes `entry_path_original_predicted_label` over `predicted_label` for evaluator reproduction.

## Result

- Payload source: `TEST_TIMESTAMPED_PREDICTIONS_SELECTED` (973 rows).
- Timestamp join: `TEST_JOIN_READY` (973 feature matches, 973 label matches, no duplicates).
- `entry_path_quality_score_by_timestamp`: `REPRODUCED_READ_ONLY_TEST_ONLY` (973/973).
- `stop_pressure_risk_score_by_timestamp`: `REPRODUCED_READ_ONLY_TEST_ONLY` (973/973).
- `recovery_guard_decision_by_timestamp`: `REPRODUCED_READ_ONLY_TEST_ONLY` (973/973).
- Test-only readiness: `TEST_ONLY_MASK_CASCADE_COUNTS_READY`.
- Full-dataset guardrail: `FULL_6481_CASCADE_NOT_ALLOWED` and `DO_NOT_BUILD_FULL_6481_CASCADE`.

The probability payload already carries the evaluator feature, setup, regime, price, ATR, future-candle, and actual-label context needed for the 973-row join. No database query or database write was required.

## Diagnostic blocks added

- `read_only_test_only_evaluator_payload_reproduction_audit`
- `test_prediction_payload_source`
- `test_prediction_join_board`
- `test_only_payload_reproduction_board`
- `test_only_reproduced_mask_summary`
- `test_only_cascade_readiness`
- `full_dataset_guardrail`
- `next_step_plan`
- `ml38_10_46_test_only_reproduction_decision`

## Files changed

- `app/experiments/compact_archive_pruner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`

## Files added

- `app/diagnostics/test_only_evaluator_payload_reproduction.py`
- `tests/test_ml38_10_46_read_only_test_only_evaluator_payload_reproduction.py`
- `tests/test_stage_ml38_10_46_report.py`
- `reports/stage_ml38_10_46_read_only_test_only_evaluator_payload_reproduction_report.md`

## Tests and checks

- Authorized `python -m py_compile` check on the diagnostic, analyzer, reporter, pruner, and tuning entrypoint files.
- `python -m pytest tests/test_ml38_10_46_read_only_test_only_evaluator_payload_reproduction.py`.
- `python -m pytest tests/test_stage_ml38_10_46_report.py`.
- Full pytest is not run without explicit user approval.

## Safety confirmation

- Runtime training was not run.
- Clean/fast/quick/sequence/full commands were not run.
- No database writes were performed.
- ml_labels was not written.
- ml_labels.direction_label was not substituted as predicted_label.
- Actual/target labels remained actual/target evidence only.
- Labels, label builders, gates, and model logic were not changed.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifact was created or staged.
- The full 6481 prediction stream remains missing.
- Full 6481 cascade is not allowed.
