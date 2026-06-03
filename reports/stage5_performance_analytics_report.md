# Stage 5 — Strategy Performance Metrics and Paper Portfolio Analytics

## Goal

Stage 5 adds local paper-runner analytics:

- strategy performance metrics
- runtime tick aggregation
- risk gate metrics
- execution metrics
- confidence metrics
- market regime metrics
- paper portfolio analytics
- persisted runner session metrics
- CLI commands for performance inspection

## Created files

- app/analytics/__init__.py
- app/analytics/strategy_performance.py
- app/analytics/paper_portfolio_analytics.py
- alembic/versions/0006_runner_session_metrics.py
- tests/test_strategy_performance.py
- tests/test_paper_portfolio_analytics.py
- tests/test_performance_cli.py
- reports/stage5_performance_analytics_report.md

## Changed files

- app/db/models.py
- app/runtime/paper_runner.py
- app/cli/commands.py

## Added database table

- runner_session_metrics

## Added migration

- revision: 0006_runner_metrics
- down_revision: 0005_runner_audit

## Added CLI commands

- performance-session
- performance-history
- performance-compare
- portfolio-analytics

## Safety

- live trading was not added
- Binance private API was not added
- real order execution was not added
- futures were not added
- margin was not added
- leverage was not added
- short execution was not added
- server deploy was not touched
- server_deploy_report.md was not changed

## PnL policy

PnL is calculated only from local paper-trading data.

Unavailable metrics are shown as N/A.

No fake mark price is generated.

No rejected or skipped action is counted as an executed trade.

## Validation

Final local validation completed:

- pytest: 90 passed
- ruff: All checks passed
- alembic upgrade head: success
- alembic current: 0006_runner_metrics (head)
- alembic downgrade 0005_runner_audit: success
- alembic upgrade head after downgrade: success
- alembic current after downgrade/upgrade: 0006_runner_metrics (head)
- runner-start: success
- runner-history: success
- runner-ticks: success
- performance-session: success
- performance-history: success
- performance-compare: success
- portfolio-analytics: success

Archive validation:

- missing count: 0
- bad count: 0
- has app: True
- has tests: True
- has alembic: True
- has reports: True

Server deploy was not touched.
Live trading was not added.
