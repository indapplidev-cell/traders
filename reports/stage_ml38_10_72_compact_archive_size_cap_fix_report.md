# ML38.10.72 Compact Archive Size-Cap Fix Report

## Decision

`COMPACT_ARCHIVE_SIZE_CAP_FIX_IMPLEMENTED_TESTED_NO_RERUN`

## ML38.10.71 Failure Summary

- Wrapper exit code: `1`.
- Child exit code: `1`.
- Failure reason: `COMPACT_PER_SYMBOL_STAGE_SIZE_CAP_EXCEEDED_AFTER_HARDENING`.
- Staged SOLUSDT output: `836.80 MB` over cap `350.00 MB`.
- ZIP was missing because compact archive creation stopped at the size guard.
- `FIELD_CONTRACT_AUDIT_PASSED`.
- Field contract version `ml38.10.69` was observed on all `291645` checked rows.
- The real run produced 45 valid streams, 45 summaries, and 45 schemas.
- Raw probabilities, calibrated probabilities, `actual_label`, unique
  `row_alignment_key`, and `prediction_layers` were present.
- Summary exact-byte hash/size validation and LF-only validation passed.
- The failure was a compact archive size-budget failure, not a prediction
  sidecar field-contract failure.

## Read-Only Size Diagnosis

The ML38.10.71 output directory was inspected read-only. No existing artifact
was normalized, rewritten, deleted, or regenerated.

- Total output size: `877456882` bytes, `836.81 MB`.
- 45 `full_dataset_prediction_stream.jsonl` files: `816931357` bytes,
  `779.09 MB`.
- 45 stream summaries: `300216` bytes, `0.29 MB`.
- 45 schemas: `399735` bytes, `0.38 MB`.
- Other JSON/Markdown/log content: approximately `57.72 MB`.
- Estimated archive-included size without full JSONL streams, retaining
  summary/schema and adding bounded manifests: approximately `58.39 MB`.
- The largest individual files were full-dataset prediction streams, each
  approximately `16.77 MB` to `17.72 MB`.

## Failure Source

- Compact per-symbol staging and the `350.00 MB` check are in
  `run_fv3_cached_tuning.py`, method
  `_compact_prune_staged_symbol_output`.
- The exact exception was raised after `compact_staged_symbol_output` when all
  staged files, including the 45 full JSONL streams, were counted.
- Archive hardening is implemented in
  `app/experiments/compact_archive_pruner.py`.
- Existing whitelist behavior byte-preserved full prediction sidecar streams,
  which made them archive candidates and caused the aggregate cap failure after
  the expanded `ml38.10.69` row contract increased stream bytes.

## Implemented Fix

Policy:
`COMPACT_ARCHIVE_MANIFEST_ONLY_LARGE_SIDECAR_STREAMS`

Policy version: `ml38.10.72`.

When compact archive-included size exceeds the unchanged `350.00 MB` cap:

1. Each full prediction stream is verified against its summary exact SHA-256
   and exact byte size.
2. The stream LF-only contract, row count, schema version, and prediction field
   contract version are validated.
3. Summary and schema remain included.
4. A bounded `prediction_sidecar_stream_manifest.json` is created.
5. The full JSONL stream remains available in `output_dir`.
6. The full JSONL stream is omitted only from compact archive members.
7. Archive metadata records manifest-only compaction counts and policy version.

Small streams remain included normally when the archive-included size is below
the cap. The cap was not raised.

## Fail-Closed Behavior

Manifest-only compaction fails closed for:

- missing stream when a summary exists;
- missing summary;
- missing schema;
- summary SHA-256 mismatch;
- summary byte-size mismatch;
- invalid or missing row count;
- missing schema or field-contract version;
- non-LF stream bytes;
- duplicate manifest path;
- final archive-included size still above cap after manifest-only compaction.

There is no silent dropping: an omitted stream requires a valid, versioned
manifest that states `full_stream_in_compact_archive=false` and
`full_stream_available_in_output_dir=true`.

## Guardrails

- No rerun, wrapper, quick-quality, fast-debug, sequence, runtime training, or
  full multi-symbol training was run.
- `run_fv3_cached_tuning.py` was not executed.
- No DB-mutating command was run.
- No manual `ml_labels` or `ml_predictions` write was performed.
- Labels, label builders, gates, model training logic, class weights, training
  objective, and production calibration policy were not changed.
- `directional_confidence_floor 0.60` was not implemented.
- Flat override was not implemented.
- h08 remains separate and was not fixed.
- Existing ML38.10.71 real artifacts were not mutated.
- No archive recovery was performed.
- No new real sidecars or ZIP were created.
- Cascade/outcome remains blocked.
- No production-like recompute or tradable edge is claimed.
- No commit, planning update, or snapshot was performed.

## Tests

- Python compilation passed for
  `app/experiments/compact_archive_pruner.py`,
  `app/reporting/compact_report.py`, and `run_fv3_cached_tuning.py`.
- ML38.10.72 targeted tests: `11 passed`.
- Existing compact archive hardening tests: `5 passed`.
- Stage report tests before full pytest: `2 passed`.
- ML38.10.69 field-contract regression: `18 passed`.
- ML38.10.70 rerun-readiness regression: `7 passed`.
- ML38.10.55/59/58 regressions: `25 passed`.
- Wrapper safety read-only grep confirmed the existing acknowledgement flag,
  `--execute` guard, SOLUSDT quick-quality command, and
  `run_fv3_cached_tuning.py` reference were unchanged.
- `TrainingService` import passed:
  `TrainingService import OK: TrainingService`.
- `test_class_weights.py --collect-only`: `1 test collected`.
- `git diff --check`: passed; only Git LF-to-CRLF working-copy warnings were
  reported.
- Full pytest: `1182 passed`, `0 skipped`, no warning summary.
- Full pytest exit code: `0`.
- Pytest execution time: `132.86 seconds`.
- Full pytest wall time: `136.9296693 seconds`.
- Full pytest log:
  `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_72_20260708_180249.log`.
- Final report test after full pytest: `2 passed`.

## Next Stage

Recommended only after separate approval:

`ML38.10.73 - separately approved SOLUSDT quick-quality rerun after compact archive fix`

This report does not authorize that rerun.
