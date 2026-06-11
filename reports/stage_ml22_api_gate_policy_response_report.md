# Stage ML22 - API response with GatePolicy block

## Status

Stage ML22 completed.

The `/predict` API response now contains a `gate_policy` block built through ML21 runtime binding.

## Endpoint changed

Changed endpoint:

- `/predict`

The response still keeps the existing prediction fields:

- `ml_available`
- `reason`
- `symbol`
- `interval`
- `horizon_candles`
- `direction`
- `prob_up`
- `prob_down`
- `prob_flat`
- `tp_before_sl_probability`
- `expected_move_atr`
- `risk_score`
- `confidence`
- `model_version`

In other words, old prediction fields are preserved.

The `gate_policy` block was added as a new field.

## Implemented files

- `app/api/schemas.py`
- `app/api/gate_policy_response_builder.py`
- `app/api/routes_predict.py`
- `tests/test_gate_policy_api_response_builder.py`
- `tests/test_api_predict_gate_policy_block.py`
- `tests/test_stage_ml22_api_gate_policy_report.py`
- `reports/stage_ml22_api_gate_policy_response_report.md`

## API integration

The API flow is now:

```text
request
-> PredictionService
-> prediction payload/result
-> ML21 runtime binding
-> gate_policy block
-> API response
```

The helper module is:

`app/api/gate_policy_response_builder.py`

It normalizes prediction response data, calls ML21 runtime binding, and returns an API-safe `gate_policy` block.

## gate_policy block

The response now contains:

```json
"gate_policy": {
  "enabled": true,
  "source": "ml21_runtime_binding",
  "is_valid": true,
  "direction": "LONG",
  "gate_policy_payload": { "...": "binding payload" },
  "gate_policy_decision": { "...": "binding decision" },
  "issues": [],
  "issue_count": 0,
  "integration_status": {
    "prediction_service_bound": true,
    "runtime_adapter_used": true,
    "gate_policy_service_used": true,
    "database_connected": false,
    "traders_core_connected": false,
    "live_trading_connected": false,
    "orders_enabled": false
  }
}
```

If binding receives an invalid payload, the API still returns a safe `gate_policy` block:

- `is_valid: false`
- `direction: NONE`
- `gate_policy_payload: null`
- non-empty `issues`

If an unexpected binding error happens, the helper returns:

- `code: gate_policy_binding_error`
- `gate_policy_service_used: false`
- all safety flags remain `false`

## Safety and scope

This stage changes only the API response shape.

It does not:

- connect to traders-core;
- connect to live trading;
- enable orders;
- add database writes for GatePolicy;
- change database schema;
- touch Alembic;
- add migrations.

Safe flags remain:

```text
database_connected: false
traders_core_connected: false
live_trading_connected: false
orders_enabled: false
```

The database was not changed.
Alembic was not touched.

## Validation

ML22 adds tests for:

- gate_policy API response builder;
- `/predict` response with gate_policy block;
- stage report coverage.

Full project validation is run with `python -m pytest`.

Final validation result:

```text
247 passed, 1 warning
```

The one FastAPI/Starlette warning is accepted and is not related to the ML22 API GatePolicy response block.

## Next stage

Next:

```text
ML23 - Replay / evaluation through GatePolicy
```
