# ML38.10.47 — Read-only Test-only Mask Cascade Counts

## Purpose

ML38.10.46 established a read-only test-only reproduction on the TEST_ONLY_973 denominator: all three evaluator values were reproduced for 973/973 rows. This stage adds deterministic mask-cascade counts for those test rows only.

The full 6481 prediction stream was not found. The full 6481 cascade is not allowed. Test-only counts are not a production-like recompute and must not be promoted to full-dataset evidence.

## Read-only test-only result

The audit read `reports/probability_diagnostics_ml_candle_mlp_v1_solusdt_15m_h12_lv31_h12_dates_exit45_long_2026_07_04_135506_445150_e354b20040.json`, the same 973-row payload documented by ML38.10.46. The reference thresholds and recovery configuration were read from the existing reference config definition; no training or production-like recompute was run.

- Input status: `TEST_ONLY_MASK_INPUTS_READY` (973/973 for every required stream, no duplicate join keys).
- Setup quality: 973 input, 225 pass, 748 removed.
- Entry-path quality: 225 input, 218 pass, 7 removed.
- Stop pressure: 218 input, 218 pass, 0 removed.
- Recovery guard: 218 input, 42 pass, 176 removed.
- Final: 42 pass, 931 removed (`4.316547%` pass).
- Removed counts are mutually exclusive and sum to 931; no double counting.
- Decision: `TEST_ONLY_MASK_CASCADE_COUNTS_COMPUTED` and `TEST_ONLY_OUTCOME_AUDIT_READY`.
- Guardrail: `FULL_6481_CASCADE_NOT_ALLOWED`.

## Diagnostic blocks

- `read_only_test_only_mask_cascade_counts_audit`
- `test_only_mask_input_summary`
- `test_only_mask_cascade_board`
- `test_only_mask_removed_breakdown`
- `test_only_distribution_before_after`
- `test_only_final_mask_summary`
- `full_dataset_guardrail`
- `ml38_10_47_test_only_mask_cascade_decision`

The board applies the evaluator-compatible order: setup quality, entry-path quality, stop pressure, optional explicit regime eligibility, and recovery guard. Actual and predicted label distributions remain separate.

## Files changed and added

- Added `app/diagnostics/test_only_mask_cascade_counts.py`.
- Extended analyzer/reporter/compact-pruner propagation for the new diagnostic blocks.
- Added `tests/test_ml38_10_47_read_only_test_only_mask_cascade_counts.py`.
- Added `tests/test_stage_ml38_10_47_report.py`.
- Added this stage report.

## Verification

- The allowed `py_compile` command passed.
- `tests/test_ml38_10_47_read_only_test_only_mask_cascade_counts.py`: 14 passed.
- `tests/test_stage_ml38_10_47_report.py`: 1 passed after correcting report-only Markdown wording.
- Full pytest requires explicit user approval after targeted tests.

## Safety confirmations

- Runtime training was not run.
- Clean/fast/quick/sequence/full commands were not run.
- No database writes were performed.
- ml_labels was not written.
- ml_labels.direction_label was not substituted as predicted_label; it remains actual/target evidence only.
- Labels, label builders, gates, and model logic were not changed.
- Live trading and auto-activation were not changed.
- The diagnostic is read-only and test-only 973.
- The full 6481 cascade is not allowed.
- Test-only counts are not a production-like recompute.
