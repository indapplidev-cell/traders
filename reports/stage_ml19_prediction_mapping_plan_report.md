# Stage ML19 — Prediction Payload Mapping Plan

## Status

Stage ML19 completed.

The project now has a documented mapping-plan layer between real prediction payload fields and future GatePolicy input fields.

## Purpose

Stage ML19 was created to define how existing prediction output should be transformed into a future `GatePolicyInput`.

This stage is intentionally a plan/contract layer.

It does not connect GatePolicy to runtime prediction yet.

Implemented flow:

```text
prediction payload fields
→ mapping plan
→ mapping plan reporter
→ CLI preview
→ compact JSON file export
→ stage report
```

## Important restriction

Stage ML19 does not implement the runtime adapter yet.

Stage ML19 does not:

- import `app/prediction/predictor.py`;
- import `app/prediction/prediction_service.py`;
- call real model inference;
- read database state for GatePolicy;
- write database state for GatePolicy;
- activate models automatically;
- call traders-core;
- open trades;
- size positions;
- interact with live trading.

The current integration flag is:

```text
runtime_adapter_implemented: false
```

## Implemented files

### Mapping plan

- `app/gates/gate_policy_prediction_mapping_plan.py`

### Mapping plan reporter

- `app/gates/gate_policy_prediction_mapping_plan_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_prediction_mapping_plan.py`
- `tests/test_gate_policy_prediction_mapping_plan_reporter.py`
- `tests/test_gate_policy_prediction_mapping_plan_cli.py`
- `tests/test_gate_policy_prediction_mapping_plan_export_cli.py`

## CLI commands

### Preview

```powershell
python -m app.cli.commands gate-policy-prediction-mapping-plan-preview
```

This prints compact mapping plan summary JSON.

It does not include full `mapping_rules`, full `direction_rules`, or `all_target_fields`.

### File export

```powershell
python -m app.cli.commands gate-policy-prediction-mapping-plan-export
```

This writes compact mapping plan summary JSON to:

```text
reports/gate_policy_prediction_mapping_plan_summary.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Mapping plan identity

Current mapping plan identity:

```text
name: gate_policy_prediction_payload_mapping
version: ml19.1
```

## Required target fields

Required future GatePolicy target fields:

- `direction`
- `confidence`
- `tp_before_sl_probability`
- `regime`

## Optional target fields

Optional future GatePolicy target fields:

- `risk_score`
- `expected_move_atr`
- `model_version`
- `symbol`
- `interval`

The expected optional field list was explicitly fixed and protected by tests.

Correct required state:

```text
optional_target_count: 5
optional_target_fields: risk_score, expected_move_atr, model_version, symbol, interval
```

## Source fields

Source fields documented by the mapping plan:

- `confidence`
- `detected_regime`
- `expected_move_atr`
- `interval`
- `market_regime`
- `model_version`
- `prob_down`
- `prob_flat`
- `prob_up`
- `regime`
- `risk_score`
- `symbol`
- `tp_before_sl_probability`

## Direction mapping

Direction is a planned mapping from:

- `prob_up`
- `prob_down`
- `prob_flat`

Rules:

- `prob_up` strictly greater than `prob_down` and `prob_flat` → `LONG`
- `prob_down` strictly greater than `prob_up` and `prob_flat` → `SHORT`
- `prob_flat` strictly greater than `prob_up` and `prob_down` → `FLAT`
- missing, invalid, negative, non-numeric or tied probabilities → `NONE`

## Field mapping rules

### `direction`

Source fields:

- `prob_up`
- `prob_down`
- `prob_flat`

Mapping type:

```text
probability_argmax
```

Fallback:

```text
NONE when probabilities are missing, invalid or tied without confidence.
```

### `confidence`

Source field:

- `confidence`

Mapping type:

```text
direct_float
```

Fallback:

```text
0.0 when confidence is missing or invalid.
```

### `tp_before_sl_probability`

Source field:

- `tp_before_sl_probability`

Mapping type:

```text
direct_float
```

Fallback:

```text
0.0 when tp_before_sl_probability is missing or invalid.
```

### `risk_score`

Source field:

- `risk_score`

Mapping type:

```text
direct_float
```

Fallback:

```text
None when risk_score is missing.
```

### `expected_move_atr`

Source field:

- `expected_move_atr`

Mapping type:

```text
direct_float
```

Fallback:

```text
None when expected_move_atr is missing.
```

### `regime`

Source aliases:

- `regime`
- `market_regime`
- `detected_regime`

Mapping type:

```text
alias_first_present
```

Fallback:

```text
unknown when regime is missing.
```

### `model_version`

Source field:

- `model_version`

Mapping type:

```text
metadata_traceability
```

`model_version` is not required by GatePolicy decision logic yet, but should be preserved for diagnostics and reports.

### `symbol`

Source field:

- `symbol`

Mapping type:

```text
metadata_traceability
```

`symbol` is preserved for diagnostics and reports.

### `interval`

Source field:

- `interval`

Mapping type:

```text
metadata_traceability
```

`interval` is preserved for diagnostics and reports.

## Validation

Stage ML19 validation target:

```text
python -m pytest
203 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Important fix during Stage ML19

During Stage ML19.3, CLI preview originally showed inconsistent optional fields:

```text
optional_target_count: 5
optional_target_fields: only 3 fields
```

This was fixed.

The final expected state is:

```text
optional_target_count: 5
optional_target_fields: risk_score, expected_move_atr, model_version, symbol, interval
```

A subprocess test was added so that the real command path is checked:

```powershell
python -m app.cli.commands gate-policy-prediction-mapping-plan-preview
```

## Current project state after Stage ML19

GatePolicy supporting layers now include:

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

### Stage ML19

Prediction payload mapping plan layer:

- mapping plan;
- mapping plan reporter;
- CLI preview;
- compact file export;
- stage report.

## Next planned stage

Next stage should be:

```text
Stage ML20.1 — Prediction Runtime Adapter Contract
```

The goal is to prepare a contract for a future runtime adapter.

Important: Stage ML20.1 should still be a contract/test-first step.

It should not directly connect GatePolicy to the real prediction service yet.

The next stage should define:

- adapter input contract;
- adapter output contract;
- validation errors;
- safe handling of missing probabilities;
- safe handling of invalid probabilities;
- safe handling of missing regime;
- metadata preservation for `model_version`, `symbol`, and `interval`;
- `runtime_adapter_implemented` should remain false until the real adapter is actually implemented.

Still no live trading.
Still no auto model activation.
Still no traders-core connection.
Still no database writes for GatePolicy.
Still no direct execution.
