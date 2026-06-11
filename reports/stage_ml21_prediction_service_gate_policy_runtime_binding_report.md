# Stage ML21 - PredictionService to GatePolicy Runtime Binding

## Status

Stage ML21 completed.

This stage adds a safe binding layer between prediction runtime payloads, `PredictionService`, the runtime adapter, and the existing GatePolicy service.

## Purpose

Implemented flow:

```text
prediction payload / PredictionService result
-> runtime adapter
-> GatePolicy-compatible payload
-> GatePolicy service decision
-> CLI preview
-> CLI export
-> stage report
```

## Scope and restrictions

Stage ML21 binds prediction runtime data to GatePolicy, but it still stays inside the standalone ML service.

It does not:

- change the API response yet;
- connect to traders-core;
- connect to live trading;
- enable orders;
- write to the database;
- run trading execution;
- open trades.

Safe integration flags remain:

```text
database_connected: false
traders_core_connected: false
live_trading_connected: false
orders_enabled: false
```

The current API response is not changed yet.
ML22 is the next stage for API response with GatePolicy block.

## Implemented files

- `app/gates/gate_policy_prediction_runtime_adapter.py`
- `app/gates/gate_policy_prediction_runtime_binding.py`
- `app/gates/gate_policy_prediction_runtime_binding_reporter.py`
- `app/cli/commands.py`
- `tests/test_gate_policy_prediction_runtime_binding.py`
- `tests/test_gate_policy_prediction_runtime_binding_reporter.py`
- `tests/test_gate_policy_prediction_runtime_binding_cli.py`
- `tests/test_stage_ml21_prediction_service_gate_policy_runtime_binding_report.py`
- `reports/stage_ml21_prediction_service_gate_policy_runtime_binding_report.md`

## Runtime adapter

The runtime adapter now exists in:

`app/gates/gate_policy_prediction_runtime_adapter.py`

It uses the Stage ML20 contract validation and converts a valid runtime prediction payload into a GatePolicy-compatible payload.

Direction mapping follows the ML19 plan:

- `prob_up` dominant -> `LONG`
- `prob_down` dominant -> `SHORT`
- `prob_flat` dominant -> `FLAT`
- tied probabilities -> `NONE`

Invalid payloads do not raise exceptions.
They return `is_valid: false`, `direction: NONE`, `gate_policy_payload: null`, issues, and a safe reject from GatePolicy.

## Binding layer

The new binding module is:

`app/gates/gate_policy_prediction_runtime_binding.py`

It supports two modes.

### payload mode

`bind_prediction_payload_to_gate_policy(payload)`

This mode accepts a plain prediction payload dict and is used by tests and CLI preview without real inference.

### service-result mode

The binding can consume a `PredictionService` result or call an injected `PredictionService` through `bind_from_service_request(...)`.

Request metadata such as `symbol`, `interval`, and context regime are normalized into the prediction payload before adapter validation.

`PredictionService` is used only as a runtime input source.
The binding does not modify `PredictionService`, does not train models, and does not activate models.

## GatePolicy integration

The binding uses:

- the runtime adapter;
- the existing `GatePolicyEvaluationAdapter`;
- the existing GatePolicy service;
- the existing `GatePolicyReporter`.

If the payload is valid, the adapter produces a GatePolicy payload and the GatePolicy service evaluates it.

If the payload is invalid, the binding still produces a safe GatePolicy reject through a fallback `direction: NONE` input.

When there is any ambiguity, the result is a safe reject rather than an allow.

## Reporter

The reporter module is:

`app/gates/gate_policy_prediction_runtime_binding_reporter.py`

It provides:

- binding summary dict;
- binding full report dict;
- binding result dict;
- JSON serialization for summary, full report, and result.

## CLI

Preview command:

```powershell
python -m app.cli.commands gate-policy-runtime-binding-preview
```

This uses a safe sample payload and prints JSON-safe output with:

- `binding_name`
- `binding_version`
- `is_valid`
- `direction`
- `gate_policy_payload`
- `gate_policy_decision`
- `integration_status`
- `issues`

Export command:

```powershell
python -m app.cli.commands gate-policy-runtime-binding-export
```

This writes a runtime artifact to:

```text
reports/gate_policy_runtime_binding_summary.json
```

The file is a runtime artifact and is not committed.

## Validation

Targeted ML21 tests cover:

- valid payload -> valid result;
- valid payload -> `LONG`;
- valid payload -> GatePolicy payload created;
- invalid payload -> safe reject;
- tied probabilities -> `NONE`;
- reporter summary and JSON serialization;
- CLI preview output;
- CLI export artifact;
- stage report coverage.

Full project validation is run with `python -m pytest`.

Final validation result:

```text
241 passed, 1 warning
```

The one FastAPI/Starlette warning is accepted and is not related to the ML21 runtime binding layer.

## Current project state after Stage ML21

Stage ML21 introduces the real PredictionService to GatePolicy runtime binding, but the external API response is not changed yet.

The service still does not connect to traders-core, live trading, or orders, and it does not open trades.

## Next stage

Next:

```text
ML22 - API response with GatePolicy block
```
