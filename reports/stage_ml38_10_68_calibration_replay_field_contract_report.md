# ML38.10.68 — calibration replay field contract diagnostic

## Final decision

`FIELD_CONTRACT_DIAGNOSTIC_COMPLETED_NEXT_ACTION_SELECTED`.

ML38.10.68 follows ML38.10.67 because distribution replay found calibrated probabilities but no raw probabilities or row-level actual labels. Distribution-only replay can describe class counts, but it cannot rank policies by correctness, baseline edge, folds, or profit/risk. The selected ML38.10.69 action is `SIDECAR_FIELD_CONTRACT_IMPLEMENTATION`.

## Source discovery

The row construction path is `TrainingService.train` in `app/training/training_service.py` → `build_full_dataset_prediction_sidecar_rows` in `app/experiments/prediction_sidecar_wiring.py`. `write_prediction_sidecar_artifacts` in `app/experiments/prediction_sidecar_exporter.py` writes `full_dataset_prediction_stream.jsonl`; the same function calls `build_prediction_sidecar_summary` for `full_dataset_prediction_stream_summary.json` and `build_prediction_payload_schema` for `prediction_payload_schema.json`.

At this boundary, `direction_logits` are available. Calibrated probabilities are produced with `softmax_with_temperature(direction_temperature)`; raw probabilities are source-available from the same logits with temperature 1.0 but are not exported. The original split rows expose `direction_label` (actual labels) and `candle_open_time`. The wiring already creates split name, dataset/global row index, split-local row index, candidate ID, and the `symbol+interval+candle_open_time` join key.

The expected denominator is currently the global/hardcoded 6481 in `TrainingPipelineConfig.prediction_sidecar_expected_row_count`, `TrainingService.train`, and exporter `FULL_DATASET_ROW_COUNT`. The candidate-specific boundary is available after `DatasetBuilder.split_rows` as the materialized `split_rows` lengths. Row-level fold/profit keys were not proven at this export boundary and remain optional/UNKNOWN.

## Prediction layer mapping

- ML38.10.66 downstream policy output 472/109/392 (DOWN/FLAT/UP).
- Sidecar argmax 532/15/426, derived from stored calibrated softmax probabilities.
- Best distribution-only policy 281/400/292 at `directional_confidence_floor=0.60`.

Source-layer warning: The ML38.10.66 current distribution is downstream policy output; the sidecar stores calibrated softmax argmax (532/15/426), so they must not be conflated. These layers are explicitly separate in this diagnostic.

## Current compact sidecar status

All 45 existing sidecar sets were previously validated and were inspected read-only. They contain calibrated probabilities, split, candidate identity, timestamp, global/split indices, and an existing alignment key. They do not contain raw probabilities, row-level actual labels, fold ID, or a profit join key. Therefore they support distribution replay but remain `INCOMPLETE_FOR_OUTCOME_AWARE_REPLAY`; they do not support raw-vs-calibrated replay or fold/profit ranking.

## Required row alignment contract

The future versioned row contract requires candidate, symbol, interval, horizon, split, global and split-local indices, timestamp/candle open time, actual label, current predicted label, sidecar argmax label, raw DOWN/FLAT/UP probabilities, calibrated DOWN/FLAT/UP probabilities, selected probability source, schema/writer versions, and a stable unique row alignment key. A downstream-policy label and replay-policy label are optional explicit layers. Fold ID and profit join key are optional for basic accuracy replay but mandatory and fail-closed when fold/profit ranking is requested.

Fail-closed checks must reject missing actual labels for outcome metrics, missing raw probabilities for raw/calibrated comparison, missing or duplicate alignment keys for joins, incomplete probability triplets, invalid probability sums, ambiguous prediction layers, row-count/split-boundary mismatches, and unsupported schema/writer versions.

## Missing-field impact and synthetic behavior

Missing raw probabilities block raw-vs-calibrated replay and calibration-method-effect diagnosis. Missing actual labels block accuracy, majority baseline, accuracy edge, FLAT recall, false-directional-on-actual-FLAT, and outcome ranking. Missing row alignment blocks label/fold/profit joins and timestamp traceability. Missing fold/profit keys blocks walk-forward and profit-risk ranking without blocking basic row-aligned accuracy ranking.

Synthetic tests prove that a complete row-aligned payload enables accuracy, majority baseline, accuracy edge, FLAT recall, false directional count, raw/calibrated comparison capability, and row-level reranking. They also prove each fail-closed missing-field case and classify the current compact shape as incomplete. Distribution-only replay is insufficient for selecting a production policy.

## h08 separate scope

The failed h08 candidate boundary remains 4539 + 973 + 973 = 6485 versus the global expected denominator 6481, delta +4. No h08 fix was applied. This is a candidate-boundary denominator contract, not the calibration field contract, and stays in a separate ML38.10.69-or-later scope.

## ML38.10.69 recommendation

Action type: `SIDECAR_FIELD_CONTRACT_IMPLEMENTATION`.

Selected next stage: `ML38.10.69 — SIDECAR_FIELD_CONTRACT_IMPLEMENTATION`.

Action summary: add versioned raw/calibrated probabilities, actual label, explicit prediction layers, and a stable row-alignment key at the TrainingService-to-sidecar wiring boundary with fail-closed validation. Keep fold/profit keys optional until their row-level source is proven. No new training run is needed yet. A real run is not part of that implementation stage; if export output changes, one SOLUSDT quick-quality wrapper rerun is allowed only after implementation, targeted tests, separately approved full pytest, and separate run approval.

## Guardrails and checks

This was a no training run, no wrapper/quick-quality rerun, no DB write, and no artifact mutation stage. No real sidecars or ZIP were created. Labels, label builders, gates, model logic, class weights, training objective, and production calibration logic were unchanged. `directional_confidence_floor 0.60 was NOT implemented`. Flat override was NOT implemented. Sidecar production export logic was not changed.

Cascade/outcome blocked. Production-like recompute was not performed or claimed. Tradable edge was not claimed.

Tests/checks run:

- `py_compile` for the diagnostic module: passed.
- ML38.10.68 diagnostic tests: 8 passed.
- ML38.10.68 report tests: 2 passed.
- ML38.10.67 regression: 6 passed.
- ML38.10.66 regression: 5 passed.
- ML38.10.64 regression: 4 passed.
- `TrainingService` import: passed.
- class-weight collect-only: 1 test collected.
- `git diff --check`: passed.
- Full pytest: 1140 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 114.34 seconds.
- Full pytest wall time: 117.97 seconds.
- Full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_68_20260707_232611.log` (external to the repository).

Final decision after full regression: `FIELD_CONTRACT_DIAGNOSTIC_COMPLETED_NEXT_ACTION_SELECTED`. Cascade/outcome remains blocked; production-like recompute remains blocked; a tradable-edge claim remains blocked.
