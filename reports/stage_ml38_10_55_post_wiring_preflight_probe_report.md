# ML38.10.55 — Post-wiring sidecar generation preflight re-probe

## Lineage and scope

ML38.10.55 follows ML38.10.54 because ML38.10.54 changed the sidecar state from not wired to `WIRED_NOT_EXECUTED`. This stage performs a read-only static re-probe of that wiring before any separately approved real execution.

The preferred future command remains `python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT`, but it was not executed by this stage.

## Static probe results

- flag propagation: PASS across wrapper, CLI, feature-regime runner, label-grid runner, training pipeline, TrainingService, wiring helper, and exporter.
- TrainingService wiring: `TRAINING_SERVICE_WIRING_CONFIRMED`; the opt-in branch lazily imports both helpers, captures train/validation/test calibrated model softmax probabilities, builds rows, and invokes the guarded writer.
- row construction contract: `ROW_CONSTRUCTION_CONTRACT_CONFIRMED`; `predicted_label` comes from model-probability argmax, not labels or `ml_labels.direction_label`.
- full-dataset boundary: `FULL_DATASET_BOUNDARY_ENFORCEMENT_CONFIRMED`; `FULL_DATASET_6481` requires exactly 6481 rows, train/val/test, matching split totals, timestamps, and unique join/row identities.
- test-only rejection: `TEST_ONLY_REJECTION_CONFIRMED`; a 973-row test-only stream cannot pass as the full dataset.
- source/config consistency: `CONSISTENCY_VALIDATION_HARDENED`; candidate, run, config, model, feature, label, horizon, symbol, interval, denominator, and dataset-row identity checks fail closed.
- overwrite guard: `OVERWRITE_GUARD_CONFIRMED`; existing JSONL, summary, or schema targets block writing unless overwrite is explicitly enabled.
- compact whitelist: PASS for the four approved prediction payloads and rejection of raw-feature and credential paths.
- reporter/analyzer metadata: `REPORTER_ANALYZER_METADATA_CONFIRMED`; `WIRED_NOT_EXECUTED`, ML38.10.54 decisions, non-execution state, and sidecar result/failure metadata are reportable.
- import-cycle fix: `IMPORT_CYCLE_FIX_CONFIRMED`; TrainingService has no top-level prediction-sidecar-wiring import and uses the lazy opt-in import.

## Approval readiness gate

Static status: `READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN`.

This is not execution approval. `quick_quality_run_allowed_by_this_stage=false`. One real SOLUSDT 15m quick-quality run requires separate explicit user approval after this stage is committed, using the reviewed ML38.10.54 wiring. Until that approval is given, the preferred command remains blocked.

## Safety and non-execution

- quick-quality was not run.
- training/runtime was not run.
- clean, fast-debug, and sequence commands were not run.
- DB writes were not performed.
- ml_labels/ml_predictions were not written.
- real 6481 stream was not created.
- real sidecars were not written to `reports/`.
- labels/label builders/gates/model logic remained unchanged.
- full 6481 cascade/outcome remains prohibited until a real stream exists and validates.
- no production-like recompute was performed.
- no tradable edge was established or claimed.

## Changed and added files

Changed existing files: none.

Added files:

- `app/diagnostics/post_wiring_sidecar_generation_preflight_probe.py`
- `tests/test_ml38_10_55_post_wiring_preflight_probe.py`
- `tests/test_stage_ml38_10_55_report.py`
- `reports/stage_ml38_10_55_post_wiring_preflight_probe_report.md`

## Tests

Only the authorized py_compile, targeted pytest, direct import, collection-only, diff checks, and the subsequently approved full regression suite were run:

- specified `py_compile`: passed.
- ML38.10.55 post-wiring probe tests: 13 passed.
- ML38.10.55 stage report tests: 2 passed.
- ML38.10.54 wiring regression tests: 23 passed.
- ML38.10.53 preflight regression tests: 8 passed.
- ML38.10.50 exporter regression tests: 11 passed.
- targeted pytest total: 57 passed.
- direct `TrainingService` import: passed.
- `tests/test_class_weights.py --collect-only`: 1 test collected, passed.
- `git diff --check`: passed.
- full pytest: 1045 passed, 0 skipped, 1 warning.
- full pytest exit code: 0.
- pytest time: 80.40s.
- total command time: 83.355s.
- full pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_55_20260706_113509.log` (outside the repository; not committed).
- final post-wiring status: `READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN`.
- approval gate: real quick-quality generation still requires separate explicit user approval after commit.
