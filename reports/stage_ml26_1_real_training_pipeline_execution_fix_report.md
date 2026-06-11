# Stage ML26.1 - Real Training Pipeline Execution Fix

Stage ML26.1 completed.

## Goal

Replace the ML26 real-mode placeholder path in `train-quality-pipeline` with actual service-backed execution for the existing training and diagnostics stages.

## Scope

- kept `dry-run` behavior unchanged
- kept deterministic sample mode unchanged
- wired real mode into existing project services instead of adding a parallel architecture
- kept `gate_policy_replay_evaluation` on the existing sample-only evaluator path
- preserved safety boundaries: no live trading, no orders, no traders-core integration, no auto activation

## Real-mode wiring added

- `load_candles`
- `check_candle_gaps`
- `build_features`
- `build_labels`
- `build_dataset`
- `train_model`
- `probability_diagnostics`
- `baseline_compare`
- `calibration_diagnostics`
- `profit_aware_evaluation`
- `walk_forward_evaluation`
- `model_quality_validation`

## Parameter policy

The runner now reuses existing repo conventions and command/service interfaces:

- `feature_version = fv1`
- `label_version = lv1`
- `horizon_candles = 8` resolved from `lv1`
- label defaults reused from CLI: `direction_atr_threshold = 0.5`, `take_profit_atr = 1.5`, `stop_loss_atr = 1.0`
- walk-forward defaults reused from the existing diagnostics flow: `mode = expanding`, `train_days = 45`, `validation_days = 10`, `test_days = 10`, `step_days = 10`, `min_train_rows = 1000`
- cost assumptions reused from the existing diagnostics/baseline comparison flow: `fee_r = 0.02`, `slippage_r = 0.01`, `same_candle_policy = conservative`

## Main fix

The generic real-mode skip reason `direct_real_execution_not_wired` is no longer part of the normal real execution path for the wired stages above.

## Tests updated

- `tests/test_training_pipeline_runner.py`
- `tests/test_training_pipeline_cli.py`
- `tests/test_training_pipeline_logger.py`
- `tests/test_training_pipeline_reporter.py`

## Safety

- no live trading
- no orders
- no traders-core integration
- no auto activation
- runtime artifacts under `reports/training_pipeline_runs/` remain non-commit artifacts
