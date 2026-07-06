# ML38.10.56 — real quick-quality sidecar generation validation audit

## Why this stage follows ML38.10.55

ML38.10.55 ended at `READY_FOR_SEPARATELY_APPROVED_REAL_QUICK_QUALITY_RUN`. The separately approved run was then executed once, so ML38.10.56 validates the resulting real artifacts read-only. It does not rerun quick-quality, training, runtime, packaging, cascade, or outcome logic.

Approved command:

`python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT`

Scope reported by the run operator: one SOLUSDT 15m invocation; no BTC/ETH or multi-symbol invocation.

## Run completion audit

- Controlling shell exit code 124 was caused by its 3604-second timeout.
- The Python exit code was lost; it is not recoverable from the controlling shell result.
- The child process continued and completed later.
- Observed elapsed time was approximately 3h22m (12:33:52–15:56 local observation window).
- Status: `COMPLETED_WITH_LOST_PYTHON_EXIT_CODE`.
- This blocks production-like and tradable-edge claims.

External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\real_quick_quality_solusdt_ml38_10_55_20260706_123352.log`

## Artifact discovery and inventory

Output directory:

`reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260706_093359`

- Output directory exists.
- 45 `full_dataset_prediction_stream.jsonl` files were found.
- 45 `full_dataset_prediction_stream_summary.json` files were found.
- 45 `prediction_payload_schema.json` files were found.
- Complete sidecar sets: 45; incomplete sets: 0.
- Summaries reporting `PREDICTION_SIDECAR_VALID`: 45; other/unreadable summaries: 0.
- Artifact discovery status: `SIDECARS_FOUND_ZIP_MISSING`.
- No new ZIP for this run was found.
- Old ZIP noted: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260704_121830.zip`.
- Archive status: `ZIP_MISSING_FOR_REAL_RUN`; compact archive retention cannot be confirmed for this run.

The latest selected set is the `lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe` candidate under its `prediction_payloads` directory.

## Latest summary contract

- `validation_status`: `PREDICTION_SIDECAR_VALID`
- schema version: `ml38.10.50`
- denominator: `FULL_DATASET_6481`
- row count / expected row count: 6481 / 6481
- splits: train 4536, val 972, test 973
- predicted-label distribution: DOWN 3170, FLAT 117, UP 3194; sum 6481
- summary SHA-256: `e6e1252ef26fe493dc3e18d7304144b1041eae7d314756a83578f4c8a27115e8`
- summary size: 6,973,344 bytes
- source: `training_service_calibrated_model_softmax_argmax`
- identity: SOLUSDT 15m, horizon 12, `fv4_book_setup_context`, `lv36_h12_metric_relax_suppress_short_exit45`
- all summary `config_consistency.matches` values are true
- `stream_sha256` is absent; legacy `sha256` is accepted as a field-level compatibility path (`SUMMARY_SHA_FIELD_COMPATIBILITY_NOTE`), but it must still match the actual file bytes.

Summary contract status: `LATEST_SIDECAR_SUMMARY_VALID`.

## JSONL integrity audit

- File exists and contains exactly 6481 valid JSON objects.
- Required fields are present in every row.
- `(symbol, interval, candle_open_time)` keys are unique.
- Computed splits match train 4536, val 972, test 973.
- Labels are restricted to UP/DOWN/FLAT.
- Probabilities are finite, bounded, and sum sanely.
- Model-softmax-argmax source stage is consistent.
- No `actual_label`, `ml_labels.direction_label`, or `target_label` prediction source was detected.
- Actual file SHA-256: `bda3316c2aef1d2ffccaac096039945e6d69e93541bb608ac8d57620145e17c9`.
- Actual file size: 6,979,825 bytes.
- The file contains 6481 CRLF separators. Replacing CRLF with LF yields 6,973,344 bytes and SHA-256 `e6e125...`, exactly the values recorded in the summary.
- Therefore the summary describes LF-normalized content, not the actual Windows file bytes. The required actual-file hash and size checks fail closed.

JSONL status: `JSONL_INTEGRITY_FAILED` (`STREAM_SHA256_MISMATCH_DETECTED`, `STREAM_SIZE_MISMATCH_DETECTED`). No full JSONL content was printed.

## Schema and configuration

- Schema status: `SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED`.
- All required sidecar fields are in the schema required list.
- Config status: `CONFIG_CONSISTENCY_CONFIRMED`.
- No lv36/lv31 mix or fv4/fv3 mix was found; symbol, interval, and horizon match SOLUSDT, 15m, and 12.

## Metadata staleness

Real sidecars exist, while the latest summary metadata still reports:

- `implementation_status = WIRED_NOT_EXECUTED`
- `real_quick_quality_run_executed = false`
- `real_full_dataset_stream_created = false`

Status: `SIDECAR_METADATA_STALE_BUT_ARTIFACT_VALIDATION_PASSED`; severity MEDIUM. Here “artifact validation passed” refers to existence/summary contract detection only; the independent actual-byte JSONL hash validation failed. Required follow-up: ML38.10.57 metadata truth update/runtime execution metadata fix.

## Decision gate

Final gate: `REAL_SIDECAR_STREAM_VALIDATION_FAILED`.

The intended incomplete-package decision cannot be granted because the actual JSONL SHA-256 and byte size do not match its summary. Independently, the new ZIP is missing, the Python exit code is unconfirmed, and metadata truth is stale.

Next allowed stage: ML38.10.57 — real run metadata/archive completion audit, including resolution of the on-disk CRLF versus summarized LF hash/size contract. Packaging recovery may be considered only if separately reviewed and safe; it was not performed here.

## Safety prohibitions retained

- no cascade/outcome
- no production-like recompute
- no tradable edge
- no labels/gates/model changes
- no DB-mutating commands
- no writes to `ml_labels` or `ml_predictions`
- quick-quality was not run again
- no training/runtime was run by this audit
- no sidecars or archives were created, changed, deleted, or packaged

## Files

Added files:

- `app/diagnostics/real_quick_quality_sidecar_validation_audit.py`
- `tests/test_ml38_10_56_real_quick_quality_sidecar_validation_audit.py`
- `tests/test_stage_ml38_10_56_report.py`
- `reports/stage_ml38_10_56_real_quick_quality_sidecar_validation_audit_report.md`

No pre-existing production, model, label, gate, runtime, or report artifact file was changed.

## Checks

- `python -m py_compile app/diagnostics/real_quick_quality_sidecar_validation_audit.py`: passed.
- `python -m pytest tests/test_ml38_10_56_real_quick_quality_sidecar_validation_audit.py`: 7 passed.
- `python -m pytest tests/test_stage_ml38_10_56_report.py`: 2 passed.
- `git diff --check`: passed.
- Full pytest: 1054 passed, 0 skipped, 1 warning.
- Full pytest exit code: 0.
- Full pytest time: 82.52s.
- Full pytest log (external, not committed): `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_56_20260706_161652.log`.

## Final stage status after full regression suite

- Final decision: `REAL_SIDECAR_STREAM_VALIDATION_FAILED`.
- Blocker: actual JSONL SHA/size mismatch with summary SHA/size.
- Likely cause: CRLF/LF contract mismatch; the actual stream contains 6481 CRLF rows while the summary matches LF-normalized content.
- JSONL status: `JSONL_INTEGRITY_FAILED`.
- Schema status: `SCHEMA_PRESENT_REQUIRED_FIELDS_CONFIRMED`.
- Config status: `CONFIG_CONSISTENCY_CONFIRMED`.
- Metadata staleness: `WIRED_NOT_EXECUTED` / `real_quick_quality_run_executed=false` / `real_full_dataset_stream_created=false`.
- Archive status: `ZIP_MISSING_FOR_REAL_RUN`.
- The real 6481-row stream exists but is not accepted as integrity-confirmed because its actual SHA/size does not match the summary.
- Next allowed stage: ML38.10.57 metadata/archive and CRLF/LF contract audit.
- Quick-quality, training, and runtime were not rerun.
- DB writes were not performed; `ml_labels` and `ml_predictions` were not written.
- Labels, label builders, gates, and model logic remain unchanged.
- No new sidecars were created by this audit or by the full pytest run.
- Full 6481 cascade/outcome remains prohibited.
- This stage is not a production-like recompute and does not establish tradable edge.
