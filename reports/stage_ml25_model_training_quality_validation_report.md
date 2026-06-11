# Stage ML25 - Model Training & Quality Validation

Stage ML25 completed.

## Goal

ML25 adds a model quality validator and a quality reporter for `traders-ml`. This stage does not change the public `/predict` response, does not connect `traders-core`, and does not enable live trading. It adds a quality-validation layer that normalizes training, baseline, calibration, profit-aware, walk-forward, and GatePolicy replay diagnostics into one JSON-safe decision.

## What was added

- `app/evaluation/model_quality_validator.py`
- `app/evaluation/model_quality_reporter.py`
- CLI command `model-quality-validation-preview`
- CLI command `model-quality-validation-export`
- deterministic sample mode preview/export behavior
- tests for validator, reporter, CLI, and this stage report

## Quality result in ML25 sample mode

- `quality_status`: `NEEDS_MORE_DATA`
- `sample_mode`: `true`
- `real_training_executed`: `false`
- `model_accuracy`: `0.3927`
- `baseline_accuracy`: `0.3783`
- `accuracy_edge`: `0.0144`
- `collapse_detected`: `false`
- `approved_for_traders_core_integration`: `false`
- `approved_for_live_trading`: `false`
- `approved_for_auto_activation`: `false`

The preview and export commands work in deterministic sample mode. Sample mode does not confirm readiness for traders-core, does not approve live trading, and does not approve auto activation. A real approval requires long-history validation.

## Metrics and quality statuses

The validator aggregates these metrics:

- `model_version`
- `training_run_id`
- `dataset_rows`
- `train_rows`
- `val_rows`
- `test_rows`
- `model_accuracy`
- `baseline_accuracy`
- `accuracy_edge`
- `collapse_detected`
- `calibration_status`
- `profit_aware_status`
- `walk_forward_status`
- `gate_policy_replay_status`
- `reasons`
- `warnings`
- `integration_status`

The validator supports these quality statuses:

- `QUALITY_APPROVED`
- `QUALITY_REJECTED`
- `NEEDS_MORE_DATA`
- `INSUFFICIENT_REAL_HISTORY`

## Validation signals used

- baseline comparison checks whether the model beats the best available baseline accuracy.
- calibration checks whether confidence quality is acceptable enough for analytical use.
- profit-aware checks whether the signal quality is positive or acceptable.
- walk-forward checks whether the model remains stable enough across folds.
- GatePolicy replay checks whether replay diagnostics preserve safety boundaries.

## Safety boundaries

- no live trading
- no orders
- no auto activation
- no traders-core connection
- no database migrations
- no production deploy

Even if `QUALITY_APPROVED` is reached in a future real run, ML25 keeps `approved_for_live_trading` and `approved_for_auto_activation` set to `false`. Only `approved_for_traders_core_integration` may become `true`, and only after non-sample validation.

## Deterministic sample mode

`model-quality-validation-preview` and `model-quality-validation-export` intentionally use sample mode. They do not start long training jobs and do not require a real database-backed training run in tests. This keeps unit tests deterministic and makes the stage safe to validate locally.

Sample mode still exercises:

- baseline normalization
- calibration normalization
- profit-aware normalization
- walk-forward normalization
- GatePolicy replay normalization
- safety flags and approval defaults

## Optional real run command plan

The next real quality pass should use long-history validation with actual project CLI commands and real project parameters:

```powershell
python -m app.cli.commands health
python -m app.cli.commands db-check
python -m app.cli.commands load-candles --symbol <symbol> --interval <interval> --start-date <yyyy-mm-dd> --end-date <yyyy-mm-dd>
python -m app.cli.commands check-candle-gaps --symbol <symbol> --interval <interval> --start-date <yyyy-mm-dd> --end-date <yyyy-mm-dd>
python -m app.cli.commands build-features --symbol <symbol> --interval <interval> --feature-version <feature-version>
python -m app.cli.commands build-labels --symbol <symbol> --interval <interval> --horizon-candles <horizon> --label-version <label-version> --direction-atr-threshold <value> --take-profit-atr <value> --stop-loss-atr <value>
python -m app.cli.commands build-dataset --symbol <symbol> --interval <interval> --horizon-candles <horizon> --feature-version <feature-version> --label-version <label-version> --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands train --symbol <symbol> --interval <interval> --horizon-candles <horizon> --feature-version <feature-version> --label-version <label-version> --model-name candle_mlp --epochs <epochs> --learning-rate <value> --weight-decay <value> --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands probability-diagnostics --model-version <model-version> --symbol <symbol> --interval <interval> --feature-version <feature-version> --label-version <label-version> --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands calibration-eval --model-version <model-version> --symbol <symbol> --interval <interval> --horizon-candles <horizon> --feature-version <feature-version> --label-version <label-version> --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands profit-eval-v2 --model-version <model-version> --symbol <symbol> --interval <interval> --feature-version <feature-version> --label-version <label-version> --take-profit-atr <value> --stop-loss-atr <value> --fee-r <value> --slippage-r <value> --same-candle-policy conservative --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands compare-models --symbol <symbol> --interval <interval> --horizon-candles <horizon> --feature-version <feature-version> --label-version <label-version> --train-end <yyyy-mm-dd> --validation-end <yyyy-mm-dd>
python -m app.cli.commands walk-forward-eval --model-version <model-version> --symbol <symbol> --interval <interval> --feature-version <feature-version> --label-version <label-version> --mode <mode> --train-days <days> --validation-days <days> --test-days <days> --step-days <days> --min-train-rows <rows> --take-profit-atr <value> --stop-loss-atr <value> --fee-r <value> --slippage-r <value> --same-candle-policy conservative
python -m app.cli.commands gate-policy-replay-evaluate-export
python -m app.cli.commands model-quality-validation-export
```

## Why long-history validation is still required

ML25 only adds the quality-validation layer and a deterministic sample mode. For a real quality decision, the project still needs:

- long-history validation
- enough dataset rows
- enough walk-forward folds
- enough GatePolicy replay records
- a real training run with persistent diagnostics

Without that, the correct result remains `NEEDS_MORE_DATA` or `INSUFFICIENT_REAL_HISTORY`.

## Final validation

- Targeted ML25 tests passed:
  - `tests/test_model_quality_validator.py`
  - `tests/test_model_quality_reporter.py`
  - `tests/test_model_quality_cli.py`
  - `tests/test_stage_ml25_model_quality_report.py`
- CLI preview/export check passed:
  - `python -m app.cli.commands model-quality-validation-preview`
  - `python -m app.cli.commands model-quality-validation-export`
- `python -m py_compile` passed for the new validator, reporter, CLI, and test files.
- Full `pytest` result: `279 passed, 1 warning`

## Next stage

ML26 - Long-history training and walk-forward validation
