# Stage ML7 Baselines Diagnostics Report

## Created Files

- `app/baseline/__init__.py`
- `app/baseline/baseline_models.py`
- `app/baseline/baseline_evaluator.py`
- `app/baseline/baseline_service.py`
- `app/diagnostics/__init__.py`
- `app/diagnostics/dataset_diagnostics.py`
- `app/diagnostics/prediction_diagnostics.py`
- `app/diagnostics/diagnostics_service.py`
- `tests/test_baseline_service.py`
- `tests/test_dataset_diagnostics.py`
- `tests/test_model_diagnostics.py`
- `tests/test_class_weights.py`
- `tests/test_overfit_check.py`
- `tests/test_compare_models.py`
- `reports/stage_ml7_baselines_diagnostics_report.md`

## Modified Files

- `README.md`
- `app/cli/commands.py`
- `app/training/loss.py`
- `app/training/training_service.py`
- `tests/test_train_cli_options.py`

## .gitignore Confirmation

- `Test-Path .gitignore` -> `True`

## Junk Cleanup Confirmation

Removed after final verifications:

- `.pytest_cache/`
- `**/__pycache__/`
- `*.pyc`
- `*.pyo`
- `*.egg-info/`

Post-cleanup scan:

- `Get-ChildItem -Recurse -Force | Where-Object { $_.FullName -match "__pycache__|\.pytest_cache|\.egg-info|\.pyc$|\.pyo$" }`
- result: no output

## Baseline Results

Report:

- `reports/baseline_btcusdt_15m_h8_fv1_lv1.json`

Validation/test summary:

- `always_flat`
  - validation accuracy: `0.2423611111111111`
  - test accuracy: `0.22971204188481675`
  - predicted test counts: `FLAT=1528`
- `majority_class`
  - train majority class: `DOWN`
  - validation accuracy: `0.35833333333333334`
  - test accuracy: `0.3782722513089005`
  - predicted test counts: `DOWN=1528`
- `last_return_direction`
  - threshold: `0.0005`
  - validation accuracy: `0.35138888888888886`
  - test accuracy: `0.325261780104712`
- `simple_ema_trend`
  - validation accuracy: `0.3638888888888889`
  - test accuracy: `0.3782722513089005`

Best baseline by current comparison:

- `majority_class`
- test accuracy: `0.3782722513089005`
- test brier_score: `1.243455497382199`

## Dataset Diagnostics Summary

Report:

- `reports/dataset_diagnostics_btcusdt_15m_h8_fv1_lv1.json`

Key values:

- `total_rows: 8433`
- `train_rows: 5465`
- `validation_rows: 1440`
- `test_rows: 1528`
- `label_counts_train: {"UP": 2015, "DOWN": 2067, "FLAT": 1383}`
- `label_counts_validation: {"UP": 575, "DOWN": 516, "FLAT": 349}`
- `label_counts_test: {"UP": 599, "DOWN": 578, "FLAT": 351}`
- `feature_null_counts["ema_200"]: 199`
- `feature_null_counts["rolling_volatility_50"]: 50`
- `train_first_open_time: 2025-01-03T01:45:00+00:00`
- `train_last_open_time: 2025-02-28T23:45:00+00:00`
- `validation_first_open_time: 2025-03-01T00:00:00+00:00`
- `validation_last_open_time: 2025-03-15T23:45:00+00:00`
- `test_first_open_time: 2025-03-16T00:00:00+00:00`
- `test_last_open_time: 2025-03-31T21:45:00+00:00`

## Overfit Check Result

Report:

- `reports/overfit_check_btcusdt_15m_h8.json`

Result:

- `rows: 256`
- `epochs: 100`
- `direction_class_weights: [0.8205128205128205, 0.8366013071895425, 1.7066666666666668]`
- `random_baseline_accuracy: 0.3333333333333333`
- `overfit_train_accuracy: 0.90234375`
- `is_better_than_random_baseline: true`

Interpretation:

- overfit sanity check passed
- the training loop can fit a small train subset much better than random baseline

## Old Model Version and Diagnostics

Old active model:

- `ml_candle_mlp_v1_2026_06_08_163348`

Diagnostics report:

- `reports/model_diagnostics_ml_candle_mlp_v1_2026_06_08_163348.json`

Key diagnostics:

- `accuracy_test: 0.22971204188481675`
- `brier_score_test: 0.6876406641968033`
- `predicted_counts_test: {"UP": 0, "DOWN": 0, "FLAT": 1528}`
- `collapse_detected: true`
- `collapse_reason: FLAT dominates test predictions: ratio=1.0000`

## New Model Version and Diagnostics

New model trained in this stage:

- `ml_candle_mlp_v1_2026_06_08_172848`

Artifact path:

- `artifacts/models/ml_candle_mlp_v1_2026_06_08_172848`

Diagnostics report:

- `reports/model_diagnostics_ml_candle_mlp_v1_2026_06_08_172848.json`

Key diagnostics:

- `accuracy_test: 0.39267015706806285`
- `brier_score_test: 0.6608990773124575`
- `predicted_counts_test: {"UP": 1350, "DOWN": 3, "FLAT": 175}`
- `collapse_detected: false`
- `collapse_reason: null`

## Baseline vs Model Comparison

Report:

- `reports/model_comparison_btcusdt_15m_h8.json`

Comparison result:

- `best_baseline: majority_class`
- `best_baseline test accuracy: 0.3782722513089005`
- `best_model: ml_candle_mlp_v1_2026_06_08_172848`
- `best_model test accuracy: 0.39267015706806285`
- `best_model test brier_score: 0.6608990773124575`
- `is_best_model_better_than_best_baseline: true`
- notes: `Recommendation only. No model activation is performed automatically.`

## Prediction Collapse Detection

- old model collapse detected: `true`
- new model collapse detected: `false`

## Is New Model Better Than Baseline

- yes, on current test slice the new model is better than the best baseline by the comparison rule used in `compare-models`
- the new model was not auto-activated
- the old model remains active

## Verification Commands Executed

```powershell
python -m pytest
$env:PATH='C:\Users\ZENOL\AppData\Roaming\Python\Python311\Scripts;' + $env:PATH; alembic upgrade head
python -m app.cli.commands health
python -m app.cli.commands db-check
python -m app.cli.commands model-list
python -m app.cli.commands evaluate-baselines --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands dataset-diagnostics --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands overfit-check --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --rows 256 --epochs 100
python -m app.cli.commands model-diagnostics --model-version ml_candle_mlp_v1_2026_06_08_163348 --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --epochs 20 --learning-rate 0.001 --weight-decay 0.0001 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands model-list
python -m app.cli.commands model-diagnostics --model-version ml_candle_mlp_v1_2026_06_08_172848 --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands compare-models --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

## Verification Results

- `python -m pytest` -> `40 passed`
- `alembic upgrade head` -> success through Python 3.11 Alembic binary
- `health` -> `{"status":"ok","service":"traders-ml","version":"0.1.0"}`
- `db-check` -> `db-check: ok`
- `model-list` before training -> one active old model
- `train` -> new model `ml_candle_mlp_v1_2026_06_08_172848`
- `model-list` after training -> new model inactive, old model still active

## Remaining Limitations

- the new model improved over baseline, but it is still heavily biased toward `UP` on the current test slice and almost never predicts `DOWN`
- confidence remains concentrated mostly in the `0.2-0.4` range, so probability calibration is still weak
- activation is still manual by policy even when comparison looks better
