# ML38.10.62 — real SOLUSDT quick-quality wrapper execution audit

The user explicitly approved ML38.10.62. The single real run used `run_solusdt_quick_quality_once.py`; `run_fv3_cached_tuning.py` was not invoked directly.

## Wrapper execution evidence

- Exact child command: `python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT`
- External log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\solusdt_quick_quality_20260707_065819.log`
- Completion marker: `D:\disk_E\game_projects\traders\traders-ml-run-logs\solusdt_quick_quality_20260707_065819.completion.json`
- Start local: `2026-07-07T06:58:19.531649+03:00`
- End local: `2026-07-07T10:40:14.575345+03:00`
- Elapsed: `13315.047` seconds
- Wrapper exit code: `1`
- Child exit code: `1`

The run trained only SOLUSDT at 15m. It did not run BTC, ETH, a multi-symbol symbol set, clean, fast-debug, sequence, cascade, or outcome. The wrapper child failed during its downstream single-symbol invocation of the multi-symbol analysis implementation: `TypeError: unhashable type: 'dict'`. No repair or rerun was attempted.

## Output and sidecar evidence

- Output directory: `reports/feature_regime_experiments/quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260707_035826`
- Discovery: 45 complete sidecar sets
- Latest stream: `per_symbol_experiments/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826/label_grid_runtime/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826_label_grid/pipeline_runs/fv3_cached_fresh_tuning_solusdt_15m_20260707_035826_label_grid_lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe/prediction_payloads/full_dataset_prediction_stream.jsonl`
- Latest summary: same directory, `full_dataset_prediction_stream_summary.json`
- Latest schema: same directory, `prediction_payload_schema.json`
- Stream size: `6973344` bytes
- SHA-256: `e38b71d1cf862991c57a99479692a6e084d51f44fed7bc9c0778b945d3e1c337`

## Validation results

- Exact SHA/size: `EXACT_BYTE_VALID`; file and summary both report SHA-256 `e38b...c337` and size `6973344`.
- Line endings: `LF_ONLY_VALID`; 6481 bare LF, 0 CRLF, 0 stray CR.
- Schema contract: valid `ml38.10.58`; required fields present.
- Summary contract: valid `EXACT_BYTES_AFTER_WRITE`, `LF`, writer `ml38.10.58`.
- Runtime truth: `RUNTIME_TRUTH_VALID`; export requested/completed and real stream created. Unknown completion facts remain null rather than false. Stale pre-run `WIRED_NOT_EXECUTED` false/false metadata was detected separately and was not treated as runtime truth.
- Completion evidence: `COMPLETION_EVIDENCE_VALID`; marker/log and both nonzero codes are known, with no fake zero or short-timeout loss.
- Archive/ZIP: `ARCHIVE_VALID`; wrapper-created ZIP is `24985558` bytes and contains 45 streams, 45 summaries, and 45 schemas. No recovery or manual ZIP recreation occurred.
- Label substitution: `NO_LABEL_SUBSTITUTION_DETECTED`; all 6481 latest-stream rows use `training_service_calibrated_model_softmax_argmax`, with no actual label payload or `ml_labels.direction_label` prediction source.

## Decision gate

Final decision remains `WRAPPER_EXECUTION_FAILED`. The fail-closed reason is wrapper/child exit code `1 / 1` and `TypeError: unhashable type: 'dict'` in downstream analysis. Durable failure evidence is valid and useful, and generated sidecars validate independently, but the nonzero exit codes prevent promotion. Therefore cascade/outcome remains blocked, production-like recompute remains blocked, and any tradable edge claim remains blocked. No live trading or automatic activation occurred.

Explicitly: cascade/outcome was not run and remains blocked; production-like recompute is not claimed; tradable edge is not claimed.

The TypeError was not fixed in this stage. The wrapper and quick-quality were not restarted after the failure.

## Full pytest

- Result: `1103 passed, 0 skipped, 1 warning`
- Exit code: `0`
- Pytest time: `103.61s`
- Wall time: `107.247s`
- External pytest log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_62_20260707_105312.log`

The successful full test suite does not override the fail-closed execution result. Sidecar validation remains exact-byte valid and LF-only valid; schema `ml38.10.58`, summary contract, runtime truth, completion evidence, and ZIP/archive validation remain valid; no label substitution was detected. Cascade/outcome, production-like recompute, and tradable edge claims remain blocked by wrapper/child exit code `1 / 1`.

## Recommended next stage

After the planning update and ML38.10.62 snapshot, the recommended next stage is `ML38.10.63 — no-run TypeError root-cause diagnostic / downstream analyzer fail-closed audit`.

No runtime artifacts, JSON, ZIP, or external logs are intended for commit. No existing artifacts were normalized, regenerated, recovered, or deleted.
