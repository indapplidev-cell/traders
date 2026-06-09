# Stage ML8 Report

## Created Files
- `app/labels/label_config.py`
- `app/diagnostics/label_diagnostics.py`
- `app/experiments/__init__.py`
- `app/experiments/experiment_models.py`
- `app/experiments/experiment_reporter.py`
- `app/experiments/label_grid_search.py`
- `app/evaluation/__init__.py`
- `app/evaluation/confidence_gate_evaluator.py`
- `app/evaluation/profit_aware_evaluator.py`
- `app/evaluation/calibration_evaluator.py`
- `tests/test_label_config.py`
- `tests/test_label_diagnostics.py`
- `tests/test_label_grid_search.py`
- `tests/test_confidence_gate_evaluator.py`
- `tests/test_profit_aware_evaluator.py`
- `tests/test_calibration_evaluator.py`
- `tests/test_experiment_summary.py`
- `reports/stage_ml8_labels_calibration_profit_report.md`

## Modified Files
- `app/labels/direction_label_builder.py`
- `app/labels/tp_sl_label_builder.py`
- `app/labels/label_builder.py`
- `app/diagnostics/diagnostics_service.py`
- `app/cli/commands.py`

## Pytest
- Command: `python -m pytest`
- Result: `47 passed`

## Label Diagnostics
- Command: `python -m app.cli.commands label-diagnostics --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1`
- Report: `reports/label_diagnostics_btcusdt_15m_h8_lv1.json`
- `total_labels: 8619`
- `direction_counts: UP=3282, DOWN=3197, FLAT=2140`
- `direction_ratios: UP=0.3808, DOWN=0.3709, FLAT=0.2483`
- `tp_before_sl_true_count: 4188`
- `tp_before_sl_false_count: 1219`
- `tp_before_sl_null_count: 3212`
- `future_return_mean: -0.0000846947`
- `future_move_atr_mean: -0.0595863941`

## Label Grid Search
- Command: `python -m app.cli.commands label-grid-search --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31 --feature-version fv1`
- Report: `reports/label_grid_search_btcusdt_15m.json`
- Top 3 `reject_reason=ok` configs selected for training:
- `lv_h16_thr03_tp10_sl10`: `horizon=16`, `threshold=0.3`, `tp=1.0`, `sl=1.0`, `dataset_rows=8425`, `baseline=majority_class`, `baseline_accuracy=0.4394736842`
- `lv_h16_thr03_tp15_sl10`: `horizon=16`, `threshold=0.3`, `tp=1.5`, `sl=1.0`, `dataset_rows=8425`, `baseline=majority_class`, `baseline_accuracy=0.4394736842`
- `lv_h16_thr03_tp20_sl10`: `horizon=16`, `threshold=0.3`, `tp=2.0`, `sl=1.0`, `dataset_rows=8425`, `baseline=majority_class`, `baseline_accuracy=0.4394736842`

## Trained Model Candidates
- `ml_candle_mlp_v1_2026_06_08_191038` for `lv_h16_thr03_tp10_sl10`
- `ml_candle_mlp_v1_2026_06_08_191245` for `lv_h16_thr03_tp15_sl10`
- `ml_candle_mlp_v1_2026_06_08_191453` for `lv_h16_thr03_tp20_sl10`

## Accuracy and Baseline
- `ml_candle_mlp_v1_2026_06_08_191038`: `accuracy=0.4493421053`, `brier_score=0.6543435455`, baseline `0.4394736842`, better than baseline: `yes`
- `ml_candle_mlp_v1_2026_06_08_191245`: `accuracy=0.4513157895`, `brier_score=0.6504964229`, baseline `0.4394736842`, better than baseline: `yes`
- `ml_candle_mlp_v1_2026_06_08_191453`: `accuracy=0.4526315789`, `brier_score=0.6507524473`, baseline `0.4394736842`, better than baseline: `yes`

## Confidence Eval
- Base model command: `python -m app.cli.commands confidence-eval --model-version ml_candle_mlp_v1_2026_06_08_172848 --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16`
- Base model report: `reports/confidence_eval_ml_candle_mlp_v1_2026_06_08_172848.json`
- Base model best threshold: `0.40`, `signal_count=18`, `coverage=0.0117801047`, `accuracy_on_signals=0.6111111111`
- Candidate `ml_candle_mlp_v1_2026_06_08_191038`: best threshold `0.40`, `signal_count=26`, `coverage=0.0171052632`, `accuracy_on_signals=0.7692307692`
- Candidate `ml_candle_mlp_v1_2026_06_08_191245`: best threshold `0.40`, `signal_count=101`, `coverage=0.0664473684`, `accuracy_on_signals=0.6237623762`
- Candidate `ml_candle_mlp_v1_2026_06_08_191453`: best threshold `0.40`, `signal_count=225`, `coverage=0.1480263158`, `accuracy_on_signals=0.5644444444`
- For thresholds `>= 0.45` all evaluated models had `signal_count=0`

## Profit Eval
- Base model command: `python -m app.cli.commands profit-eval --model-version ml_candle_mlp_v1_2026_06_08_172848 --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --take-profit-atr 1.5 --stop-loss-atr 1.0 --confidence-thresholds 0.45,0.50,0.55,0.60,0.65,0.70 --train-end 2025-03-01 --validation-end 2025-03-16`
- Base model report: `reports/profit_eval_ml_candle_mlp_v1_2026_06_08_172848.json`
- Base model: all thresholds `0.45..0.70` produced `signal_count=0`, `profit_factor=0.0`, `total_r=0`
- Candidate `ml_candle_mlp_v1_2026_06_08_191038`: all thresholds `0.45..0.70` produced `signal_count=0`, `profit_factor=0.0`, `total_r=0`
- Candidate `ml_candle_mlp_v1_2026_06_08_191245`: all thresholds `0.45..0.70` produced `signal_count=0`, `profit_factor=0.0`, `total_r=0`
- Candidate `ml_candle_mlp_v1_2026_06_08_191453`: all thresholds `0.45..0.70` produced `signal_count=0`, `profit_factor=0.0`, `total_r=0`

## Calibration Eval
- Base model command: `python -m app.cli.commands calibration-eval --model-version ml_candle_mlp_v1_2026_06_08_172848 --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16`
- Base model report: `reports/calibration_eval_ml_candle_mlp_v1_2026_06_08_172848.json`
- Base model: `brier_score=0.6608990773`, `expected_calibration_error=0.02917555`
- Candidate `ml_candle_mlp_v1_2026_06_08_191038`: `brier_score=0.6543435455`, `expected_calibration_error=0.0780111658`
- Candidate `ml_candle_mlp_v1_2026_06_08_191245`: `brier_score=0.6504964229`, `expected_calibration_error=0.0752164530`
- Candidate `ml_candle_mlp_v1_2026_06_08_191453`: `brier_score=0.6507524473`, `expected_calibration_error=0.0724831966`

## Experiment Summary
- Command: `python -m app.cli.commands experiment-summary --symbol BTCUSDT --interval 15m`
- Report: `reports/stage_ml8_experiment_summary.json`
- `best_label_config: lv_h16_thr03_tp10_sl10`
- `best_model_by_accuracy: ml_candle_mlp_v1_2026_06_08_191453`
- `best_model_by_profit_factor: ml_candle_mlp_v1_2026_06_08_172848`
- `best_model_by_total_r: ml_candle_mlp_v1_2026_06_08_172848`
- `best_model_by_calibration: ml_candle_mlp_v1_2026_06_08_172848`
- `recommended_model_version: null`
- `recommended_confidence_threshold: null`
- `recommended_label_version: null`
- Warning: `Best accuracy model has profit_factor <= 1.0.`

## Model Activation
- New models were not activated automatically.
- `experiment-summary` produced recommendation fields only.
- Automatic activation behavior was not added.

## Remaining Limitations
- All profit-aware evaluations at required thresholds `0.45..0.70` produced zero signals, so there is no profit-positive recommendation.
- All three newly trained candidate models still showed prediction collapse toward `UP` on test.
- Best calibrated model by ECE remains the earlier model `ml_candle_mlp_v1_2026_06_08_172848`, but it also has zero profit signals at required thresholds.
