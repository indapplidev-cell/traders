# Stage ML38.2: FV3 Label, Threshold and Collapse Tuning

This report tracks ML38.2 work for `fv3_candle_ta_context`, flat bias reduction, down blindness diagnostics, config ranking, and fresh-grid archive assembly.

## Part 1 status

- branch: `ml38-2-fv3-label-threshold-collapse-tuning`
- commit hash: pending post-commit
- pytest result: `429 passed in 48.75s`
- CLI checks: `health`, `db-check`, `collapse-diagnostics-preview`, `regime-label-builder-preview`, `walk-forward-profit-diagnostics-preview`, `candle-ta-context-preview` for BTCUSDT/ETHUSDT/SOLUSDT, `ml38-2-fv3-tuning-preview` all passed
- py_compile result: passed for `app/cli/commands.py`, `app/diagnostics/class_bias_diagnostics.py`, `app/diagnostics/collapse_tuning_summary.py`, `app/experiments/feature_regime_experiment_runner.py`, `app/experiments/multi_symbol_feature_regime_analyzer.py`, `app/experiments/multi_symbol_feature_regime_reporter.py`, `app/experiments/ml38_2_config_ranker.py`, `app/experiments/ml38_2_fv3_tuning_matrix.py`, `app/labels/label_quality_grid.py`
- fresh grid script path: `D:\disk_E\game_projects\traders\run_ml38_2_fv3_tuning_btc_eth_sol.ps1`
- fresh archive path: pending fresh batch

## Implementation summary

- Added `class_bias_diagnostics` for `flat_bias_detected`, `down_blindness_detected`, `symbol_bias_severity`, and per-class bias ratios.
- Added `collapse_tuning_summary` to distinguish `confidence_collapse`, `flat_bias`, `down_blindness`, `up_bias`, and `mixed`.
- Added ML38.2 risk-first config ranking with transparent `score_components` and `reasons_why_best_still_rejected`.
- Added ML38.2 FV3 tuning matrix and preview/run CLI wrappers for `fv3_candle_ta_context`.
- Preserved FV3 multisymbol invariants and kept gates visible instead of softening or hiding them.

Required final sections:

- branch
- commit hash
- pytest result
- CLI checks
- py_compile result
- fresh grid script path
- fresh archive path
- symbols evaluated
- configs evaluated
- best_config_by_symbol
- best_global_config
- accepted_candidate_count
- rejected_candidate_count
- collapse summary
- flat bias summary
- down blindness summary
- walk-forward summary
- profit-aware summary
- baseline-edge summary
- final decision
- Can proceed to ML38.3
- Can proceed to ML39

Final table format:

| symbol | best_config | status | failed_gates | passed_gates | collapse_type | flat_bias | down_blindness | WF PF | WF R | accuracy | baseline | score |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|

Safety confirmation:

- traders-core integration: no
- live trading: no
- orders/trades: no
- model auto activation: no
- db migrations: no
- production deploy: no
