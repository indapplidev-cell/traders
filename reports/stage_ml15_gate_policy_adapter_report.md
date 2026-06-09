# Stage ML15 — GatePolicy Adapter Layer

## Status

Stage ML15 completed.

The GatePolicy layer can now accept raw ML/evaluation-style payload dictionaries through an isolated adapter pipeline.

## Purpose

Stage ML15 prepares GatePolicy for future integration with real ML analytics data.

The implemented flow is:

```text
raw dict payloads
→ GatePolicyEvaluationAdapter
→ GatePolicyInput
→ GatePolicyDiagnosticsService
→ GatePolicyResult
→ GatePolicyDiagnosticsReport
→ GatePolicyAdapterReporter
→ JSON / CLI / file export
```

## Important restriction

Stage ML15 does not connect GatePolicy to trading execution.

Stage ML15 does not:

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

### Adapter layer

- `app/gates/gate_policy_adapter.py`
- `app/gates/gate_policy_adapter_diagnostics.py`
- `app/gates/gate_policy_adapter_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_adapter.py`
- `tests/test_gate_policy_adapter_diagnostics.py`
- `tests/test_gate_policy_adapter_reporter.py`
- `tests/test_gate_policy_adapter_cli.py`
- `tests/test_gate_policy_adapter_export_cli.py`

## Implemented components

### GatePolicyEvaluationAdapter

Added conversion from raw dictionaries into `GatePolicyInput`.

Supported input aliases include:

- `regime`, `market_regime`, `detected_regime`;
- `direction`, `predicted_direction`, `signal_direction`, `side`;
- `confidence`, `model_confidence`, `signal_confidence`;
- `tp_before_sl_probability`, `tp_before_sl_prob`, `take_profit_before_stop_loss_probability`;
- `risk_score`, `model_risk_score`;
- `expected_move_atr`, `expected_atr_move`;
- `model_total_r`, `ml_total_r`, `total_r`;
- `baseline_total_r`, `baseline_r`;
- `model_profit_factor`, `ml_profit_factor`, `profit_factor`;
- `baseline_profit_factor`;
- `sample_count`, `samples`, `n`.

The adapter uses safe defaults for missing or invalid values.

### GatePolicyAdapterDiagnosticsService

Added end-to-end diagnostics for raw payloads.

The service evaluates this chain:

```text
raw payloads
→ adapted GatePolicyInput objects
→ GatePolicyResult objects
→ GatePolicyDiagnosticsReport
```

### GatePolicyAdapterReporter

Added JSON-safe serialization for adapter diagnostics result.

The reporter outputs:

- `input_count`;
- `result_count`;
- `report`;
- `inputs`;
- `results`;
- `decision_sequence`;
- `allowed_sequence`.

It also makes metadata JSON-safe.

### CLI preview

Added:

```powershell
python -m app.cli.commands gate-policy-adapter-preview
```

This prints adapter diagnostics JSON to the terminal.

Expected demo summary:

```json
{
  "raw_payload_count": 4,
  "input_count": 4,
  "result_count": 4,
  "report": {
    "total": 4,
    "allowed_total": 2,
    "blocked_total": 2
  }
}
```

Expected decisions:

```text
ALLOW_LONG
ALLOW_SHORT
BAD_REGIME
LOW_CONFIDENCE
```

### CLI export

Added:

```powershell
python -m app.cli.commands gate-policy-adapter-export
```

This writes adapter diagnostics JSON to:

```text
reports/gate_policy_adapter_preview_report.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Validation

Stage ML15 validation target:

```text
python -m pytest
131 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Current project state after Stage ML15

GatePolicy now has two completed layers:

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

## Next planned stage

Next stage should be:

```text
Stage ML16.1 — Prediction Payload Contract Discovery
```

The goal is to inspect existing prediction/evaluation models and define the first real payload contract for future GatePolicy integration.

Still no live trading.
Still no auto model activation.
Still no traders-core connection.
