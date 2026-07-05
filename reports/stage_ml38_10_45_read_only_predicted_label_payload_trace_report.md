# ML38.10.45 — Read-only Predicted Label Payload Trace Audit

## Purpose

ML38.10.44 proved that the 6,481 dataset-compatible rows contain the feature, setup, price, ATR, future-candle, and production-label inputs needed for evaluator payload reproduction. Reproduction remained blocked because the original evaluator `predicted_label by timestamp` was missing from every row.

`ml_labels.direction_label` is the production target/actual label. It is not the evaluator prediction: actual labels cannot be used as evaluator predicted direction. Substitution would introduce target leakage and invalidate entry-path quality, stop-pressure, recovery-guard, and mask-cascade results.

## Read-only sources traced

- Full uncompressed `candidate_results/<candidate>.json` files under `reports/feature_regime_experiments/**`.
- Compact quick-quality ZIP candidate JSON.
- Compact omission metadata for `selected_predictions`, `calibrated_rows`, `selected_rows`, `score_rows`, and `signal_rows`.
- The `ml_predictions` model/table contract (`candle_open_time`, probabilities, and `direction`).
- Existing reports, caches, temporary/runtime diagnostic folders, and probability diagnostics.
- Candidate aggregate and row payloads under bounded calibration, calibrated decisions, decision policy, probability, entry-path quality, profit-aware, and walk-forward diagnostics.

The exact compact candidate payload has 973-row omission markers. A matching uncompressed probability diagnostics file for model version `ml_candle_mlp_v1_solusdt_15m_h12_lv31_h12_dates_exit45_long_2026_07_04_135506_445150_e354b20040` contains timestamped `calibrated_rows` with `candle_open_time`, `predicted_label`, and probability columns. This is evidence for a test-only 973-row join, not a 6,481-row dataset join. The correct status is `PARTIAL_TEST_ONLY_JOIN_READY`; the full mask cascade remains blocked.

## Diagnostic blocks added

- `read_only_predicted_label_payload_trace_audit`
- `predicted_label_source_discovery_board`
- `candidate_payload_omission_audit`
- `prediction_row_locator_board`
- `timestamp_prediction_join_readiness`
- `actual_vs_predicted_guardrail`
- `trace_blockers`
- `next_reproduction_plan`
- `ml38_10_45_predicted_label_trace_decision`

## Files changed

- `app/experiments/compact_archive_pruner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`

## Files added

- `app/diagnostics/predicted_label_payload_trace.py`
- `tests/test_ml38_10_45_read_only_predicted_label_payload_trace.py`
- `tests/test_stage_ml38_10_45_report.py`
- `reports/stage_ml38_10_45_read_only_predicted_label_payload_trace_report.md`

## Tests and checks

- `python -m py_compile` on the authorized diagnostic, analyzer, reporter, pruner, and tuning entrypoint files.
- `python -m pytest tests/test_ml38_10_45_read_only_predicted_label_payload_trace.py`
- `python -m pytest tests/test_stage_ml38_10_45_report.py`
- Full pytest is not run without explicit user approval.

## Safety confirmation

- Runtime training was not run.
- Clean/fast/quick/sequence/full commands were not run.
- No database writes were performed.
- ml_labels was not written.
- Labels, label builders, gates, and model logic were not changed.
- Live trading and auto-activation were not changed.
- No actual label was substituted for `predicted_label`.
- No runtime JSON, ZIP, or log artifact was created or staged.
