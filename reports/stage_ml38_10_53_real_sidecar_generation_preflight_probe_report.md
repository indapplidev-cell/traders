# ML38.10.53 — Real sidecar generation preflight probe

## Scope and lineage

ML38.10.53 follows ML38.10.52 because ML38.10.52 was design-only command design. It identified the preferred future command but did not prove that the quick-quality path invoked the exporter or supplied full-dataset prediction rows. ML38.10.53 is preflight probe only: it inspects code paths and records a fail-closed readiness decision without executing quick-quality.

## Probe result

- Entrypoint status: `PASS`. `run_fv3_cached_tuning.py` supports `--quick-quality`, `--quick-quality-symbol SOLUSDT`, defaults to `15m`, constructs timestamped output below `reports/feature_regime_experiments`, and documents caller-controlled external logging.
- Sidecar wiring status: `NOT_WIRED` at the real candidate boundary. The exporter, validator, writer, reporter metadata, and compact whitelist exist, but `run_fv3_cached_tuning.py` does not reference or invoke `write_prediction_sidecar_artifacts`. Reporter/analyzer integration is metadata-only.
- Full dataset boundary status: `TEST_ONLY_BOUNDARY_RISK`. Training code builds `dataset_rows` and `split_rows` with candle timestamps, but row-level model probabilities are reduced to metrics and are not exposed as one train/val/test stream with split identity. Static inspection cannot prove a 6481-row export and the documented 973-row test-only boundary remains a concrete risk.
- Artifact path status: `PARTIAL`. The exporter defines the three `prediction_payloads/` paths and the wrapper uses timestamped run/archive names, but no caller connects those two path boundaries and no explicit sidecar overwrite refusal was found.
- Compact whitelist status: `PASS`. The full stream, summary, schema, and optional test stream are retained; raw feature dumps and credential paths are rejected.
- Source/config consistency status: `CONSISTENCY_VALIDATION_PARTIAL`. Config, model, feature, label, denominator count, join-key, and forbidden-source checks exist. Expected-value validation is incomplete for candidate/run identity, horizon, symbol, interval, and dataset-row identity.
- Readiness decision: `NOT_READY_SIDEСAR_WIRING_NOT_CONFIRMED`.
- Required next stage: **ML38.10.54 — sidecar quick-quality wiring implementation**. A real run must not be approved until that wiring and its targeted tests exist.

## Safety and non-execution

- quick-quality was not run.
- training/runtime was not run. Clean, fast-debug, and sequence commands were not run.
- DB writes were not performed.
- ml_labels/ml_predictions were not written.
- The real 6481 stream was not created and no sidecars were written to `reports/`.
- Labels, label builders, gates, and model logic were unchanged.
- Full 6481 cascade/outcome remains prohibited until a real stream exists and validates.
- There was no production-like recompute and no tradable edge was established or claimed.
- A future real quick-quality run still requires separate explicit user approval after wiring readiness is proven.

## Added files

- `app/diagnostics/real_sidecar_generation_preflight_probe.py`
- `tests/test_ml38_10_53_real_sidecar_generation_preflight_probe.py`
- `tests/test_stage_ml38_10_53_report.py`
- `reports/stage_ml38_10_53_real_sidecar_generation_preflight_probe_report.md`

## Changed files

- None. Only the diagnostic module, targeted tests, and stage report were added.

## Tests run

- The permitted `python -m py_compile` command passed.
- Targeted pytest passed: ML38.10.53 probe 8/8, ML38.10.53 report 2/2, and ML38.10.52 regression 6/6 (16 tests total). The ML38.10.53 probe was rechecked after the final importability assertion and remained 8/8 passing.
- `git diff --check` passed.
- Full pytest was not run. It requires a separate user decision after these targeted tests.
