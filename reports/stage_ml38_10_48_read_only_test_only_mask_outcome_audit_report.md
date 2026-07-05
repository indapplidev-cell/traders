# ML38.10.48 — Read-only Test-only Mask Outcome Audit

## Purpose and scope

ML38.10.47 established the deterministic `TEST_ONLY_973` mask cascade and produced **42 pass / 931 removed**. ML38.10.48 is needed to inspect prediction outcomes after that selectivity, while preserving the original denominator boundary. This stage analyzes only the 42 final pass rows.

The full 6481 prediction stream was not found. Therefore, the full 6481 cascade and outcome audit are not allowed. This is not a production-like recompute and is not a tradable edge. The sample-size warning remains active for 42 rows.

## Diagnostic result

The implementation computes actual and predicted distributions independently, a predicted-vs-actual confusion matrix, directional hit/hard-miss/FLAT-leakage counts, UP/DOWN precision, confidence summaries when fields exist, and R-outcome summaries only when explicit read-only row-level outcome fields exist.

The ML38.10.47 snapshot establishes the final-pass marginals:

- Actual: DOWN 8, FLAT 25, UP 9; 17 directional and 25 flat.
- Predicted: DOWN 22, UP 20, FLAT 0; all 42 predictions directional.
- Confusion matrix (`predicted -> actual`): UP -> UP 9 / DOWN 0 / FLAT 11; DOWN -> UP 0 / DOWN 8 / FLAT 14.
- Directional hits: 17; hard wrong-direction misses: 0; FLAT leakage: 25 (`59.523810%`).
- UP precision: `9/20 = 45.000000%`; DOWN precision: `8/22 = 36.363636%`; all-directional same-side precision: `17/42 = 40.476190%`.
- Confidence: 42 rows, min `0.645897`, max `0.689635`, mean `0.667488`, median `0.654400`, p25 `0.651281`, p75 `0.684840`.
- Profit status: `PROFIT_OUTCOME_MISSING`. No explicit row-level `outcome_r`/`net_r` field was present, so no R or profit edge conclusion was computed.

## Diagnostic blocks added

- `read_only_test_only_mask_outcome_audit`
- `test_only_outcome_input_summary`
- `final_pass_label_prediction_distribution`
- `final_pass_confusion_matrix`
- `final_pass_directional_precision_board`
- `final_pass_probability_confidence_summary`
- `final_pass_profit_outcome_summary`
- `final_pass_sample_rows`
- `test_only_outcome_interpretation`
- `full_dataset_guardrail`
- `ml38_10_48_test_only_outcome_decision`

## Files changed and added

- Added `app/diagnostics/test_only_mask_outcome_audit.py`.
- Extended `app/experiments/multi_symbol_feature_regime_analyzer.py`.
- Extended `app/experiments/multi_symbol_feature_regime_reporter.py`.
- Extended `app/experiments/feature_regime_experiment_reporter.py`.
- Extended `app/experiments/compact_archive_pruner.py`.
- Added `tests/test_ml38_10_48_read_only_test_only_mask_outcome_audit.py`.
- Added `tests/test_stage_ml38_10_48_report.py`.
- Added this stage report.

## Verification

- The allowed `py_compile` command passed.
- `tests/test_ml38_10_48_read_only_test_only_mask_outcome_audit.py`: 15 passed.
- `tests/test_stage_ml38_10_48_report.py`: 1 passed.
- A read-only invocation against the existing 973-row probability payload reproduced 42 final-pass rows and the outcome metrics above; it created no artifact and performed no writes.
- Full pytest was not run; it requires explicit user approval after targeted tests.

## Safety confirmations

- Runtime and training were not run.
- Clean/fast/quick/sequence/full commands were not run.
- No database writes were performed.
- ml_labels was not written.
- ml_labels.direction_label was not substituted as predicted_label; it remains actual/target evidence only.
- Labels, label builders, gates, and model logic were not changed.
- Live trading and auto-activation were not changed.
- No runtime JSON, ZIP, or log artifact was created or staged.
- The full 6481 cascade and outcome audit are not allowed.
- Test-only outcome evidence is not a production-like recompute and is not a tradable edge.
