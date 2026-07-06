# ML38.10.59 post-fix sidecar fixture validation report

## Why ML38.10.59 follows ML38.10.58

ML38.10.58 fixed the future sidecar writer and metadata/archive contracts but did not execute a new export. ML38.10.59 validates that implementation on synthetic/tmp_path only. The previous status was `SIDECAR_WRITER_METADATA_ARCHIVE_CONTRACT_FIXED_NOT_EXECUTED`.

## Previous ML38.10.58 contract summary

The writer uses deterministic UTF-8/LF bytes, hashes and sizes exact bytes after write, declares schema and writer version `ml38.10.58`, separates `sidecar_runtime_truth` from static wiring, represents unknown facts with `UNKNOWN`/null, supports truthful archive/completion states, and rejects legacy normalized-only hashes.

## Diagnostic summary

`post_fix_sidecar_fixture_validation` uses execution mode `SYNTHETIC_TMP_PATH_FIXTURE_VALIDATION_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES`. Its fixture builder requires a caller-owned temporary directory and leaves nothing outside it.

## Synthetic fixture export result

Three `FIXTUREUSDT` 15m rows covering train/val/test and UP/DOWN/FLAT were exported. Predictions come from synthetic model probabilities; neither `actual_label` nor `direction_label` is present. Stream, summary, and schema files were generated with `PREDICTION_SIDECAR_VALID`.

## Exact-byte integrity result

The summary SHA-256 equals the SHA-256 of exact stream file bytes. `size_bytes` equals the exact file byte length. Because the generated stream is LF-only, its LF-normalized hash equals its exact-byte hash.

## LF-only line ending result

The fixture JSONL contains bare LF record terminators, no CRLF sequences, and no stray CR bytes.

## Summary contract fields result

Validated fields: `hash_contract=EXACT_BYTES_AFTER_WRITE`, `line_ending_contract=LF`, `byte_size_contract=EXACT_BYTES_AFTER_WRITE`, and `writer_contract_version=ml38.10.58`.

## Schema version result

The generated schema declares `schema_version=ml38.10.58` and documents the exact-byte summary contract.

## sidecar_runtime_truth result

The fixture export records `export_completed=true` and `real_full_dataset_stream_created=true` for the synthetic fixture. Unavailable quick-quality, exit-code, timeout, and late-completion facts remain null/unknown rather than false.

## Archive status result

`NOT_REQUESTED`, `MISSING`, and `UNKNOWN` are representable. Fixture archive state is `UNKNOWN`; retention is not confirmed without ZIP creation and inspection.

## Completion status result

Completion state is `UNKNOWN_OR_EXTERNAL`; controlling-shell and Python exit codes are null. No fake exit code 0 is emitted.

## Legacy normalized-only fail-closed result

A temporary CRLF fixture whose summary hashes LF-normalized content is rejected with `SUMMARY_HASH_MATCHES_LF_NORMALIZED_NOT_EXACT_BYTES`. Exact SHA-256 and size are unchanged before and after validation; the validator does not normalize or rewrite the fixture.

## Real artifact guardrail

Validation used synthetic/tmp_path only. Source code was inspected, but existing real JSONL/summary/schema files were not read for validation, and no real artifacts were mutated; no new real sidecars or ZIP were created.

## Tests run

- authorized `py_compile`: passed;
- ML38.10.59 diagnostic tests: 6 passed;
- ML38.10.59 report tests: the first run had one literal-phrase case mismatch, then 2 passed after the report wording fix;
- seven listed regression files: 73 passed;
- direct `TrainingService` import: passed;
- `tests/test_class_weights.py --collect-only`: 1 test collected;
- `git diff --check`: passed.

### Full pytest regression result

- result: `1082 passed, 0 skipped, 1 warning`;
- exit code: `0`;
- pytest time: `80.59s`;
- wall time: `83.65s`;
- log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_59_20260706_183915.log`.

The separately approved full regression suite passed. It did not execute quick-quality, training, runtime, real sidecar generation, archive recovery, or cascade/outcome.

## Post-full-pytest confirmations

- validation remained synthetic/tmp_path only;
- exact SHA-256 and `size_bytes` match the written fixture bytes;
- fixture JSONL is LF-only and CRLF is absent;
- schema version is `ml38.10.58`;
- `hash_contract`, `line_ending_contract`, `byte_size_contract`, and `writer_contract_version` are present and valid;
- `sidecar_runtime_truth` is valid;
- archive and completion contracts are valid and no fake exit code is present;
- the legacy normalized-only fixture fails closed and remains byte-identical;
- quick-quality, training, and runtime were not run;
- no DB writes and no `ml_labels`/`ml_predictions` writes occurred;
- labels, label builders, gates, and model logic were unchanged;
- existing real artifacts were not mutated;
- no new real sidecars or ZIP were created;
- full 6481 cascade/outcome remains prohibited;
- this is not a production-like recompute and is not tradable edge.

## Safety prohibitions

The prohibited cleanup, quick-quality, fast-debug, training, runtime, DB mutation, archive recovery, ZIP packaging, and cascade/outcome operations were not invoked. In particular, quick-quality/training/runtime were not run; no `ml_labels` or `ml_predictions` writes occurred; labels, label builders, gates, and model logic were unchanged.

## Final decision

`POST_FIX_FIXTURE_VALIDATION_PASSED_NO_REAL_RUN`

- `future_writer_contract_validated_on_fixture: true`
- `newly_generated_exact_byte_valid_real_sidecar_available: false`
- `cascade_outcome_allowed_now: false`
- `production_like_recompute_allowed_now: false`
- `tradable_edge_claim_allowed_now: false`
- next allowed stage: ML38.10.60 — separately approved real SOLUSDT quick-quality re-run or no-run package/metadata validation plan.

The full 6481 cascade/outcome remains blocked. This is not a production-like recompute and is not tradable edge.
