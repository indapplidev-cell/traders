# Stage 8 - Paper Runner Control Layer Report

## Status

DONE.

Stage 8 adds a safe paper runner control layer for bounded paper-only execution.

## Safety rules

The project remains paper-only:

- no live trading;
- no Binance private API;
- no real orders;
- no daemon;
- no server deploy;
- no unbounded runner.

## Main changes

The legacy `paper-runner` command is disabled.

The allowed entrypoint is:

```powershell
python -m app.cli.commands runner-start --strategy simple_trend --symbol BTCUSDT --interval 15m --ticks 3 --sleep-seconds 0
```

`--ticks` is required.

## Changed files

- app/cli/commands.py
- scripts/paper_runner_control_check.py
- tests/test_paper_runner_control_check.py
- scripts/local_runtime_check.py
- tests/test_local_runtime_check.py
- reports/stage8_paper_runner_control_report.md

## Verified behavior

`runner-start` without `--ticks`

```text
Missing option '--ticks'
```

`runner-start` with `--ticks 0`

```text
ERROR: ticks must be > 0
```

`runner-start` with `--ticks 3`

```text
status: STOPPED
ticks requested: 3
ticks completed: 3
```

`paper-runner`

```text
ERROR: paper-runner is disabled for Stage 8. Use runner-start with explicit --ticks for bounded paper-only execution.
```

## Latest checks

- pytest tests/test_paper_runner_control_check.py -> 9 passed
- ruff check tests/test_paper_runner_control_check.py -> All checks passed
- pytest tests/test_runner_cli.py -> 3 passed
- ruff check . -> All checks passed
- paper_runner_control_check.py -> СТАТУС: УСПЕХ

## Required final verification

```powershell
python -m py_compile app/cli/commands.py
python -m py_compile scripts/paper_runner_control_check.py
pytest tests/test_paper_runner_control_check.py
pytest tests/test_runner_cli.py
pytest tests/test_local_runtime_check.py
pytest
ruff check .
alembic current
.venv\Scripts\python .\scripts\paper_runner_control_check.py --symbol BTCUSDT --interval 15m --ticks 3 --initial-cash 1000
.venv\Scripts\python .\scripts\local_runtime_check.py --symbol BTCUSDT --interval 15m --days 7 --ticks 3 --initial-cash 1000
```

## Expected final result

- pytest: passed
- ruff: All checks passed
- alembic current: 0007_backtest_metrics (head)
- paper_runner_control_check.py: СТАТУС: УСПЕХ
- local_runtime_check.py: СТАТУС: УСПЕХ
