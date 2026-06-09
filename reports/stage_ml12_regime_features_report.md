# Stage ML12 - Regime Features, Baseline Feature Parity and Directional Signal Upgrade

## What Was Done

- Added a new feature version `fv2_regime` without breaking `fv1`.
- Added EMA baseline parity features, slope features, regime flags, and momentum/pullback features.
- Added `feature-diagnostics-v2`.
- Added `model-vs-baseline` comparison.
- Added `stage-ml12-summary`.
- Added fallback chronological dataset split when legacy default dates leave validation or test empty.
- Trained exactly 2 new fv2 models.
- Ran evaluation, probability diagnostics, prediction bias diagnostics, walk-forward evaluation, model-vs-baseline comparison, robust summary, and ML12 summary.

## Created Files

- `app/diagnostics/feature_diagnostics_v2.py`
- `app/evaluation/model_vs_baseline_comparator.py`
- `tests/test_regime_feature_builder.py`
- `tests/test_feature_diagnostics_v2.py`
- `tests/test_model_vs_baseline_comparator.py`
- `tests/test_stage_ml12_summary.py`
- `reports/stage_ml12_regime_features_report.md`

## Modified Files

- `app/features/__init__.py`
- `app/features/feature_models.py`
- `app/features/feature_builder.py`
- `app/diagnostics/diagnostics_service.py`
- `app/training/training_service.py`
- `app/cli/commands.py`
- `app/dataset/dataset_splitter.py`
- `tests/test_dataset_builder.py`
- `tests/test_dataset_splitter.py`
- `tests/test_train_cli_options.py`

## Final Checks

- `python -m pytest` -> `80 passed`
- `alembic upgrade head` -> success
- `python -m app.cli.commands health` -> `{"status": "ok", "service": "traders-ml", "version": "0.1.0"}`
- `python -m app.cli.commands db-check` -> `db-check: ok`
- `python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv2_regime` -> `built=8640`
- `python -m app.cli.commands feature-diagnostics-v2 --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp15_sl10` -> report created
- `python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp15_sl10` -> `dataset_rows=8415`
- `python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp10_sl10` -> `dataset_rows=8415`
- `python -m app.cli.commands train --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp15_sl10` -> `ml_candle_mlp_v1_2026_06_09_040604`
- `python -m app.cli.commands train --symbol BTCUSDT --interval 15m --feature-version fv2_regime --label-version lv_h16_thr03_tp10_sl10` -> `ml_candle_mlp_v1_2026_06_09_040622`
- `evaluate`, `probability-diagnostics`, `prediction-bias-root-cause`, `walk-forward-eval`, `model-vs-baseline` were executed for both new models
- `python -m app.cli.commands robust-experiment-summary --symbol BTCUSDT --interval 15m --require-both-directions` -> `robust_recommended_model_version=null`
- `python -m app.cli.commands stage-ml12-summary --symbol BTCUSDT --interval 15m` -> report created

## Feature Counts

- `fv1` feature count: `34`
- `fv2_regime` feature count: `77`

## Dataset v2 Stats

- `lv_h16_thr03_tp15_sl10`: `dataset_rows=8415`, `train=5890`, `validation=1262`, `test=1263`, `dropped_incomplete_features=209`, `dropped_missing_labels=16`
- `lv_h16_thr03_tp10_sl10`: `dataset_rows=8415`, `train=5890`, `validation=1262`, `test=1263`, `dropped_incomplete_features=209`, `dropped_missing_labels=16`

## Feature Diagnostics v2

- Report: `reports/feature_diagnostics_v2_BTCUSDT_15m_fv2_regime.json`
- `null warnings`: none
- `zero variance warnings`: none
- `warning_count`: `55`
- Most warnings are `low_up_down_separation:*`
- Top UP/DOWN separation features:
- `ema_9` -> `914.1950631311192`
- `ema_21` -> `898.3195562905603`
- `ema_50` -> `839.5199478582945`
- `ema_200` -> `713.0696268159227`
- `macd_signal` -> `27.651729460651122`

## New Models

- `ml_candle_mlp_v1_2026_06_09_040604`
- label version: `lv_h16_thr03_tp15_sl10`
- accuracy: `0.35391923990498814`
- dominant_class_ratio: `0.6552083333333333`
- recall_DOWN: `0.6182634730538922`
- long_count: `3`
- short_count: `148`
- global_total_r: `22.26039590999996`
- global_profit_factor: `1.280507126250739`
- global_expectancy_r: `0.1474198404635759`
- profitable_fold_ratio: `0.5`
- model_vs_ema_baseline total_r: `22.26039590999996` vs `129.6027191899973`
- model_vs_ema_baseline profit_factor: `1.280507126250739` vs `1.0723524923111214`
- recommendation_allowed: `false`
- reject_reasons: `["model_total_r_not_above_baseline"]`

- `ml_candle_mlp_v1_2026_06_09_040622`
- label version: `lv_h16_thr03_tp10_sl10`
- accuracy: `0.30245447347585114`
- dominant_class_ratio: `0.4822916666666667`
- recall_DOWN: `0.5059880239520959`
- long_count: `36`
- short_count: `422`
- global_total_r: `-19.904769280000192`
- global_profit_factor: `0.9286089339121714`
- global_expectancy_r: `-0.043460194934498236`
- profitable_fold_ratio: `0.0`
- model_vs_ema_baseline total_r: `-19.904769280000192` vs `129.6027191899973`
- model_vs_ema_baseline profit_factor: `0.9286089339121714` vs `1.0723524923111214`
- recommendation_allowed: `false`
- reject_reasons: `["model_total_r_not_above_baseline", "model_profit_factor_not_above_baseline", "model_expectancy_not_positive"]`

## Walk-Forward Summary

- `ml_candle_mlp_v1_2026_06_09_040604`: `fold_count=4`, `folds_with_selected_gate=2`, `folds_profitable_on_test=1`, `total_test_signal_count=151`, `total_test_r=22.26039590999996`, `avg_test_profit_factor=1.8000063766108338`, `avg_test_expectancy_r=0.274664280879354`, `profitable_fold_ratio=0.5`
- `ml_candle_mlp_v1_2026_06_09_040622`: `fold_count=4`, `folds_with_selected_gate=1`, `folds_profitable_on_test=0`, `total_test_signal_count=458`, `total_test_r=-19.904769280000192`, `avg_test_profit_factor=0.9286089339121714`, `avg_test_expectancy_r=-0.043460194934498236`, `profitable_fold_ratio=0.0`

## Recommendation

- `recommended_model_version`: `null`
- `best_model_version`: `ml_candle_mlp_v1_2026_06_09_040604`
- `best_baseline`: `ema_9_21_direction`
- `model_beats_baseline`: `false`
- `short_signals_restored`: `true`
- `dominant_class_ratio_improved`: `true`
- `recommended_reject_reasons`: `["model_total_r_not_above_baseline", "profitable_fold_ratio_lt_0_60"]`
- `recommended_next_action`: `add_more_regime_features`

## Notes

- `robust_experiment_summary` remained `null`.
- Both new models were evaluated but not activated.
- `traders-core` was not changed.
- `alembic upgrade head` was executed with the exact command name `alembic`, but routed to Python 3.11 `alembic.exe` because the system PATH still points the global `alembic.exe` to Python 3.13, which is incompatible with the current SQLAlchemy environment.
