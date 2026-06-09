# Stage ML11 Report

## Created Files

- `app/baseline/directional_baseline_evaluator.py`
- `app/diagnostics/fold_label_diagnostics.py`
- `app/diagnostics/directional_opportunity_diagnostics.py`
- `app/diagnostics/prediction_bias_root_cause.py`
- `tests/test_fold_label_diagnostics.py`
- `tests/test_directional_opportunity_diagnostics.py`
- `tests/test_directional_baseline_evaluator.py`
- `tests/test_prediction_bias_root_cause.py`
- `tests/test_global_profit_aggregation.py`
- `reports/stage_ml11_direction_bias_root_cause_report.md`

## Modified Files

- `app/evaluation/profit_aware_evaluator_v2.py`
- `app/validation/walk_forward_evaluator.py`
- `app/diagnostics/diagnostics_service.py`
- `app/cli/commands.py`
- `tests/test_walk_forward_evaluator.py`
- `tests/test_robust_experiment_summary.py`

## Implemented ML11 Scope

### Fold Label Diagnostics

- Added `fold-label-diagnostics`.
- For each walk-forward fold it counts `UP/DOWN/FLAT` in `train/validation/test`.
- Added warnings:
  - `train_up_ratio_gte_0_60`
  - `train_down_ratio_gte_0_60`
  - `validation_up_ratio_gte_0_60`
  - `validation_down_ratio_gte_0_60`
  - `test_up_ratio_gte_0_60`
  - `test_down_ratio_gte_0_60`
  - `flat_ratio_gte_0_50`
  - `class_missing`

### Directional Opportunity Diagnostics

- Added `directional-opportunity-diagnostics`.
- For each fold it evaluates long-only and short-only opportunities on validation and test with `same-candle-policy=conservative`.
- Added segment warnings:
  - `no_short_opportunity`
  - `no_long_opportunity`
  - `long_only_market_segment`
  - `short_only_market_segment`
  - `both_sides_unprofitable`

### Directional Baselines

- Added `directional-baselines`.
- Implemented baselines:
  - `always_long`
  - `always_short`
  - `always_flat`
  - `random_long_short`
  - `label_majority_per_train_fold`
  - `previous_candle_direction`
  - `ema_9_21_direction`
- Added global aggregation:
  - `global_gross_profit_r`
  - `global_gross_loss_r`
  - `global_profit_factor`
  - `global_total_r`
  - `global_expectancy_r`
  - `global_win_rate`
  - `global_max_drawdown_r`

### Prediction Bias Root Cause

- Added `prediction-bias-root-cause`.
- Report includes:
  - train/validation/test label distribution
  - predicted class distribution
  - predicted signal distribution
  - average probabilities
  - probability separation metrics
  - confusion matrix
  - recall/precision per class
  - warnings:
    - `predicts_up_but_labels_balanced`
    - `predicts_no_down`
    - `down_recall_zero`
    - `flat_recall_zero`
    - `low_probability_separation`
    - `likely_training_bias`
    - `likely_label_bias`

### Robust Summary Changes

- `robust-experiment-summary` now supports:
  - `--require-both-directions`
  - `--no-require-both-directions`
- Reject reasons now include:
  - `global_total_r_not_positive`
  - `global_profit_factor_not_above_1`
  - `global_expectancy_r_not_positive`
  - `no_short_signals`
  - `no_long_signals`
- Added backward-compatible fallback: if older `walk_forward_eval_*.json` do not yet contain `global_*` fields, global metrics are derived from fold `test_result` blocks.

### Stage Summary

- Added `stage-ml11-summary`.
- Output file:
  - `reports/stage_ml11_direction_bias_root_cause_summary.json`

## Commands Run

1. `python -m pytest`
2. `alembic upgrade head`
3. `python -m app.cli.commands health`
4. `python -m app.cli.commands db-check`
5. `python -m app.cli.commands fold-label-diagnostics --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000`
6. `python -m app.cli.commands directional-opportunity-diagnostics --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000 --take-profit-atr 1.5 --stop-loss-atr 1.0 --fee-r 0.02 --slippage-r 0.01 --same-candle-policy conservative`
7. `python -m app.cli.commands directional-baselines --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp15_sl10 --mode expanding --train-days 45 --validation-days 10 --test-days 10 --step-days 10 --min-train-rows 1000 --take-profit-atr 1.5 --stop-loss-atr 1.0 --fee-r 0.02 --slippage-r 0.01 --same-candle-policy conservative`
8. `python -m app.cli.commands prediction-bias-root-cause --model-version ml_candle_mlp_v1_2026_06_08_172848 --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv1`
9. `python -m app.cli.commands prediction-bias-root-cause --model-version ml_candle_mlp_v1_2026_06_08_191038 --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp10_sl10`
10. `python -m app.cli.commands prediction-bias-root-cause --model-version ml_candle_mlp_v1_2026_06_08_191245 --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp15_sl10`
11. `python -m app.cli.commands prediction-bias-root-cause --model-version ml_candle_mlp_v1_2026_06_08_191453 --symbol BTCUSDT --interval 15m --feature-version fv1 --label-version lv_h16_thr03_tp20_sl10`
12. `python -m app.cli.commands robust-experiment-summary --symbol BTCUSDT --interval 15m --require-both-directions`
13. `python -m app.cli.commands stage-ml11-summary --symbol BTCUSDT --interval 15m`

## Results

### Core Checks

- `python -m pytest` -> `70 passed`
- `alembic upgrade head` -> success
- `python -m app.cli.commands health` -> `{"status": "ok", "service": "traders-ml", "version": "0.1.0"}`
- `python -m app.cli.commands db-check` -> `db-check: ok`

Note:
- The shell `alembic.exe` on default PATH pointed to Python 3.13 and failed because local project dependencies are on Python 3.11.
- Final successful `alembic upgrade head` was executed after normalizing PATH to the Python 3.11 Alembic launcher.

### Fold Label Diagnostics

- `fold_count=4`
- `labels_are_balanced_by_fold=true`
- `warnings=[]`

### Directional Opportunity Diagnostics

- `short_opportunities_exist=true`
- `long_opportunities_exist=true`
- `test_long_total_r=2.136428109997304`
- `test_short_total_r=-114.89522348000266`
- `better_side=LONG`
- Mixed regime warnings were observed across folds:
  - `long_only_market_segment`
  - `short_only_market_segment`

### Directional Baselines

- `always_long.global_total_r=2.136428109997304`
- `always_short.global_total_r=-114.89522348000266`
- `best_directional_baseline=ema_9_21_direction`
- `best_directional_baseline.global_total_r=134.30271918999733`
- `best_directional_baseline.global_profit_factor=1.0748042783449028`

### Prediction Bias Root Cause

- Reports created for:
  - `ml_candle_mlp_v1_2026_06_08_172848`
  - `ml_candle_mlp_v1_2026_06_08_191038`
  - `ml_candle_mlp_v1_2026_06_08_191245`
  - `ml_candle_mlp_v1_2026_06_08_191453`
- All four reports showed `low_probability_separation`.
- On the current default dataset split, validation/test rows are empty for these root-cause reports, so they also emit `predicts_no_down` for empty non-train splits.

### Robust Summary

- `robust_recommended_model_version=null`
- Reject reasons:
  - `dominant_class_ratio_gte_0_90`
  - `global_expectancy_r_not_positive`
  - `global_profit_factor_not_above_1`
  - `global_total_r_not_positive`
  - `no_short_signals`
  - `profitable_fold_ratio_lt_0_60`

### Stage ML11 Summary

- `labels_are_balanced_by_fold=true`
- `short_opportunities_exist=true`
- `best_directional_baseline=ema_9_21_direction`
- `best_directional_baseline_total_r=134.30271918999733`
- `ml_best_global_total_r=-18.707005280000537`
- `ml_best_global_profit_factor=0.968329185928301`
- `ml_beats_directional_baseline=false`
- `all_models_long_only=true`
- `likely_root_cause=feature_insufficient_directional_signal`
- `recommended_next_action=add_regime_features`

## Exact Reason No Model Was Recommended

`robust_recommended_model_version` stayed `null` because the available walk-forward candidates still violate the ML11 hard filters:

- `dominant_class_ratio_gte_0_90`
- `global_expectancy_r_not_positive`
- `global_profit_factor_not_above_1`
- `global_total_r_not_positive`
- `no_short_signals`
- `profitable_fold_ratio_lt_0_60`

## Constraints Confirmed

- No model was auto-activated.
- `traders-core` was not changed.
