# ML38.10.54 — Sidecar quick-quality wiring implementation

## Lineage and status

ML38.10.54 follows ML38.10.53 because that preflight found `NOT_READY_SIDEСAR_WIRING_NOT_CONFIRMED`: the exporter existed, but its invocation at the quick-quality candidate boundary and a safe full-dataset row stream were not confirmed. This stage is implementation-only. Its status is `WIRED_NOT_EXECUTED`.

## Wiring implemented

- `prediction_sidecar_wiring.py` builds one exporter-ready row per original train/validation/test `DatasetRow`, using calibrated model softmax probabilities and probability argmax for `predicted_label`.
- The implementation does not derive or substitute predictions from `actual_label`, target fields, `direction_label`, or `ml_labels.direction_label`.
- The quick-quality wrapper now passes an explicit internal sidecar export flag through the ML38.2 CLI, feature-regime runner, label-grid runner, and training pipeline.
- The exporter invocation is connected inside `TrainingService.train`, where the trained model, original split rows, aligned split tensors, model/run identity, and calibrated direction temperature are simultaneously available.
- Artifacts are written below the candidate pipeline run directory in `prediction_payloads/`; no reconstruction from compact reports or probability diagnostics is used.

## Fail-closed controls

- Full-dataset boundary validation requires the declared 6481-row denominator, exact row count, and all train/val/test splits.
- A test-only 973 stream is rejected as `FULL_DATASET_6481`; test-only rows cannot pass by declaring a full-dataset scope.
- Missing split names or timestamps, duplicate join keys, duplicate dataset-row identities, invalid labels/probabilities/confidence, and forbidden prediction sources fail closed.
- source/config consistency validation now checks expected candidate, run, config, model, feature, label, horizon, symbol, and interval values.
- The overwrite guard rejects any existing stream, summary, or schema target unless overwrite is explicitly allowed; candidate wiring leaves overwrite disabled.
- Candidate/report/reporter/analyzer metadata propagates `full_dataset_prediction_sidecar_wiring` and `ml38_10_54_sidecar_quick_quality_wiring_decision`, including `WIRED_NOT_EXECUTED` and non-execution flags.

## Verification

- Allowed `py_compile` check passed.
- ML38.10.54 synthetic/mocked wiring tests passed: 23 tests.
- Stage report tests passed: 2 tests.
- Regression tests passed: ML38.10.50 exporter 11 tests, ML38.10.51 fixture audit 8 tests, and ML38.10.53 historical preflight probe 8 tests.
- All writer tests use pytest temporary directories; no test writes sidecars to `reports/`.

## Safety and non-execution

- quick-quality was not run.
- training/runtime was not run.
- clean, fast-debug, and sequence commands were not run.
- DB writes were not performed.
- ml_labels/ml_predictions were not written.
- real 6481 stream was not created.
- labels/label builders/gates/model logic unchanged.
- full 6481 cascade/outcome remains prohibited until a real stream exists and validates.
- no production-like recompute was performed.
- no tradable edge was established or claimed.

## Next step

The next implementation stage is **ML38.10.55 — preflight re-probe after wiring**. An approved real quick-quality generation may occur only after a separate explicit user approval; ML38.10.54 itself does not authorize it.
