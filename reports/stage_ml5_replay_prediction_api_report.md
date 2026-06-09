# Stage ML5 Replay Prediction API Report

## Created Files

- `app/replay/__init__.py`
- `app/replay/replay_models.py`
- `app/replay/historical_replay_engine.py`
- `app/replay/replay_service.py`
- `app/prediction/__init__.py`
- `app/prediction/predictor.py`
- `app/prediction/prediction_service.py`
- `app/api/routes_predict.py`
- `app/api/routes_models.py`
- `app/api/routes_replay.py`
- `app/api/routes_shared.py`
- `app/db/repositories/prediction_repository.py`
- `app/db/repositories/replay_repository.py`
- `tests/test_predictor.py`
- `tests/test_prediction_service.py`
- `tests/test_api_predict.py`
- `tests/test_replay_engine.py`
- `tests/test_replay_service.py`
- `reports/stage_ml5_replay_prediction_api_report.md`

## Changed Files

- `app/api/main.py`
- `app/api/schemas.py`
- `app/cli/commands.py`
- `app/db/repositories/__init__.py`
- `app/db/repositories/model_registry_repository.py`

## API Endpoints

- `POST /predict`
  - loads active model or returns fallback contract
  - builds features from passed candles only
  - writes prediction to `ml_predictions`
- `GET /models`
  - returns registered models
- `POST /models/activate`
  - activates `model_version`
- `GET /replay/sessions`
  - returns replay session list

Request/response schemas are OpenAPI-compatible through Pydantic models in `app/api/schemas.py`.

## Replay Logic

Historical replay flow:
1. choose explicit `model_version` or active model for the scope;
2. load historical candles from DB;
3. build actual future labels over the same history;
4. iterate history with a sliding window up to each replay point;
5. run prediction at each point using only candles available up to that point;
6. open the next `horizon_candles` through label logic and compare predicted direction with actual direction;
7. write each replay row to `ml_replay_results`;
8. write replay summary to `ml_replay_sessions`;
9. generate markdown replay report in `reports/`.

## Fallback Contract

`/predict` is fallback-friendly and does not throw when ML is unavailable.

Returned contracts:
- model not found:
  - `{"ml_available": false, "reason": "active_model_not_found"}`
- insufficient candle history:
  - `{"ml_available": false, "reason": "not_enough_candles"}`
- successful prediction:
  - includes `ml_available=true`, direction probabilities, TP-before-SL probability, expected move, risk score, confidence, and `model_version`

This keeps the contract safe for future `traders-core` consumption without directly coupling the projects.

## Verification Commands

- `python -m pytest`
- `python -m app.cli.commands model-list`
- Replay command from the brief was not executed:
  - `python -m app.cli.commands replay --model-version <existing_model_version> --symbol BTCUSDT --interval 15m --start-date 2025-01-01 --end-date 2025-01-07 --horizon-candles 8`

## Verification Results

- `python -m pytest`
  - `28 passed`
- `python -m app.cli.commands model-list`
  - `[]`
- Replay command:
  - not executed because there is no existing trained model in the registry
  - current `model-list` output is empty, so there is no valid `model_version` to pass into replay
