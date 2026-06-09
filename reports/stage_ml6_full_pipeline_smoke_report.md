# Stage ML6 Full Pipeline Smoke Report

## Scope

- Changes were made only inside `traders-ml/`.
- Existing stage reports `reports/stage_ml1_*.md` through `reports/stage_ml5_*.md` were preserved.

## Created Files

- `.gitignore`
- `alembic/versions/0003_constraints_indexes.py`
- `tests/test_api_session_lifecycle.py`
- `tests/test_db_constraints_indexes.py`
- `tests/test_prediction_candle_schema.py`
- `tests/test_train_cli_options.py`
- `tests/test_full_pipeline_smoke.py`
- `reports/stage_ml6_full_pipeline_smoke_report.md`

## Modified Files

- `app/api/routes_shared.py`
- `app/api/routes_predict.py`
- `app/api/routes_models.py`
- `app/api/routes_replay.py`
- `app/api/schemas.py`
- `app/db/models.py`
- `app/db/repositories/candle_repository.py`
- `app/db/repositories/feature_repository.py`
- `app/db/repositories/label_repository.py`
- `app/features/feature_builder.py`
- `app/dataset/dataset_splitter.py`
- `app/dataset/dataset_builder.py`
- `app/training/training_service.py`
- `app/prediction/predictor.py`
- `app/replay/historical_replay_engine.py`
- `app/cli/commands.py`
- `tests/test_api_predict.py`
- `tests/test_predictor.py`

## Deleted Junk Files

- `.pytest_cache/`
- all `__pycache__/`
- all `*.pyc`
- `traders_ml.egg-info/`

## Foundation Fixes

### Git Ignore

Added ignore rules for:

- Python cache
- virtual environments
- build artifacts
- runtime artifacts
- OS/IDE files

### FastAPI DB Session Lifecycle

Fixed API DB session handling:

- `routes_predict.py`
- `routes_models.py`
- `routes_replay.py`

All DB-backed routes now use FastAPI dependency injection with `Depends(db_session_dependency)` instead of constructing sessions manually inside route factories.

### DB Constraints and Indexes

Added unique constraints:

- `ml_model_versions.model_version`
- `ml_training_runs.run_id`
- `ml_replay_sessions.session_id`

Added indexes:

- `market_candles(symbol, interval, open_time)`
- `ml_features(symbol, interval, candle_open_time, feature_version)`
- `ml_labels(symbol, interval, candle_open_time, horizon_candles, label_version)`
- `ml_predictions(symbol, interval, candle_open_time)`
- `ml_predictions(model_version)`
- `ml_replay_results(session_id)`
- `ml_replay_results(model_version, symbol, interval, candle_open_time)`
- `ml_model_versions(symbol, interval, horizon_candles, is_active)`

Added PostgreSQL partial unique active-model constraint:

- only one active model per `(symbol, interval, horizon_candles)` where `is_active = true`

### Prediction Contract Hardening

Extended prediction candle schema with optional fields:

- `quote_asset_volume`
- `number_of_trades`
- `taker_buy_base_volume`
- `taker_buy_quote_volume`

Fallback behaviour:

- returns `ml_available=false, reason=active_model_not_found` if no active model or artifact is missing
- returns `ml_available=false, reason=not_enough_candles` if feature window is insufficient
- returns `ml_available=false, reason=incomplete_features` if required features are not fully available

### Training/Dataset CLI Configurability

Added CLI support for:

- `build-dataset --train-end --validation-end`
- `train --epochs --learning-rate --weight-decay --train-end --validation-end`
- `predict-sample --symbol --interval --horizon-candles --limit`

### Large Batch Upsert Fix

Fixed PostgreSQL parameter-limit failure during large candle/features/labels upserts by batching repository writes.

## Replay Performance Fix

Initial `replay` implementation timed out because it:

- reloaded the model artifact on every candle
- rebuilt the whole feature history on every candle
- performed per-step prediction flow repeatedly

Fix:

- predictor runtime is prepared once
- feature history is built once
- replay uses prebuilt feature rows for inference

Result:

- required replay command completed successfully in about 18 seconds

## Full Data Smoke Results

### Health and DB

Command:

```powershell
python -m app.cli.commands health
```

Result:

```json
{"status": "ok", "service": "traders-ml", "version": "0.1.0"}
```

Command:

```powershell
python -m app.cli.commands db-check
```

Result:

```text
db-check: ok
```

### Schema Migration

Command:

```powershell
alembic upgrade head
```

Result:

- success

### Candle Load

Command:

```powershell
python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
```

Result:

- `loaded: 8640`
- `inserted_or_updated: 8640`
- `first_open_time: 2025-01-01T00:00:00+00:00`
- `last_open_time: 2025-03-31T23:45:00+00:00`

### Candle Gap Check

Command:

```powershell
python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
```

Result:

- `checked: 8640`
- `duplicate_count: 0`
- `gap_count: 0`
- `misaligned_count: 0`
- `is_valid: true`

### Feature Build

Command:

```powershell
python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1
```

Result:

- `candles_used: 8640`
- `built: 8640`
- `inserted_or_updated: 8640`

### Label Build

Command:

```powershell
python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1
```

Result:

- `candles_used: 8640`
- `built: 8619`
- `inserted_or_updated: 8619`
- `direction_counts: {"UP": 3282, "DOWN": 3197, "FLAT": 2140}`

### Dataset Build

Command:

```powershell
python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
```

Result:

- `dataset_rows: 8433`
- `dropped_incomplete_features: 199`
- `dropped_missing_labels: 8`
- `train_rows: 5465`
- `validation_rows: 1440`
- `test_rows: 1528`
- `train_first_open_time: 2025-01-03T01:45:00+00:00`
- `train_last_open_time: 2025-02-28T23:45:00+00:00`
- `validation_first_open_time: 2025-03-01T00:00:00+00:00`
- `validation_last_open_time: 2025-03-15T23:45:00+00:00`
- `test_first_open_time: 2025-03-16T00:00:00+00:00`
- `test_last_open_time: 2025-03-31T21:45:00+00:00`

Dataset summary file:

- `reports/dataset_summary_btcusdt_15m_h8_fv1_lv1.json`

### Training

Command:

```powershell
python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --epochs 3 --train-end 2025-03-01 --validation-end 2025-03-16
```

Result:

- `run_id: train_ml_candle_mlp_v1_2026_06_08_163348`
- `model_version: ml_candle_mlp_v1_2026_06_08_163348`
- `artifact_path: D:\disk_E\game_projects\traders\traders-ml\artifacts\models\ml_candle_mlp_v1_2026_06_08_163348`
- `accuracy: 0.22971204188481675`
- `precision_up: 0.0`
- `precision_down: 0.0`
- `brier_score: 0.6876406641968033`
- `tp_before_sl_accuracy: 0.7881773399014779`
- `average_expected_move_error: 1.4906230918019392`
- `rows: 1528`

### Model List After Training

Command:

```powershell
python -m app.cli.commands model-list
```

Result before activation:

- one model found
- `model_version: ml_candle_mlp_v1_2026_06_08_163348`
- `is_active: false`

### Model Activation

Command:

```powershell
python -m app.cli.commands model-activate --model-version ml_candle_mlp_v1_2026_06_08_163348
```

Result:

- `activated: true`
- warning: `Model metrics look weak versus baseline: accuracy=0.2297, brier_score=0.6876`

Command:

```powershell
python -m app.cli.commands model-list
```

Result after activation:

- one model found
- `model_version: ml_candle_mlp_v1_2026_06_08_163348`
- `is_active: true`

### Predict Sample

Command:

```powershell
python -m app.cli.commands predict-sample --symbol BTCUSDT --interval 15m --horizon-candles 8 --limit 220
```

Result:

- `ml_available: true`
- `direction: FLAT`
- `prob_up: 0.3241107165813446`
- `prob_down: 0.28955185413360596`
- `prob_flat: 0.38633739948272705`
- `tp_before_sl_probability: 0.5467519760131836`
- `expected_move_atr: 0.0579119473695755`
- `risk_score: 0.18867763876914978`
- `confidence: 0.38633739948272705`
- `model_version: ml_candle_mlp_v1_2026_06_08_163348`

### Replay

Command:

```powershell
python -m app.cli.commands replay --model-version ml_candle_mlp_v1_2026_06_08_163348 --symbol BTCUSDT --interval 15m --start-date 2025-03-16 --end-date 2025-03-31 --horizon-candles 8
```

Result:

- `session_id: replay_ml_candle_mlp_v1_2026_06_08_163348_20260608_165206`
- `results_written: 1528`
- `accuracy: 0.22971204188481675`
- `average_error_score: 0.6748088865067946`
- `actual_counts: {"DOWN": 578, "UP": 599, "FLAT": 351}`
- `predicted_counts: {"FLAT": 1528}`
- replay report: `reports/replay_ml_candle_mlp_v1_2026_06_08_163348_20260608_165206.md`

## Test Results

Command:

```powershell
python -m pytest
```

Result:

- `34 passed`

Added/updated coverage includes:

- API DB session lifecycle
- DB constraints and indexes
- prediction candle schema
- train CLI options forwarding
- full pipeline smoke path
- predictor and replay compatibility

## Verification Commands Executed

```powershell
python -m pytest
alembic upgrade head
python -m app.cli.commands health
python -m app.cli.commands db-check
python -m app.cli.commands load-candles --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
python -m app.cli.commands check-candle-gaps --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-03-31
python -m app.cli.commands build-features --symbol BTCUSDT --interval 15m --feature-version fv1
python -m app.cli.commands build-labels --symbol BTCUSDT --interval 15m --horizon-candles 8 --label-version lv1
python -m app.cli.commands build-dataset --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands train --symbol BTCUSDT --interval 15m --horizon-candles 8 --feature-version fv1 --label-version lv1 --model-name candle_mlp --epochs 3 --train-end 2025-03-01 --validation-end 2025-03-16
python -m app.cli.commands model-list
python -m app.cli.commands model-activate --model-version ml_candle_mlp_v1_2026_06_08_163348
python -m app.cli.commands model-list
python -m app.cli.commands predict-sample --symbol BTCUSDT --interval 15m --horizon-candles 8 --limit 220
python -m app.cli.commands replay --model-version ml_candle_mlp_v1_2026_06_08_163348 --symbol BTCUSDT --interval 15m --start-date 2025-03-16 --end-date 2025-03-31 --horizon-candles 8
```

## Remaining Limitations

- The first real trained model is weak on the current slice and predicts only `FLAT` on the replay test window.
- Activation warning is emitted, but weak models are not blocked by policy.
- `predict-sample` and replay now work on the trained artifact, but prediction quality remains a modelling/data problem rather than an infrastructure problem.
