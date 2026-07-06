# ML38.10.52 — Real sidecar generation command design report

## Purpose and sequence

ML38.10.52 follows ML38.10.51 because the implementation and synthetic evidence are complete, but the real generation boundary is not yet approved or proven. ML38.10.50 implemented the prediction sidecar exporter, validator, schema, writer, and compact whitelist. ML38.10.51 passed the fixture/dry-run audit on six synthetic rows, including fail-closed and whitelist checks, without creating sidecars under `reports/`.

This stage is design-only. It defines a future real quick-quality sidecar generation command, preflight checks, expected artifacts, fail-closed source/config consistency, post-run validation, rollback behavior, and approval gates. It does not execute the command.

## Command design status

Preferred future command after separate explicit user approval:

```text
python run_fv3_cached_tuning.py --quick-quality --quick-quality-symbol SOLUSDT
```

The quick-quality entry point and SOLUSDT selector are supported by current code, but current source inspection does not guarantee that this path invokes the sidecar exporter. The candidate is therefore `partial`, requires a preflight wiring probe, and is not allowed now. A future explicit `--export-prediction-sidecar` command and a validation-only CLI are also recorded as unsupported design candidates requiring new wiring.

## Preflight and artifact contract

The future preflight requires a clean git status, recorded branch and commit, no uncommitted code, no planned DB/ml_labels/ml_predictions writes, SOLUSDT only, expected 15m interval, a unique non-overwriting output directory, importable exporter, available compact whitelist, enabled source/config validation, declared sidecar paths, passing tests, logs outside the repository, and explicit user approval.

Expected sidecars below the unique approved run directory are:

- `prediction_payloads/full_dataset_prediction_stream.jsonl`
- `prediction_payloads/full_dataset_prediction_stream_summary.json`
- `prediction_payloads/prediction_payload_schema.json`
- archive manifest entries and checksums for the retained sidecars

The expected denominator is `FULL_DATASET_6481`; actual row count must match `split_total_rows`, with unique `symbol+interval+candle_open_time` keys.

## Source/config consistency

The ML38.10.49 warning is handled explicitly: snapshot evidence had an lv36 probability payload versus an lv31 reference config and fv4 feature metadata versus prior fv3 candidate metadata. ML38.10.52 sets `mismatch_policy: FAIL_CLOSED`. It forbids silent cross-candidate mixing, treating the test-only 973 predictions as the full 6481 stream, and using `ml_labels.direction_label` or any actual label as `predicted_label`.

## Post-run validation and failure handling

After a future approved run, ML38.10.53 must locate the exact approved run, locate sidecars, validate JSONL count and unique keys, reconcile split counts, validate label domain and probabilities, verify config/model/feature/label provenance, reject actual-label substitution, verify compact ZIP retention and checksums, and confirm that no DB/ml_labels/ml_predictions writes occurred. Every failed check blocks the next stage.

Missing or incomplete artifacts, count/key/schema/probability/config violations, archive omissions, unexpected DB writes, actual-label substitution, or runtime failure all fail closed. Incomplete runtime artifacts must not be committed. Cleanup is limited to the uniquely identified failed-run output after review; prior reports and DB rows must not be modified. A retry requires root-cause review and fresh approval.

## Approval gate and safety record

- This stage does not allow a real run; real quick-quality generation requires separate explicit user approval.
- quick-quality was not run.
- training/runtime was not run; clean, fast-debug, and sequence commands were not run.
- DB writes were not performed.
- ml_labels and ml_predictions were not written.
- The real 6481 stream was not created.
- Labels, label builders, gates, and model logic were unchanged.
- The full 6481 cascade/outcome remains prohibited until a real stream exists and validates.
- There was no production-like recompute and no tradable edge was established or claimed.

After an approved generation, the required next stage is **ML38.10.53 — real sidecar generation validation audit**.

## Changed and added files

Added files:

- `app/diagnostics/real_sidecar_generation_command_design.py`
- `tests/test_ml38_10_52_real_sidecar_generation_command_design.py`
- `tests/test_stage_ml38_10_52_report.py`
- `reports/stage_ml38_10_52_real_sidecar_generation_command_design_report.md`

No existing source, label, label-builder, gate, model-logic, or runtime artifact file was changed.

## Tests run

- `python -m py_compile` on the explicitly allowed modules — passed.
- targeted pytest for ML38.10.52 design, ML38.10.52 report, and ML38.10.51 regression — 16 passed (after correcting one report wording assertion).
- `git diff --check` — recorded after the targeted tests.
- Full pytest was not run; user approval is required after targeted tests.
