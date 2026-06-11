# Stage ML23 - GatePolicy replay/evaluation layer

## Status

Stage ML23 completed.

This stage adds a GatePolicy replay/evaluation layer over existing prediction payload sequences.

## Implemented files

- `app/evaluation/gate_policy_replay_evaluator.py`
- `app/evaluation/gate_policy_replay_reporter.py`
- `app/cli/commands.py`
- `tests/test_gate_policy_replay_evaluator.py`
- `tests/test_gate_policy_replay_reporter.py`
- `tests/test_gate_policy_replay_cli.py`
- `tests/test_stage_ml23_gate_policy_replay_evaluation_report.py`
- `reports/stage_ml23_gate_policy_replay_evaluation_report.md`

## Evaluator

Created evaluator:

`app/evaluation/gate_policy_replay_evaluator.py`

It accepts in-memory prediction payload lists and evaluates them through:

```text
prediction payload sequence
-> ML22 API GatePolicy block builder
-> ML21 runtime binding
-> GatePolicy replay/evaluation records
-> aggregate metrics
```

The evaluator does not require `PredictionService`.

Safe integration flags are:

```text
runtime_binding_used: true
gate_policy_used: true
prediction_service_required: false
database_connected: false
database_writes: false
traders_core_connected: false
live_trading_connected: false
orders_enabled: false
```

## Reporter

Created reporter:

`app/evaluation/gate_policy_replay_reporter.py`

It provides:

- full summary with records;
- compact summary without records;
- JSON serialization for both shapes.

## Metrics

The replay/evaluation summary counts:

- total records;
- valid records;
- invalid records;
- valid and invalid ratios;
- direction counts for `LONG`, `SHORT`, `FLAT`, `NONE`;
- GatePolicy allowed count;
- GatePolicy blocked count;
- GatePolicy none count;
- issue counts;
- top issue codes;
- sample size.

## invalid payloads and direction NONE

Invalid payloads do not break evaluation.

They are reported as invalid records with issues and a safe blocked GatePolicy result.

direction NONE is counted explicitly and does not produce an unsafe allow.

## CLI

Added commands:

```powershell
python -m app.cli.commands gate-policy-replay-evaluate-preview
python -m app.cli.commands gate-policy-replay-evaluate-export
```

The preview prints a compact JSON summary for a sample payload set.

The export writes a runtime artifact to:

```text
reports/gate_policy_replay_evaluation_summary.json
```

## Safety and scope

This evaluation layer does not open trades.

It does not:

- create orders;
- create trades;
- connect to live trading;
- connect to traders-core;
- write to the database for GatePolicy replay;
- change database schema;
- touch Alembic.

The database was not changed.
Alembic was not touched.

## Validation

ML23 adds tests for:

- evaluator record and summary logic;
- reporter full and compact serialization;
- CLI preview/export;
- stage report coverage.

Full project validation is run with `python -m pytest`.

Final validation result:

```text
256 passed, 1 warning
```

The one FastAPI/Starlette warning is accepted and is not related to the ML23 GatePolicy replay/evaluation layer.

## Next stage

Next:

```text
ML24 - Final standalone traders-ml readiness audit
```
