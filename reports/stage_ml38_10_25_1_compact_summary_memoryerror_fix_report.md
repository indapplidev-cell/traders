# ML38.10.25.1 — compact summary JSON payload cap / MemoryError fix

## Status

Completed.

## Root cause

`feature_regime_experiment_summary.json` was serializing full `FeatureRegimeExperimentResult.to_dict()` during runtime summary export.
After ML38.10.25 this payload became too large because it included full nested candidate diagnostics, validation candidate boards, gate probes, passed gates, walk-forward fold arrays, directional-side recovery rows, and full `candidate_results` for every config.
That made the per-symbol summary write path vulnerable to `MemoryError`.

## Fix

`FeatureRegimeExperimentReporter.write_summary_json(...)` now writes a compact/capped payload with `summary_payload_mode = "compact_capped_ml38_10_25_1"` and no longer depends on full `FeatureRegimeExperimentResult.to_dict()` for runtime summary generation.
Heavy arrays are preserved only in compact form with counts and truncation flags, including `candidate_results`, `configs_ranked`, `candidate_board_rows`, `best_failed_total_r_by_fold`, `gate_probes`, `passed_gates`, fold snapshots, low-signal folds, and directional-side recovery fold rows.
`GateSelector` diagnostics now cap `gate_probes` and `passed_gates` while preserving total counts.
`MultiSymbolFeatureRegimeAnalyzer` now tolerates compact summary board payloads and caps carried row samples in global analysis output.

## Safety

No trading or ML decision logic was changed.
Safety invariants remain unchanged:

- `approved_for_live_trading = false`
- `approved_for_auto_activation = false`
- `orders_enabled = false`
- `traders_core_connected = false`

`lv30_*` remains research-only.

## Runtime expectations

- `--fast-debug` expected candidate count remains `20`
- `--quick-quality --quick-quality-symbol SOLUSDT` expected candidate count remains `21`

## Tests

Passed:

- `python -m py_compile app/experiments/feature_regime_experiment_reporter.py`
- `python -m py_compile app/experiments/feature_regime_experiment_runner.py`
- `python -m py_compile app/validation/gate_selector.py`
- `python -m py_compile app/diagnostics/walk_forward_validation_candidate_board.py`
- `python -m py_compile app/diagnostics/walk_forward_profit_diagnostics.py`
- `python -m py_compile app/diagnostics/directional_side_signal_recovery_diagnostics.py`
- `python -m py_compile app/experiments/multi_symbol_feature_regime_analyzer.py`
- `python -m py_compile run_fv3_cached_tuning.py`
- `python -m py_compile tests/test_ml38_10_25_1_compact_summary_memoryerror_fix.py`
- targeted `pytest`
- full `pytest`
