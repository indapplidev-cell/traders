# ML38.10.51 — Sidecar Exporter Fixture/Dry-run Audit

## Scope and lineage

This stage follows ML38.10.50. ML38.10.50 implemented the exporter, validator, and compact whitelist, plus sidecar schema/writers and reporter/analyzer metadata, but did not execute real generation. ML38.10.51 is fixture/dry-run only and checks that implementation with deterministic synthetic prediction rows.

## Fixture audit evidence

- The JSONL stream, summary JSON, and schema JSON were created only in pytest tmp_path; no fixture artifact was written to `reports/`.
- The valid fixture stream passed validation. Duplicate keys, missing or invalid predicted labels, forbidden sources, probability errors, and config/feature/label mismatches failed closed.
- Summary evidence includes row count, split counts, denominator scope, byte size, and SHA-256.
- Compact whitelist was checked with fixture paths: stream, summary, schema, and test stream are retained; arbitrary raw feature and credential paths are rejected.
- Actual labels and ml_labels.direction_label are forbidden as predictions. Synthetic actual labels were included only as target fields.

## Safety and non-execution

- The real 6481 stream was not created.
- Quick-quality, training, and runtime were not run. Clean, fast-debug, and sequence commands were not run.
- No database writes were performed. ml_labels and ml_predictions were not written.
- Labels, label builders, gates, and model logic were unchanged.
- Full 6481 cascade/outcome remains prohibited until a separately approved real stream exists and validates.
- This stage performs no production-like recompute and establishes no tradable edge.
- Any real generation or quick-quality rerun requires separate user approval.

## Added files

- `app/diagnostics/sidecar_exporter_fixture_audit.py`
- `tests/test_ml38_10_51_sidecar_exporter_fixture_audit.py`
- `tests/test_stage_ml38_10_51_report.py`
- `reports/stage_ml38_10_51_sidecar_exporter_fixture_audit_report.md`

## Changed files

- None outside the added diagnostic-only module, tests, and stage report.

## Tests run

- Permitted `python -m py_compile ...`: passed.
- `python -m pytest tests/test_ml38_10_51_sidecar_exporter_fixture_audit.py`: 8 passed.
- `python -m pytest tests/test_stage_ml38_10_51_report.py`: 1 passed.
- `python -m pytest tests/test_ml38_10_50_prediction_sidecar_exporter.py`: 11 passed.
- `git diff --check`: passed.
- Full pytest requires separate approval and was not run during the targeted-check phase.
