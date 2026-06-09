# Stage ML14 — GatePolicy Layer

## Status

Stage ML14 completed.

GatePolicy is implemented as an isolated risk-first ML signal admission layer.

## Purpose

GatePolicy answers one narrow question:

> Can this ML signal be trusted enough to pass further into the trading analysis pipeline?

GatePolicy does not trade.
GatePolicy does not open positions.
GatePolicy does not activate models automatically.
GatePolicy does not connect to traders-core.
GatePolicy does not read or write database state.

## Implemented files

### Core package

- `app/gates/__init__.py`
- `app/gates/gate_policy_models.py`
- `app/gates/gate_policy_service.py`
- `app/gates/gate_policy_diagnostics.py`
- `app/gates/gate_policy_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_service.py`
- `tests/test_gate_policy_diagnostics.py`
- `tests/test_gate_policy_reporter.py`
- `tests/test_gate_policy_cli.py`
- `tests/test_gate_policy_export_cli.py`

## Implemented components

### GatePolicy models

Added:

- `GatePolicyDecision`
- `GateDirection`
- `GatePolicyConfig`
- `GatePolicyInput`
- `GatePolicyResult`

Supported decisions:

- `ALLOW_LONG`
- `ALLOW_SHORT`
- `BLOCK`
- `MODEL_UNTRUSTED`
- `BASELINE_BETTER`
- `LOW_CONFIDENCE`
- `BAD_REGIME`

### GatePolicyService

Added `GatePolicyService.evaluate()`.

The service blocks signals when:

- direction is not tradeable;
- market regime is not trusted;
- confidence is below threshold;
- TP-before-SL probability is below threshold;
- risk score is too high;
- sample count is too low;
- baseline is better by total R;
- baseline is better by profit factor.

### GatePolicyDiagnosticsService

Added batch diagnostics over multiple `GatePolicyInput` signals.

The diagnostics report includes:

- total signal count;
- allowed count;
- blocked count;
- decision counts;
- regime counts;
- direction counts;
- reason counts.

### GatePolicyReporter

Added serialization layer:

- single result to dict;
- diagnostics report to dict;
- diagnostics report to JSON.

### CLI commands

Added:

```powershell
python -m app.cli.commands gate-policy-smoke
```

This prints demo GatePolicy diagnostics JSON.

Added:

```powershell
python -m app.cli.commands gate-policy-export
```

This writes demo GatePolicy diagnostics JSON to:

```text
reports/gate_policy_smoke_report.json
```

The generated JSON file is a runtime artifact and should not be committed.

## Expected smoke payload

The demo signal pack contains 5 signals:

- 2 allowed signals;
- 3 blocked signals.

Expected summary:

```json
{
  "total": 5,
  "allowed_total": 2,
  "blocked_total": 3
}
```

Expected decision categories:

- `ALLOW_LONG`
- `ALLOW_SHORT`
- `BAD_REGIME`
- `LOW_CONFIDENCE`
- `BLOCK`

## Validation

Stage ML14 validation target:

```text
python -m pytest
111 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Current restrictions

GatePolicy remains isolated.

Do not connect GatePolicy directly to:

- live trading;
- order execution;
- position sizing;
- traders-core;
- model activation;
- database writes.

Future integration must go through an explicit adapter/service layer.
