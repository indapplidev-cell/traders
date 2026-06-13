# Stage ML36.2 Report

## Original fresh grid failure

- model_quality_validation failed with 'NoneType' object is not iterable for BTC/ETH/SOL.
- Critical gap gate did not reach final failed_gates.
- Candidate became FAILED instead of REJECTED.
- Top-level regime summary contradicted candidate runtime status.

## Files changed

- `app/training/training_pipeline_runner.py`
- `app/experiments/label_grid_experiment_runner.py`
- `app/experiments/feature_regime_experiment_runner.py`
- `app/experiments/feature_regime_experiment_reporter.py`
- `app/experiments/multi_symbol_feature_regime_analyzer.py`
- `app/experiments/multi_symbol_feature_regime_reporter.py`
- `tests/test_ml36_2_model_quality_validation_real_grid_none_path.py`
- `tests/test_ml36_2_gap_gate_final_rejection.py`
- `tests/test_ml36_2_top_level_regime_summary_propagation.py`
- `tests/test_ml36_2_no_final_failed_for_quality_rejection.py`
- `tests/test_stage_ml36_2_report.py`

## Fixes

- Real runtime payload normalization was added in the training pipeline runner so `model_quality_validation` no longer crashes on missing dict/list diagnostics.
- Gap quality rejection now forces `gap_quality_gate` into final `failed_gates` and resolves to `candidate_status=REJECTED` instead of a misleading final `FAILED`.
- Top-level feature-regime summary now aggregates final runtime regime state from candidates and exposes explicit `*_any` and `*_all` flags.
- Aggregate summaries now carry explicit diagnostic payloads and missing reasons for `probability_diagnostics`, `collapse_diagnostics_v2`, `walk_forward_profit_diagnostics`, `profit_aware_diagnostics`, `regime_label_builder_status`, and `real_feature_diagnostics`.
- Multi-symbol/reporter summary paths were normalized so `None` list payloads no longer break serialization.

## Regression tests

- `test_ml36_2_model_quality_validation_real_grid_none_path`
- `test_ml36_2_gap_gate_final_rejection`
- `test_ml36_2_top_level_regime_summary_propagation`
- `test_ml36_2_no_final_failed_for_quality_rejection`
- `test_stage_ml36_2_report`

## Safety

- traders-core integration: no
- live trading: no
- orders/trades: no
- model auto activation: no
- database migrations: no
- production deploy: no
- ML38/candle/TA features: no
