# Stage ML10 Report

## What Was Done
- Added walk-forward split planning with `expanding` and `rolling` modes.
- Added validation-only gate selection.
- Added walk-forward evaluation that selects gate on validation and applies it to test without retraining models.
- Added direction bias diagnostics to walk-forward reports.
- Added robust experiment summary over `walk_forward_eval_*.json`.
- Hardened `ProfitAwareEvaluatorV2` with `same-candle-policy` and `ambiguous_count`.

## Created Files
- `app/validation/__init__.py`
- `app/validation/walk_forward_splitter.py`
- `app/validation/gate_selector.py`
- `app/validation/walk_forward_evaluator.py`
- `app/diagnostics/direction_bias_diagnostics.py`
- `tests/test_walk_forward_splitter.py`
- `tests/test_gate_selector.py`
- `tests/test_walk_forward_evaluator.py`
- `tests/test_direction_bias_diagnostics.py`
- `tests/test_robust_experiment_summary.py`
- `reports/stage_ml10_walk_forward_gate_robustness_report.md`

## Modified Files
- `app/evaluation/profit_aware_evaluator_v2.py`
- `app/diagnostics/diagnostics_service.py`
- `app/cli/commands.py`
- `tests/test_profit_aware_evaluator_v2.py`

## Checks
- `python -m pytest` -> `64 passed`
- `alembic upgrade head` -> success
- `python -m app.cli.commands health` -> `{"status": "ok", "service": "traders-ml", "version": "0.1.0"}`
- `python -m app.cli.commands db-check` -> `db-check: ok`

## Walk-Forward Results
- `ml_candle_mlp_v1_2026_06_08_172848`
- `fold_count=4`
- `folds_with_selected_gate=3`
- `folds_profitable_on_test=0`
- `total_test_signal_count=1206`
- `total_test_r=-95.96010005`
- `avg_test_profit_factor=0.7506926569`
- `avg_test_expectancy_r=-0.1370635552`
- `profitable_fold_ratio=0.0`
- `long_total_count=1206`
- `short_total_count=0`
- `bias warnings=["long_short_imbalance_gte_0_90","no_short_signals","predicted_up_ratio_gte_0_80"]`

- `ml_candle_mlp_v1_2026_06_08_191038`
- `fold_count=4`
- `folds_with_selected_gate=3`
- `folds_profitable_on_test=1`
- `total_test_signal_count=1193`
- `total_test_r=-75.12509579`
- `avg_test_profit_factor=1.1133131909`
- `avg_test_expectancy_r=-0.0024540265`
- `profitable_fold_ratio=0.3333333333`
- `long_total_count=1193`
- `short_total_count=0`
- `bias warnings=["long_short_imbalance_gte_0_90","no_short_signals","predicted_up_ratio_gte_0_80"]`

- `ml_candle_mlp_v1_2026_06_08_191245`
- `fold_count=4`
- `folds_with_selected_gate=3`
- `folds_profitable_on_test=2`
- `total_test_signal_count=998`
- `total_test_r=-18.70700528`
- `avg_test_profit_factor=1.3414610767`
- `avg_test_expectancy_r=0.1486989451`
- `profitable_fold_ratio=0.6666666667`
- `long_total_count=998`
- `short_total_count=0`
- `bias warnings=["long_short_imbalance_gte_0_90","no_short_signals","predicted_up_ratio_gte_0_80"]`

- `ml_candle_mlp_v1_2026_06_08_191453`
- `fold_count=4`
- `folds_with_selected_gate=3`
- `folds_profitable_on_test=2`
- `total_test_signal_count=973`
- `total_test_r=-20.30000352`
- `avg_test_profit_factor=inf`
- `avg_test_expectancy_r=0.4917440786`
- `profitable_fold_ratio=0.6666666667`
- `long_total_count=973`
- `short_total_count=0`
- `bias warnings=["long_short_imbalance_gte_0_90","no_short_signals","predicted_up_ratio_gte_0_80"]`

## Robust Summary
- Command: `python -m app.cli.commands robust-experiment-summary --symbol BTCUSDT --interval 15m`
- Report: `reports/robust_experiment_summary.json`
- `robust_recommended_model_version=null`
- Exact reject reasons:
- `avg_test_expectancy_r_not_positive`
- `avg_test_profit_factor_not_above_1`
- `dominant_class_ratio_gte_0_90`
- `no_short_signals`
- `profitable_fold_ratio_lt_0_60`
- `total_test_r_not_positive`

## Main Conclusion
- Walk-forward removed the illusion of a reusable edge from single-test gate tuning.
- Some models still show positive fold-level `profit_factor` or positive `avg_test_expectancy_r`, but all 4 fail robust recommendation because:
- total walk-forward `R` is non-positive for every model
- all models remain long-only in selected gates, with `short_total_count=0`
- dominant class / direction bias remains too high
- no model satisfied the robust recommendation rules

## Constraints Confirmed
- Model was not activated automatically.
- `model-activate` was not used.
- `traders-core` was not changed.
