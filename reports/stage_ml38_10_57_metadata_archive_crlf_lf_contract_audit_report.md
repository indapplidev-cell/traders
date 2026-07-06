# ML38.10.57 metadata/archive and CRLF/LF contract audit

## Why this stage follows ML38.10.56

ML38.10.56 ended fail-closed with `REAL_SIDECAR_STREAM_VALIDATION_FAILED` and `JSONL_INTEGRITY_FAILED`. The real 6481-row stream exists and is structurally valid, but its exact on-disk SHA-256 and size do not match the summary. This audit determines whether newline conversion explains the mismatch and traces the associated metadata, archive, and timeout contracts. It does not repair or regenerate runtime artifacts.

Previous closed commit: `b72b962232b397d4f254199997eb9082ea4643b0`.

## Execution and selected real artifacts

- Mode: `READ_ONLY_METADATA_ARCHIVE_CRLF_LF_CONTRACT_AUDIT_NO_QUICK_QUALITY_NO_TRAINING_NO_DB_WRITES`.
- Output directory: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260706_093359`.
- Selected sidecar folder: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260706_093359/per_symbol_experiments/fv3_cached_fresh_tuning_solusdt_15m_20260706_093359/label_grid_runtime/fv3_cached_fresh_tuning_solusdt_15m_20260706_093359_label_grid/pipeline_runs/fv3_cached_fresh_tuning_solusdt_15m_20260706_093359_label_grid_lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe/prediction_payloads`.
- Selection reason: latest selected sidecar from the ML38.10.56 deep audit.
- Stream, summary, and schema all exist.
- Real artifacts were read only and were not normalized, rewritten, repackaged, deleted, or otherwise mutated.

## CRLF/LF contract blocker

Selected `full_dataset_prediction_stream.jsonl`:

- summary SHA-256: `e6e1252ef26fe493dc3e18d7304144b1041eae7d314756a83578f4c8a27115e8`
- exact file SHA-256: `bda3316c2aef1d2ffccaac096039945e6d69e93541bb608ac8d57620145e17c9`
- LF-normalized SHA-256: `e6e1252ef26fe493dc3e18d7304144b1041eae7d314756a83578f4c8a27115e8`
- summary size: 6,973,344 bytes
- exact file size: 6,979,825 bytes
- LF-normalized size: 6,973,344 bytes
- CRLF count: 6481
- total LF bytes: 6481
- bare LF count: 0
- row count: 6481; it matches the summary
- exact hash/size match: false
- LF-normalized hash/size match: true

Status: `SUMMARY_HASHES_LF_NORMALIZED_CONTENT_WHILE_FILE_IS_CRLF`. The CRLF/LF root cause is confirmed, not merely suspected.

## All 45 sidecar sets

- total sets: 45
- sets matching exact file bytes: 0
- sets matching LF-normalized bytes only: 45
- sets failing both comparisons: 0
- uniform contract observed: true
- aggregate: `ALL_SETS_SUMMARY_MATCH_LF_NORMALIZED_ONLY`

Every summary/stream pair was hashed read-only. No stream content was printed or changed.

## Summary hash source audit

`app/experiments/prediction_sidecar_exporter.py` builds canonical JSONL text with an LF appended to every row. `build_prediction_sidecar_summary` encodes that in-memory text as UTF-8 and computes `sha256(encoded)` and `len(encoded)` before the file is written.

The stream is then written with `Path.write_text(..., encoding="utf-8")`. Encoding is explicit, but `newline` is not. On Windows, text-mode newline translation writes the LF text as CRLF. The writer does not re-read or re-hash the exact file bytes after writing.

- summary hash source: `IN_MEMORY_LF_TEXT`
- size source: `IN_MEMORY_LF_TEXT_SIZE`
- disk behavior: `PLATFORM_DEFAULT_NEWLINE_CONVERSION_RISK`
- root cause: `CRLF_LF_CONTRACT_ROOT_CAUSE_CONFIRMED`

## JSONL writer contract audit

Neither the summary nor schema declares whether `sha256` and `size_bytes` cover exact file bytes or normalized logical content. No separate normalized hash field exists. The current writer is not cross-platform safe for an exact-byte interpretation.

Recommended future contract: `EXACT_BYTES_HASH_AND_SIZE_AFTER_WRITE`. An alternative is to declare normalized LF SHA separately from exact file SHA/size. Status: `WRITER_CONTRACT_AUDITED_FIX_REQUIRED_NOT_APPLIED`.

## Metadata truth audit

The runtime export path in `training_service.py` calls `write_full_dataset_prediction_sidecar_for_candidate`. That function embeds `build_sidecar_wiring_metadata()` unchanged. The builder is static implementation-stage metadata with:

- `implementation_status = WIRED_NOT_EXECUTED`
- `real_quick_quality_run_executed = false`
- `real_full_dataset_stream_created = false`

The export path never replaces those values with runtime truth and does not add post-write validation or exit-code state. Static wiring metadata was therefore reused in real runtime artifacts.

Status: `METADATA_TRUTH_CONTRACT_AUDITED_FIX_REQUIRED_NOT_APPLIED`. Future runtime metadata should separate static wiring state from execution state and record `EXECUTED_REAL_QUICK_QUALITY`, real command execution, post-existence stream creation, validation result, and `LOST_DUE_TIMEOUT` where applicable.

## Archive packaging audit

- output directory exists: true
- new run ZIP exists: false
- old ZIP `quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260704_121830.zip` exists: true
- wrapper archive step exists: true (`_finalize_archive` and `zipfile.ZipFile`)
- compact whitelist contains the stream, summary, and schema paths: true
- archive step likely not reached after timeout: true
- recovery without quick-quality rerun is technically possible from existing output, but requires a separately approved packaging-recovery design and verification

The wrapper performs staging and analysis before `_finalize_archive`; the current log stops at symbol launch and contains no archive marker. Status: `ARCHIVE_PACKAGE_MISSING_CAUSE_AUDITED_FIX_REQUIRED_NOT_APPLIED`. No ZIP was recreated in this stage.

## Timeout and lost exit-code audit

- controlling shell exit code: 124
- timeout wrapper limit: 3604 seconds
- Python exit code lost: true
- child completed later: true, based on the completed sidecar set timestamps and ML38.10.56 evidence
- run log exists: true
- success marker in log tail: false
- archive marker in log tail: false
- exception marker in log tail: false

Status: `TIMEOUT_LOST_EXIT_CODE_AUDITED`. Exit 124 describes the controlling timeout, not the Python child result; the Python result cannot be reconstructed from the log.

## Risk board

Fail-closed handling remains required for exact-byte mismatch across OS newline modes, a summary that reports valid while exact-byte checks fail, stale execution metadata, missing compact ZIP, lost Python exit status, premature acceptance of partial artifacts, cascade/outcome before integrity repair, and production-like or tradable-edge claims before package completion. Each blocks cascade and production-like claims; the integrity and premature-downstream risks are critical.

## Fix plan not applied

ML38.10.58 should design, review, and test the following without mutating the existing real artifacts:

- Write JSONL with explicit LF (`newline="\n"`) or binary exact bytes and compute SHA/size from exact bytes after write; alternatively store explicit normalized and exact hashes separately.
- Update the summary schema version if fields or semantics change.
- Separate runtime execution truth from static wiring metadata; set execution true when the command actually runs and stream-created true only after files exist.
- Recover packaging from the existing completed output only with separate approval, without rerunning quick-quality, and verify the ZIP contains all sidecar paths.
- Ensure the parent timeout exceeds the child run, capture the child exit code, and write an unambiguous completion marker.

Fixes applied now: false. Real artifact mutation now: false.

## Decision gate

- CRLF/LF root cause confirmed: true
- summary normalized-hash contract confirmed empirically: true
- metadata staleness confirmed: true
- ZIP missing confirmed: true
- timeout/lost-exit-code issue confirmed: true
- decision: `CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED`
- next allowed stage: `ML38.10.58 — sidecar writer metadata/archive contract fix design/implementation plan`
- cascade/outcome allowed now: false
- production-like recompute allowed now: false
- tradable-edge claim allowed now: false

The stream remains structurally valid but exact-byte integrity is not accepted under the current summary contract.

## Safety prohibitions retained

- no quick-quality, fast-debug, clean sequence, training, runtime, cascade, or outcome execution
- no production-like recompute and no tradable-edge claim
- no DB-mutating commands and no writes to `ml_labels` or `ml_predictions`
- no changes to labels, label builders, gates, or model logic
- no mutation, normalization, recreation, deletion, or packaging of real artifacts
- no new sidecars created
- no use of actual labels as predicted labels

## Files

Changed existing files: none.

Added files:

- `app/diagnostics/metadata_archive_crlf_lf_contract_audit.py`
- `tests/test_ml38_10_57_metadata_archive_crlf_lf_contract_audit.py`
- `tests/test_stage_ml38_10_57_report.py`
- `reports/stage_ml38_10_57_metadata_archive_crlf_lf_contract_audit_report.md`

## Checks

- `python -m py_compile app/diagnostics/metadata_archive_crlf_lf_contract_audit.py`: passed.
- `python -m pytest tests/test_ml38_10_57_metadata_archive_crlf_lf_contract_audit.py`: 8 passed.
- `python -m pytest tests/test_stage_ml38_10_57_report.py`: 2 passed.
- `git diff --check`: passed.
- Full pytest: 1064 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Full pytest time: 83.39s.
- Full pytest wall time: 86.86s.
- Full pytest log (external, not committed): `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_57_20260706_172117.log`.

## Final status after full regression suite

- Final status: `CRLF_LF_CONTRACT_CONFIRMED_FIX_REQUIRED`.
- The summary matches LF-normalized bytes, not exact file bytes; exact file SHA-256 and size remain different from the summary.
- All 45 sidecar sets are LF-normalized-only: 0 exact-byte matches, 45 LF-normalized-only matches, 0 failures of both comparisons.
- The selected 6481-row stream remains structurally valid, but exact-byte integrity is not confirmed.
- Metadata staleness is confirmed: `WIRED_NOT_EXECUTED`, `real_quick_quality_run_executed=false`, and `real_full_dataset_stream_created=false`.
- Missing ZIP is confirmed.
- Shell timeout and lost Python exit code are confirmed.
- The fix plan is documented but was not applied.
- Recommended future contract: `EXACT_BYTES_HASH_AND_SIZE_AFTER_WRITE`.
- Quick-quality, training, and runtime were not rerun.
- DB-mutating commands were not run; `ml_labels` and `ml_predictions` were not written.
- Labels, label builders, gates, and model logic remain unchanged.
- Real artifacts were not mutated and no new sidecars were created.
- Full 6481 cascade/outcome remains prohibited.
- This stage is not a production-like recompute and does not establish tradable edge.
- Next allowed stage: `ML38.10.58 — sidecar writer metadata/archive contract fix design/implementation plan`.
