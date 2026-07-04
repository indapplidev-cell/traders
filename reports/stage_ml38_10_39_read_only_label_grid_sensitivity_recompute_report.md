# ML38.10.39 — read-only label-grid sensitivity recompute

## Reason and scope

ML38.10.38 established that the current SOLUSDT 15m labels are too FLAT-heavy, but the compact ZIP lacks timestamp-level forward candle paths and ATR-at-entry values. It therefore cannot recompute alternative label distributions. ML38.10.39 adds a diagnostic-only, read-only in-memory recompute over candle data without invoking training or persisting labels.

## Diagnostic implementation

- Added `read_only_label_grid_sensitivity_recompute`.
- Added a read-only candle loader supporting an injected PostgreSQL repository or JSON/JSONL/CSV cache.
- Added pure forward-path labeling, distribution calculation, row classification, sensitivity-board construction, and top-level decision construction.
- The conservative diagnostic semantics use first upper/lower ATR-threshold touch; same-candle dual touch is ambiguous FLAT. If neither threshold is touched, terminal ATR movement must exceed the neutral boundary.

Supported grid:

- horizons: h8 / h12 / h16 / h24
- TP/SL pairs: 0.6/0.6, 0.8/0.8, 1.0/1.0, 1.2/1.2, 1.5/1.0, 1.0/1.5
- flat boundaries: 0.10 / 0.20 / 0.30 / 0.40

Verdicts are conservative: samples below 100 are marked `DIRECTIONAL_SAMPLE_TOO_SMALL`; FLAT above 85% is `TOO_FLAT` once sample size is sufficient; FLAT below 50% is `TOO_NOISY`; promising zones require both directions at 40 or more, FLAT between 55% and 85%, a ratio below 12.14, and non-HIGH noise risk.

## Files changed

- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/compact_archive_pruner.py`

## Files added

- `app/diagnostics/label_grid_sensitivity_recompute.py`
- `tests/test_ml38_10_39_read_only_label_grid_sensitivity_recompute.py`
- `tests/test_stage_ml38_10_39_report.py`
- `reports/stage_ml38_10_39_read_only_label_grid_sensitivity_recompute_report.md`

## Verification

- `python -m py_compile`: passed for the six authorized files.
- `python -m pytest tests/test_ml38_10_39_read_only_label_grid_sensitivity_recompute.py`: passed, 8 tests.
- `python -m pytest tests/test_stage_ml38_10_39_report.py`: passed, 1 test.
- Full pytest: not run; user approval is required after targeted tests.

## Prohibition and safety confirmation

- runtime training was not run.
- clean/fast/quick/sequence/full were not run.
- labels, label builders, gates, and model logic were not changed.
- database was not changed and ml_labels were not written.
- no database write repository method is called by the diagnostic loader.
- no runtime config was added.
- live trading and auto-activation were not changed.
- no runtime JSON, ZIP, or log artifact was created or staged.
