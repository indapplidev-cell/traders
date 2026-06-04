# Stage 6 - Strategy Backtest Analytics and Session Comparison Hardening

## Goal

Stage 6 adds local backtest analytics and hardened session comparison.

## Created files

- app/backtest/backtest_runner.py
- app/analytics/backtest_performance.py
- app/analytics/session_comparison.py
- alembic/versions/0007_backtest_session_metrics.py
- tests/test_backtest_performance.py
- tests/test_backtest_runner.py
- tests/test_session_comparison.py
- tests/test_backtest_cli.py
- reports/stage6_backtest_analytics_report.md

## Changed files

- app/db/models.py
- app/cli/commands.py

## Added tables

- backtest_sessions
- backtest_session_metrics

## Added migration

- revision: 0007_backtest_metrics
- down_revision: 0006_runner_metrics

## Added CLI commands

- backtest-run
- backtest-performance
- backtest-history
- session-compare

## Validation

Final local validation completed:

- pytest: 116 passed
- ruff: All checks passed
- alembic upgrade head: success
- alembic current: 0007_backtest_metrics (head)
- alembic downgrade 0006_runner_metrics: success
- alembic upgrade head after downgrade: success
- alembic current after downgrade/upgrade: 0007_backtest_metrics (head)
- backtest-run: success
- backtest-performance: success
- backtest-history: success
- runner-start: success
- session-compare: success

Archive validation:

- missing count: 0
- bad count: 0
- tmp count: 0
- has app: True
- has tests: True
- has alembic: True
- has reports: True

## Safety

- live trading was not added
- Binance private API was not added
- real order execution was not added
- futures were not added
- margin was not added
- leverage was not added
- short execution was not added
- server deploy was not touched
