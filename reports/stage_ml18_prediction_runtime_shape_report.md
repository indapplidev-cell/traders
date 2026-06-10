# Stage ML18 — Prediction Runtime Shape Discovery

## Status

Stage ML18 completed.

The project now has a safe text-based discovery layer for narrow prediction runtime shape inspection.

## Purpose

Stage ML18 was created to inspect existing prediction runtime structures before writing any GatePolicy integration mapping.

The implemented flow is:

```text
selected runtime files
→ text-based runtime shape discovery
→ runtime shape report
→ runtime shape reporter
→ CLI compact summary
→ compact JSON file export
```

The runtime shape layer scans selected files as text and does not import the actual prediction service or predictor.

## Important restriction

Stage ML18 does not integrate GatePolicy with real prediction services.

Stage ML18 does not:

- import `app/prediction/prediction_service.py`;
- import `app/prediction/predictor.py`;
- read database state;
- write database state;
- start model training;
- run model inference;
- activate models automatically;
- call traders-core;
- open trades;
- size positions;
- interact with live trading.

## Implemented files

### Runtime shape discovery layer

- `app/gates/gate_policy_prediction_runtime_shape.py`
- `app/gates/gate_policy_prediction_runtime_shape_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_prediction_runtime_shape.py`
- `tests/test_gate_policy_prediction_runtime_shape_reporter.py`
- `tests/test_gate_policy_prediction_runtime_shape_cli.py`
- `tests/test_gate_policy_prediction_runtime_shape_export_cli.py`

## CLI commands

### Compact summary

```powershell
python -m app.cli.commands gate-policy-prediction-runtime-shape-summary
```

This prints compact runtime shape summary JSON.

It does not include the full `files` list.

### File export

```powershell
python -m app.cli.commands gate-policy-prediction-runtime-shape-export
```

This writes compact runtime shape summary JSON to:

```text
reports/gate_policy_prediction_runtime_shape_summary.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Runtime shape target files

Stage ML18 focuses on these target files:

- `app/prediction/predictor.py`
- `app/prediction/prediction_service.py`
- `app/api/schemas.py`
- `tests/test_predictor.py`
- `tests/test_prediction_service.py`
- `tests/test_api_predict.py`

## Latest observed runtime shape summary

Latest observed manual runtime shape summary:

```text
total_targets: 6
existing_targets: 6
missing_targets: 0
files_with_runtime_shape_signals: 6
unique_class_count: 21
unique_function_count: 26
unique_keyword_count: 16
```

Counts can change when runtime files are edited.

## Important runtime classes found

Important classes found include:

- `PredictionRuntime`
- `Predictor`
- `PredictionService`
- `PredictionCandleInput`
- `PredictionContextInput`
- `PredictionRequest`
- `PredictionResponse`
- `HealthResponse`
- `ModelSummaryResponse`
- `ModelActivateRequest`
- `ModelActivateResponse`
- `ReplaySessionResponse`

Test fake classes were also discovered, for example:

- `FakePredictionService`
- `FakePredictor`
- `FakePredictionRepository`
- `FakeModelRegistry`
- `FakeModelLoader`

These fake classes are useful because they document expected runtime behavior in tests.

## Important runtime functions found

Important functions found include:

- `predict`
- `prepare_runtime`
- `predict_from_feature_record`
- `build_feature_records`
- `_resolve_model`
- `_predict_feature_record`
- `_has_incomplete_features`
- `_to_tensor`
- `_to_candle_objects`
- `_candle_payload`
- `get_active_model`
- `get_by_model_version`
- `create`
- `load`
- `activate`
- `list_models`
- `list_sessions`

Test functions were also discovered, for example:

- `test_predictor_returns_fallback_when_active_model_not_found`
- `test_predictor_returns_prediction_and_logs_it`
- `test_prediction_service_delegates_to_predictor`
- `test_predict_endpoint_returns_fallback_contract`
- `test_models_and_replay_endpoints`

## Important keywords found

Important keywords found include:

- `prob_up`
- `prob_down`
- `prob_flat`
- `confidence`
- `risk_score`
- `expected_move_atr`
- `tp_before_sl_probability`
- `model_version`
- `prediction`
- `predictor`
- `regime`
- `symbol`
- `interval`
- `candle`
- `candles`
- `model`

## Runtime shape interpretation

The current runtime shape already contains the core fields required by the earlier GatePolicy prediction payload contract:

- `prob_up`
- `prob_down`
- `prob_flat`
- `confidence`
- `risk_score`
- `expected_move_atr`
- `tp_before_sl_probability`
- `model_version`

This means the project likely has enough raw prediction output data to build a future adapter.

However, Stage ML18 does not perform that mapping yet.

## Validation

Stage ML18 validation target:

```text
python -m pytest
181 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Current project state after Stage ML18

GatePolicy now has five completed supporting layers:

### Stage ML14

Core GatePolicy logic:

- models;
- service;
- batch diagnostics;
- reporter;
- CLI smoke;
- file export;
- stage report.

### Stage ML15

GatePolicy adapter layer:

- raw payload adapter;
- adapter diagnostics;
- adapter reporter;
- CLI preview;
- file export;
- stage report.

### Stage ML16

Prediction payload contract layer:

- payload contract;
- contract reporter;
- CLI preview;
- file export;
- stage report.

### Stage ML17

Prediction discovery layer:

- text-based broad discovery scanner;
- discovery reporter;
- CLI compact summary;
- compact file export;
- stage report.

### Stage ML18

Prediction runtime shape layer:

- narrow runtime shape discovery;
- runtime shape reporter;
- CLI compact summary;
- compact file export;
- stage report.

## Next planned stage

Next stage should be:

```text
Stage ML19.1 — Prediction Payload Mapping Plan
```

The goal is to design the mapping between real prediction runtime output and GatePolicy input.

This must still be a plan/contract stage first.

Do not directly connect GatePolicy to runtime prediction yet.

The next stage should inspect and document mapping rules for:

- `prob_up`, `prob_down`, `prob_flat` → direction;
- prediction confidence → GatePolicy confidence;
- `tp_before_sl_probability` → GatePolicy tp-before-sl probability;
- `risk_score` → GatePolicy risk score;
- `expected_move_atr` → GatePolicy expected move;
- `model_version` → traceability metadata;
- `regime` → GatePolicy regime.

Still no live trading.
Still no auto model activation.
Still no traders-core connection.
Still no database writes for GatePolicy.
Still no direct execution.
