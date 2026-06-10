# Stage ML17 — Prediction Discovery Layer

## Status

Stage ML17 completed.

The project now has a safe text-based discovery layer for existing prediction/evaluation-related files.

## Purpose

Stage ML17 was created to avoid connecting GatePolicy to `prediction_service.py` blindly.

The implemented flow is:

```text
project files
→ text-based prediction discovery scanner
→ discovery report
→ discovery reporter
→ CLI compact summary
→ compact JSON file export
```

The discovery layer scans files as text and does not import the actual prediction service.

## Important restriction

Stage ML17 does not integrate GatePolicy with real prediction services.

Stage ML17 does not:

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

### Discovery layer

- `app/gates/gate_policy_prediction_discovery.py`
- `app/gates/gate_policy_prediction_discovery_reporter.py`

### CLI integration

- `app/cli/commands.py`

### Tests

- `tests/test_gate_policy_prediction_discovery.py`
- `tests/test_gate_policy_prediction_discovery_reporter.py`
- `tests/test_gate_policy_prediction_discovery_cli.py`
- `tests/test_gate_policy_prediction_discovery_export_cli.py`

## CLI commands

### Compact summary

```powershell
python -m app.cli.commands gate-policy-prediction-discovery-summary
```

This prints compact discovery summary JSON.

It does not include the full `files` list.

### File export

```powershell
python -m app.cli.commands gate-policy-prediction-discovery-export
```

This writes compact discovery summary JSON to:

```text
reports/gate_policy_prediction_discovery_summary.json
```

The generated JSON file is a runtime artifact and must not be committed.

## Latest observed discovery summary

Latest observed manual discovery summary:

```text
total_files: 144
files_with_content_matches: 138
unique_content_keyword_count: 14
unique_name_keyword_count: 10
```

Counts can change when new files are added.

## Content keywords found

The discovery layer found these content keywords:

- `baseline`
- `confidence`
- `expected_move_atr`
- `model_version`
- `prediction`
- `predictor`
- `prob_down`
- `prob_flat`
- `prob_up`
- `profit_factor`
- `regime`
- `risk_score`
- `total_r`
- `tp_before_sl_probability`

## Name keyword families found

The discovery layer found these name keyword families:

- `baseline`
- `confidence`
- `evaluation`
- `evaluator`
- `model`
- `predict`
- `prediction`
- `probability`
- `profit`
- `regime`

## Important discovered directions

The discovery output points to these important project areas for future mapping.

### Prediction runtime

- `app/prediction/predictor.py`
- `app/prediction/prediction_service.py`

These are likely the most important files for future real prediction payload mapping.

### API schemas

- `app/api/schemas.py`
- `app/api/routes_predict.py`

These files are likely useful for understanding external prediction response shape.

### Evaluation and signal gates

- `app/evaluation/signal_gate_evaluator.py`
- `app/evaluation/profit_aware_evaluator.py`
- `app/evaluation/profit_aware_evaluator_v2.py`
- `app/evaluation/confidence_gate_evaluator.py`
- `app/evaluation/calibration_evaluator.py`

These files are likely useful for understanding current probability/confidence/profit-aware evaluation structures.

### Diagnostics

- `app/diagnostics/prediction_probability_diagnostics.py`
- `app/diagnostics/prediction_bias_root_cause.py`
- `app/diagnostics/prediction_collapse_detector.py`
- `app/diagnostics/prediction_diagnostics.py`

These files are likely useful for understanding model output quality and failure modes.

### Replay

- `app/replay/historical_replay_engine.py`
- `app/replay/replay_models.py`

These files are likely useful for future historical replay integration.

### Database models and repositories

- `app/db/models.py`
- `app/db/repositories/prediction_repository.py`

These files are relevant later, but Stage ML17 did not connect to DB.

## Validation

Stage ML17 validation target:

```text
python -m pytest
165 passed
```

One FastAPI/Starlette warning is currently accepted and is not related to GatePolicy.

## Current project state after Stage ML17

GatePolicy now has four completed layers:

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

- text-based discovery scanner;
- discovery reporter;
- CLI compact summary;
- compact file export;
- stage report.

## Next planned stage

Next stage should be:

```text
Stage ML18.1 — Prediction Runtime Shape Discovery
```

The goal is to inspect existing prediction runtime structures more narrowly:

- `app/prediction/predictor.py`
- `app/prediction/prediction_service.py`
- `app/api/schemas.py`
- `tests/test_predictor.py`
- `tests/test_prediction_service.py`
- `tests/test_api_predict.py`

Still no live trading.
Still no auto model activation.
Still no traders-core connection.
Still no database writes for GatePolicy.
Still no direct GatePolicy integration.