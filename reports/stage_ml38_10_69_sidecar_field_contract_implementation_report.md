# ML38.10.69 — SIDECAR_FIELD_CONTRACT_IMPLEMENTATION

## Stage rationale and source path

ML38.10.69 follows ML38.10.68 because the calibration replay diagnostic proved that the compact sidecar supported distribution replay but lacked raw probabilities and row-level actual labels. The exact implementation path is `TrainingService.train -> build_full_dataset_prediction_sidecar_rows -> write_prediction_sidecar_artifacts`.

## Implementation summary

Future sidecar rows use the versioned `ml38.10.69` schema, writer, and prediction field contract. The row contract adds raw probabilities, calibrated probabilities, actual label, deterministic `row_alignment_key`, and explicit prediction layers. Existing `prob_down`, `prob_flat`, and `prob_up` fields remain backward-compatible aliases of the calibrated probability fields; `predicted_label` remains an explicitly documented alias of calibrated sidecar argmax.

The raw probability source is `direction_logits` at temperature=1.0, computed with numerically stable softmax. The actual label source is `source_row.direction_label`. The calibrated probability source remains the current temperature-scaled model probability output passed by `TrainingService`.

The deterministic alignment key is `sha256:` plus SHA-256 of canonical JSON containing candidate_id, symbol, interval, horizon, split, row_index_global, row_index_split, and timestamp. It contains no UUID, random value, filesystem path, or run-dependent fragment.

Prediction layers are kept separate: `raw_model_softmax_temperature_1`, `calibrated_model_softmax`, and `sidecar_selected`. The downstream policy output is unavailable at this writer boundary and is explicitly marked unavailable; it is not inferred or conflated with calibrated sidecar argmax. The downstream 472/109/392 distribution, calibrated sidecar argmax 532/15/426 distribution, and distribution-only 281/400/292 replay remain distinct.

The fail-closed validation runs before artifact directory creation. It rejects missing required identity/alignment fields, actual labels, raw or calibrated probabilities, invalid class keys, non-finite or negative values, invalid sums, missing prediction layers, source/config mismatch, and duplicate row_alignment_key values. Schema and summary metadata expose the contract versions and presence/uniqueness flags. Denominator behavior remains unchanged.

## Scope and guardrails

This stage performed no training/wrapper/quick-quality run, no DB writes, and no real artifacts mutated. It created no new real sidecars/ZIP. Existing real JSONL, summaries, ZIP files, and reports were not normalized or regenerated. Archive recovery was not performed.

The h08 issue remains separately scoped: candidate boundary 6485 versus current global expected denominator 6481, delta +4; h08 fix not applied. Labels, label builders, gates, model training logic, class weights, training objective, and production calibration policy were not changed. `directional_confidence_floor 0.60 not implemented`; `flat override not implemented`.

The distribution-only replay policy was not introduced. `cascade/outcome remains blocked`. `production-like recompute/tradable edge not claimed`.

## Verification

Targeted checks completed:

- `py_compile` passed for TrainingService, sidecar wiring/exporter, and touched sidecar diagnostics.
- ML38.10.69 field-contract tests: 18 passed.
- ML38.10.69 report tests: 2 passed.
- ML38.10.68 regression: 8 passed.
- ML38.10.67 regression: 6 passed.
- ML38.10.66 regression: 5 passed.
- ML38.10.64 regression: 4 passed.
- Existing sidecar wiring regression: 23 passed.
- Existing writer metadata regression: 6 passed.
- TrainingService import passed.
- Class-weight collect-only: 1 test collected.
- `git diff --check` passed before the full-suite run.

Narrow regression fix: the ML38.10.55 static probe was updated to distinguish required `actual_label` target export from forbidden label substitution. `actual_label` is required in future sidecars for outcome-aware replay, while `predicted_label`, `current_predicted_label`, `sidecar_argmax_label`, and the `sidecar_selected` label still derive from calibrated probability argmax. No label substitution was detected. The targeted formerly failing test passed, and the complete ML38.10.55 probe file passed with 13 tests.

Completed full pytest result after the static-probe fix: 1160 passed, 0 skipped, 0 warnings in 94.26 seconds; exit code 0; wall time 97.5170548 seconds. External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_69_static_probe_fix_20260707_235953.log`.

## Decision and next stage

Final decision: `SIDECAR_FIELD_CONTRACT_IMPLEMENTED_TESTED_NO_REAL_RUN`.

`ML38.10.70 — POST_FIELD_CONTRACT_SOLUSDT_QUICK_QUALITY_RERUN_READINESS` is not yet authorized. No training/wrapper/quick-quality run, DB write, or real artifact mutation was performed. The h08 denominator issue remains separate and was not fixed. Production calibration policy, directional confidence floor 0.60, and flat override remain unchanged. Cascade/outcome remains blocked, and no production-like recompute or tradable edge is claimed.
