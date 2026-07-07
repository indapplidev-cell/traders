# ML38.10.67 — SOLUSDT calibration replay

Final decision: `CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS`.

ML38.10.67 follows ML38.10.66 `CALIBRATION_TUNING` because all 45 completed candidates failed the baseline edge and exposed the same severe class-distribution mismatch. This stage tested the existing evidence read-only; it did not start a new real run.

## Evidence and sidecar validation

- Output: `D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_151645`
- ZIP: the matching `.zip` beside that output directory
- External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\solusdt_quick_quality_20260707_181639.log`
- Completion marker: `D:\disk_E\game_projects\traders\traders-ml-run-logs\solusdt_quick_quality_20260707_181639.completion.json`
- Found and validated: 45 streams, 45 summaries, 45 schemas; 45 complete sets and zero incomplete sets.
- Exact bytes, LF-only, schema, and summary contracts all validate. The required observed SHA-256 is `5ef2a0492f33686e5885fe9d2128bf223df8d4b7c0f0939fd3486f0d8100f3c4`.

## Probability fields and baseline

The sidecars contain `prob_down`, `prob_flat`, and `prob_up` with source semantics `training_service_calibrated_model_softmax_argmax`. Separate raw probabilities are absent: `RAW_PROBABILITIES_NOT_AVAILABLE_IN_SIDECAR`. Row-level actual labels, fold membership, and profit/outcome rows are also absent from the compact artifacts.

The ML38.10.66 selected downstream-policy baseline remains actual DOWN/FLAT/UP = 31/899/43 and predicted DOWN/FLAT/UP = 472/109/392: actual FLAT 899 versus predicted FLAT 109. Accuracy is 0.1880781089414183 versus the FLAT-majority baseline 0.9239465570400822, for accuracy edge -0.7358684480986639. The derived false-directional count on actual FLAT is 790 and directional overprediction is 864 predicted versus 74 actual.

The sidecar layer is different: its stored calibrated-softmax argmax is 532/15/426. The report does not conflate that raw decision layer with the ML38.10.66 selected `flat_on_low_margin` output.

## Read-only policy grid

The diagnostic replayed 19 policies over 45 candidates, 855 candidate-policy pairs. All 45 test probability sequences and resulting distributions are identical. This rules out candidate-specific configuration as the immediate explanation for the replayed probability behavior.

The largest FLAT recoveries in the bounded grid are:

| Policy | Parameters | DOWN/FLAT/UP | FLAT gain vs sidecar argmax |
|---|---:|---:|---:|
| directional confidence floor | 0.60 | 281/400/292 | +385 |
| directional confidence floor | 0.55 | 332/324/317 | +309 |
| combined conservative | threshold 0.55, margin 0.10 | 332/324/317 | +309 |
| flat minimum probability | 0.30 | 357/270/346 | +255 |
| directional confidence floor | 0.50 | 369/262/342 | +247 |

Every bounded policy improves FLAT recovery relative to sidecar argmax, but even the strongest produces only 400 FLAT, 499 below actual FLAT. No policy is shown to reach or beat the majority baseline: accuracy, recall, false-directional reduction, fold sensitivity, and profit/risk cannot be recomputed without row-aligned target/outcome evidence. Therefore none is approved for implementation.

## Calibration finding

Thresholding helps but is not the main sufficient fix. The evidence points to class-prior/class-balance mismatch: actual FLAT is 92.39%, mean available FLAT probability is about 0.265, all candidate probability sequences are identical, and temperature scaling can improve NLL/Brier but cannot change argmax ordering by itself. Source inspection also shows that the `trade_two_stage` direction class-weight path zeros the FLAT direction weight. That is a diagnostic clue, not a causal production claim; raw probabilities and row-aligned labels are still required before choosing between calibration, class-prior correction, or objective rebalance.

No bounded calibration implementation zone is selected. The 0.55–0.60 directional-confidence floor is the strongest distribution sensitivity zone, but it is not outcome-validated. The best replay policy is `directional_confidence_floor 0.60 -> 281/400/292`, recovering 291 FLAT predictions versus the current 472/109/392 policy output while remaining 499 FLAT predictions below the actual 31/899/43 distribution.

## h08 denominator contract

Candidate `lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax` failed in `train_model`: produced 6485 rows versus expected 6481, delta +4. The produced boundary is train 4539 + validation 973 + test 973 = 6485. The expected count comes from a hardcoded 6481 default in `TrainingPipelineConfig`, is forwarded through `TrainingService`, and is reinforced by the exporter `FULL_DATASET_6481` contract.

The likely cause is an h08-specific usable dataset boundary being checked against the h12/global denominator. A later minimal fix should derive expected count and denominator scope from the materialized candidate splits while retaining fail-closed validation. ML38.10.67 adds only a synthetic mismatch diagnostic test; no h08 production fix was applied.

## Selected ML38.10.68 action

Action type: `CALIBRATION_REPLAY_INCOMPLETE_NEEDS_FIELDS`.

Add a bounded diagnostic-only contract exposing row-level actual labels plus raw and calibrated probabilities, with fold/profit join keys where already available, then repeat the read-only ranking. Do not implement production calibration from distribution alone. Keep the h08 dynamic-denominator fix as a separately scoped minimal change.

## Guardrails and checks

There was no training run, no wrapper or quick-quality rerun, no runtime execution, no DB write, and no write to `ml_labels` or `ml_predictions`. Labels, label builders, gates, model logic, analyzer production logic, and production calibration logic were not changed. Existing real artifacts were not mutated; no sidecars or ZIPs were created; no archive recovery was performed.

Checks executed:

- `py_compile` for the new diagnostic: passed.
- ML38.10.67 diagnostic tests: 6 passed.
- ML38.10.67 report tests: 2 passed.
- ML38.10.66 regression: 5 passed.
- ML38.10.64 regression: 4 passed.
- ML38.10.63 regression: 4 passed.
- `TrainingService` import: passed.
- `tests/test_class_weights.py --collect-only`: 1 test collected.
- `git diff --check`: passed.
- Full pytest: 1130 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Pytest time: 106.49 seconds.
- Full pytest wall time: 109.874 seconds.
- Full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_67_20260707_225010.log`.

Final decision: `CALIBRATION_REPLAY_INCOMPLETE_MISSING_PROBABILITY_FIELDS`. The evidence remains 45/45 valid sidecars, 19 policies and 855 replay pairs. Calibrated fields were found; raw probabilities and row-level actual labels were absent. Distribution replay is possible, but outcome ranking remains incomplete. The accuracy edge remains -0.7358684480986639. The h08 contract remains 6485 candidate rows versus hardcoded expected 6481, delta +4.

The next stage is `ML38.10.68 — CALIBRATION_REPLAY_INCOMPLETE_NEEDS_FIELDS`: add diagnostic raw/calibrated/actual row alignment, rerank calibration policies, and keep the h08 denominator fix separately scoped. No new training run is needed yet, and `run_fv3_cached_tuning.py` remains blocked.

Cascade/outcome blocked. Production-like recompute blocked. Tradable edge claim blocked.
