# Stage ML20 — Prediction Runtime Adapter Contract

## Status

Stage ML20 completed.

The project now has a contract/reporting/CLI/export layer for a future prediction runtime adapter.

This stage does not implement the real runtime adapter yet.

## Purpose

Stage ML20 was created to define and validate the expected shape of a future runtime prediction payload before it can be converted into GatePolicy-compatible input.

Implemented flow:

```text
raw runtime prediction payload
→ runtime adapter contract validation
→ contract reporter
→ CLI preview
→ compact JSON file export
→ stage report
```

## Important restriction

Stage ML20 does not implement the real runtime adapter yet.

Stage ML20 does not:

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

### Runtime adapter contract

- `app/gates/gate_policy_prediction_runtime_adapter_contract.py`

### Runtime adapter contract reporter

- `app/gates/gate_policy_prediction_runtime_adapter_contract_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_prediction_runtime_adapter_contract.py`
- `tests/test_gate_policy_prediction_runtime_adapter_contract_reporter.py`
- `tests/test_gate_policy_prediction_runtime_adapter_contract_cli.py`
- `tests/test_gate_policy_prediction_runtime_adapter_contract_export_cli.py`

## CLI commands

### Preview

```powershell
python -m app.cli.commands gate-policy-runtime-adapter-contract-preview
```

This prints compact runtime adapter contract summary JSON.

### File export

```powershell
python -m app.cli.commands gate-policy-runtime-adapter-contract-export
```

This writes compact runtime adapter contract summary JSON to:

```text
reports/gate_policy_runtime_adapter_contract_summary.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Contract identity

Current contract identity:

```text
contract_name: gate_policy_prediction_runtime_adapter_contract
contract_version: ml20.1
```

## Required probability fields

The runtime prediction payload must provide:

- `prob_up`
- `prob_down`
- `prob_flat`

These fields are used later for direction mapping.

## Required numeric fields

Required numeric fields:

- `prob_up`
- `prob_down`
- `prob_flat`
- `confidence`
- `tp_before_sl_probability`

Correct required state:

```text
required_numeric_count: 5
required_numeric_fields: prob_up, prob_down, prob_flat, confidence, tp_before_sl_probability
```

## Required context fields

Required context fields:

- `regime`

## Optional numeric fields

Optional numeric fields:

- `risk_score`
- `expected_move_atr`

Invalid optional numeric fields are normalized to `None`.

## Traceability fields

Traceability metadata fields:

- `model_version`
- `symbol`
- `interval`

These fields are preserved for diagnostics and reports.

## Future GatePolicy target fields

Future GatePolicy target fields:

- `direction`
- `confidence`
- `tp_before_sl_probability`
- `regime`
- `risk_score`
- `expected_move_atr`
- `model_version`
- `symbol`
- `interval`

## Validation policy

The contract validation layer handles payload problems safely.

Validation issue codes:

```text
missing_required_numeric_field
invalid_numeric_field
negative_probability
missing_required_context_field
```

Policy:

- missing required numeric field → error;
- invalid required numeric field → error;
- negative probability → error;
- missing required context field → error;
- invalid optional numeric field → normalize to `None`.

## JSON-safe result

The contract validation result can be converted to JSON-safe dict.

It includes:

- contract identity;
- validation status;
- required/optional/traceability field lists;
- normalized payload;
- metadata;
- issues;
- issue count;
- `runtime_adapter_implemented: false`.

## Reporter

The reporter provides:

- full contract report dict;
- compact summary dict;
- validation report dict;
- full contract report JSON;
- compact summary JSON;
- validation report JSON.

The reporter does not connect to real prediction service.

## CLI preview

The CLI preview prints compact JSON and includes guard checks.

It protects:

- `runtime_adapter_implemented` must remain `false`;
- `required_numeric_count` must match `required_numeric_fields`;
- `required_numeric_fields` must include:
  - `prob_up`
  - `prob_down`
  - `prob_flat`
  - `confidence`
  - `tp_before_sl_probability`
- traceability fields must be:
  - `model_version`
  - `symbol`
  - `interval`

## File export

The file export writes compact summary JSON to:

```text
reports/gate_policy_runtime_adapter_contract_summary.json
```

This file is not committed.

It must contain:

```text
required_numeric_count: 5
required_numeric_fields: prob_up, prob_down, prob_flat, confidence, tp_before_sl_probability
runtime_adapter_implemented: false
```

It must not contain:

```text
validation_policy
required_probability_fields
normalized_payload
issues
metadata
```

## Important fix during Stage ML20

During Stage ML20.3, CLI preview initially showed an inconsistent state:

```text
required_numeric_count: 5
required_numeric_fields: only 3 fields
```

Correct final state:

```text
required_numeric_count: 5
required_numeric_fields: prob_up, prob_down, prob_flat, confidence, tp_before_sl_probability
```

The final CLI preview output was verified manually.

## Validation

Stage ML20 validation target:

```text
python -m pytest
227 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy or runtime adapter contract.

## Current project state after Stage ML20

GatePolicy supporting layers now include:

### Stage ML14

GatePolicy core/service/report/export layer.

### Stage ML15

GatePolicy adapter layer.

### Stage ML16

Prediction payload contract layer.

### Stage ML17

Prediction discovery layer.

### Stage ML18

Prediction runtime shape layer.

### Stage ML19

Prediction payload mapping plan layer.

### Stage ML20

Prediction runtime adapter contract layer.

## Next planned stage

Next stage should be:

```text
Stage ML21.1 — Prediction Runtime Adapter Skeleton
```

Goal:

- create a skeleton adapter module;
- use Stage ML20 contract validation;
- use Stage ML19 mapping plan only as a reference;
- still avoid real prediction_service connection;
- still avoid predictor import;
- still avoid database access;
- still avoid traders-core connection;
- still avoid live trading;
- still avoid automatic model activation.

The adapter skeleton should be test-first and safe.

It should not open trades.
It should not size positions.
It should not call live execution.
