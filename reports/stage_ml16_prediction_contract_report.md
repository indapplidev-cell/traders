# Stage ML16 — Prediction Payload Contract

## Status

Stage ML16 completed.

The project now has a documented and test-covered GatePolicy prediction payload contract.

## Purpose

Stage ML16 defines the payload shape that future prediction/evaluation outputs must use before they can be adapted into `GatePolicyInput`.

The implemented flow is:

```text
prediction/evaluation payload contract
→ contract reporter
→ CLI preview
→ file export
```

This stage does not connect the contract to real model inference yet.

## Important restriction

Stage ML16 does not integrate GatePolicy with live prediction services.

Stage ML16 does not:

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

### Contract layer

- `app/gates/gate_policy_prediction_contract.py`
- `app/gates/gate_policy_prediction_contract_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_prediction_contract.py`
- `tests/test_gate_policy_prediction_contract_reporter.py`
- `tests/test_gate_policy_prediction_contract_cli.py`
- `tests/test_gate_policy_prediction_contract_export_cli.py`

## Contract name

```text
gate_policy_prediction_payload
```

## Contract version

```text
ml16.1
```

## Required fields

The required fields are:

- `regime`
- `direction`
- `confidence`
- `tp_before_sl_probability`

## Optional fields

The optional fields are:

- `risk_score`
- `expected_move_atr`
- `model_total_r`
- `baseline_total_r`
- `model_profit_factor`
- `baseline_profit_factor`
- `sample_count`

## Supported field aliases

### regime

- `regime`
- `market_regime`
- `detected_regime`

### direction

- `direction`
- `predicted_direction`
- `signal_direction`
- `side`

### confidence

- `confidence`
- `model_confidence`
- `signal_confidence`

### tp_before_sl_probability

- `tp_before_sl_probability`
- `tp_before_sl_prob`
- `take_profit_before_stop_loss_probability`

### risk_score

- `risk_score`
- `model_risk_score`

### expected_move_atr

- `expected_move_atr`
- `expected_atr_move`

### model_total_r

- `model_total_r`
- `ml_total_r`
- `total_r`

### baseline_total_r

- `baseline_total_r`
- `baseline_r`

### model_profit_factor

- `model_profit_factor`
- `ml_profit_factor`
- `profit_factor`

### baseline_profit_factor

- `baseline_profit_factor`

### sample_count

- `sample_count`
- `samples`
- `n`

## Supported direction aliases

Direction aliases are normalized as:

- `UP` → `LONG`
- `BUY` → `LONG`
- `LONG` → `LONG`
- `DOWN` → `SHORT`
- `SELL` → `SHORT`
- `SHORT` → `SHORT`
- `FLAT` → `FLAT`
- `SIDEWAYS` → `FLAT`
- `NONE` → `NONE`
- `NO_TRADE` → `NONE`

## Known regime values

Known regime values are:

- `trend_up`
- `trend_down`
- `breakout_setup`
- `range`
- `high_volatility`
- `low_volatility`
- `low_liquidity`
- `unknown`

## Contract reporter

Added:

```text
GatePolicyPredictionContractReporter
```

The reporter can produce:

- full contract dict;
- contract summary dict;
- full contract JSON;
- contract summary JSON.

## CLI preview

Added:

```powershell
python -m app.cli.commands gate-policy-prediction-contract-preview
```

This prints the full contract JSON to the terminal.

## CLI export

Added:

```powershell
python -m app.cli.commands gate-policy-prediction-contract-export
```

This writes the contract JSON to:

```text
reports/gate_policy_prediction_contract_report.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Validation

Stage ML16 validation target:

```text
python -m pytest
149 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Current project state after Stage ML16

GatePolicy now has three completed layers:

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

## Next planned stage

Next stage should be:

```text
Stage ML17.1 — Existing Prediction Service Discovery
```

The goal is to inspect existing prediction-related modules and document what real output structures already exist in the project.

Still no live trading.
Still no auto model activation.
Still no traders-core connection.
Still no database writes for GatePolicy.
