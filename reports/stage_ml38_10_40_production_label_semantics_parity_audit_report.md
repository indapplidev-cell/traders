# ML38.10.40 — production label semantics parity audit

## Reason and scope

ML38.10.39 produced a read-only board where all 96 rows were `TOO_NOISY`, with roughly 1-9% FLAT and 91-99% directional labels. This contradicts the quick-quality production reference of FLAT about 92% and about 8% directional. The sensitivity board is therefore not actionable until production semantics and denominator parity are proven.

The audit identifies that ML38.10.39 uses an independent upper/lower ATR first-touch plus terminal-boundary rule, while production supports selectable future-close/first-touch/setup-aware modes, direction ATR thresholds, setup and entry-path masks, opportunity qualification, and regime-specific threshold overrides.

## Diagnostic blocks added

- `production_label_semantics_parity_audit`
- `label_recompute_semantics_gap_board`
- `current_config_mapping_audit`
- `ml38_10_40_parity_decision`

The config-name parser recovers h12, tts, thr065, sqmask060, epq070, sp045, and recovery-guard hints, but deliberately reports `CURRENT_CONFIG_MAPPING_INCOMPLETE` while TP/SL, denominator, and regime mappings remain unavailable.

## Files changed

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Tests added

- `tests/test_ml38_10_40_production_label_semantics_parity_audit.py`
- `tests/test_stage_ml38_10_40_report.py`

## Verification

- `python -m py_compile`: passed for the six authorized files.
- `python -m pytest tests/test_ml38_10_40_production_label_semantics_parity_audit.py`: passed, 7 tests.
- `python -m pytest tests/test_stage_ml38_10_40_report.py`: passed, 1 test.
- Full pytest: not run; user approval is required after targeted tests.

## Prohibition and safety confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- database writes were not performed.
- ml_labels were not written.
- labels, label builders, gates, and model logic were not changed.
- no runtime config was added.
- live trading and auto-activation were not changed.
- no runtime JSON, ZIP, or log artifact was created or staged.
