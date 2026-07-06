# ML38.10.58 — sidecar writer metadata/archive contract fix

## Why this stage follows ML38.10.57

ML38.10.57 confirmed `CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED`: summaries hashed LF-normalized in-memory JSONL while Windows wrote CRLF bytes. All 45 audited real sidecar sets matched only the LF-normalized representation. Runtime summaries also reused static `WIRED_NOT_EXECUTED` metadata, the real-run ZIP was missing, and shell timeout 124 lost the Python exit code.

ML38.10.58 is a code/test-only future-contract fix. Existing real artifacts were not rewritten, normalized, repackaged, or otherwise mutated.

## Exact writer hash/size contract

The selected contract is `EXACT_BYTES_HASH_AND_SIZE_AFTER_WRITE`:

- canonical JSONL is encoded as UTF-8 with explicit LF separators;
- JSONL is written with `Path.write_bytes`, avoiding platform newline conversion;
- the writer reads the file bytes back after writing;
- `sha256` is the SHA-256 of those exact file bytes;
- `size_bytes` is the exact byte count after writing;
- exact-byte validation runs before the companion summary is emitted;
- LF-normalized-only matches fail closed with `SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES`.

The summary keeps backward-compatible `sha256` and `size_bytes` names and adds `hash_contract`, `line_ending_contract`, `byte_size_contract`, and `writer_contract_version`. The schema version is `ml38.10.58`, and its `summary_contract` documents these semantics.

## Runtime metadata truth contract

Static wiring metadata remains under `full_dataset_prediction_sidecar_wiring`; it is not used as runtime truth. A successful future write adds `sidecar_runtime_truth` with `runtime_execution_status=EXECUTED`, requested/completed flags, `real_full_dataset_stream_created=true`, validation status, archive status, and completion status. Facts unavailable to the writer—such as whether an external wrapper is quick-quality—are `null`/`UNKNOWN`, never fabricated as `false`.

## Archive/ZIP status contract

Future summary metadata can distinguish `NOT_REQUESTED`, `MISSING`, and `UNKNOWN`. It carries `archive_expected`, `archive_created`, `archive_path`, `archive_contains_sidecars`, `archive_status`, and `sidecar_retention_confirmed`. Retention is never confirmed unless packaging code later creates and inspects an archive. No ZIP was created and no recovery of the existing run was performed in this stage. The compact whitelist was unchanged.

## Timeout/exit-code contract

The sidecar writer reports external completion facts as unknown: `controlling_shell_exit_code=null`, `python_exit_code=null`, `timeout_detected=null`, `child_completed_later=null`, `completion_marker_written=false`, and `run_exit_code_status=UNKNOWN_OR_EXTERNAL`. A controlling wrapper may later replace this with known values or `LOST_DUE_TIMEOUT`; the writer does not fake a Python exit code.

## Legacy artifact policy

Legacy normalized-only artifacts remain untouched and are not accepted as exact-byte valid. Validation is read-only and fail-closed. Existing real summaries, JSONL streams, schemas, and archives were not recreated.

## Changed files

- `app/experiments/prediction_sidecar_exporter.py`
- `app/experiments/prediction_sidecar_wiring.py`
- `app/diagnostics/real_quick_quality_sidecar_validation_audit.py`
- `app/diagnostics/real_sidecar_generation_preflight_probe.py`
- `tests/test_ml38_10_53_real_sidecar_generation_preflight_probe.py`

## Added files

- `app/diagnostics/sidecar_writer_metadata_archive_contract_fix.py`
- `tests/test_ml38_10_58_sidecar_writer_metadata_archive_contract_fix.py`
- `tests/test_stage_ml38_10_58_report.py`
- `reports/stage_ml38_10_58_sidecar_writer_metadata_archive_contract_fix_report.md`

## Tests run

- permitted `py_compile`: passed;
- ML38.10.58 contract tests: 6 passed;
- ML38.10.58 report tests: 2 passed;
- ML38.10.50 exporter regressions: 11 passed;
- ML38.10.51 fixture-audit regressions: 8 passed;
- ML38.10.54 wiring regressions: 23 passed;
- ML38.10.56 validation-audit regressions: 7 passed;
- ML38.10.57 CRLF/LF audit regressions: 8 passed;
- direct `TrainingService` import: passed;
- `tests/test_class_weights.py --collect-only`: 1 test collected;
- `git diff --check`: passed.

The unique targeted pytest set initially totaled 65 passed tests across the seven authorized test files. During that initial targeted-check phase, Full pytest is not authorized by this stage and was not run.

## Full pytest first attempt

- result: failed during collection;
- exit code: 2;
- collected: 1064 items / 1 error;
- failing test: `tests/test_ml38_10_53_real_sidecar_generation_preflight_probe.py`;
- root cause: the stale ML38.10.53 static probe required the source marker `.write_text(` after ML38.10.58 intentionally replaced the JSONL text writer with the exact-byte contract;
- root-cause detail: the stale ML38.10.53 diagnostic expected `.write_text(` via `.index(...)`;
- fix: diagnostic source inspection now uses safe `.find()` optional-marker detection and supports `EXACT_BYTE_WRITE`, `LEGACY_TEXT_WRITE`, and `UNKNOWN`;
- `UNKNOWN` fails closed without an import/collection exception;
- the ML38.10.58 exact-byte writer contract was not rolled back;
- no quick-quality, training, or runtime rerun;
- no database writes or real artifact mutation.

Post-fix targeted verification passed: 10 ML38.10.53 probe tests plus the 65 previously authorized contract/regression tests, for 75 unique passed tests across eight files. The ML38.10.58 exact-byte writer contract was not changed or rolled back.

## Full pytest retry

- result: 1074 passed, 0 skipped, 1 warning;
- exit code: 0;
- pytest time: 80.58 seconds;
- wall time: 83.562 seconds;
- log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_58_retry_20260706_181153.log`;
- the ML38.10.53 collection failure no longer reproduces.

## Confirmed final contract

- writer: UTF-8/LF binary write with exact-byte SHA-256 and size after write;
- schema version: `ml38.10.58`;
- summary fields: `hash_contract`, `line_ending_contract`, `byte_size_contract`, `writer_contract_version`;
- runtime metadata: `sidecar_runtime_truth`, with `UNKNOWN`/`null` for facts unavailable to the writer;
- archive statuses: `NOT_REQUESTED`, `MISSING`, and `UNKNOWN` without false retention confirmation;
- completion contract: controlling-shell/Python exit codes, timeout detection, late-child completion, and completion-marker state;
- legacy LF-normalized-only artifacts fail closed and are never rewritten;
- ML38.10.53 source-probe compatibility recognizes current exact-byte and legacy text writers and fails closed for unknown writers.

## Safety prohibitions observed

- no quick-quality, fast-debug, training, or runtime execution;
- no database writes and no `ml_labels`/`ml_predictions` writes;
- no label, label-builder, gate, or model-logic changes;
- no existing real artifact mutation or normalization;
- no new real sidecars and no archive recovery/ZIP creation;
- no full 6481 cascade/outcome; it remains blocked;
- no production-like recompute claim;
- no tradable-edge claim;
- no use of actual labels or `ml_labels.direction_label` as `predicted_label`.

## Decision

Final status: `SIDECAR_WRITER_METADATA_ARCHIVE_CONTRACT_FIXED_NOT_EXECUTED`.

Implementation code fixes the future sidecar contract. Quick-quality was not rerun, existing real artifacts were not mutated, and no new real sidecars or ZIP files were created. Legacy artifacts remain fail-closed and unchanged. Full 6481 cascade/outcome remains prohibited. This stage is not a production-like recompute and establishes no tradable edge.
