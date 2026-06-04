# Stage 6.5 - Update Terminal Demo Pipeline for Backtest Analytics

## Goal

Update the local terminal demo script to show Stage 6 backtest analytics and session comparison.

## Created files

- reports/stage6_5_terminal_demo_report.md

## Changed files

- scripts/demo_traders_pipeline.py
- tests/test_demo_traders_pipeline.py

## Added demo stages

- backtest-run
- backtest-performance
- backtest-history
- session-compare

## Corrected stage order

1. health
2. async-health
3. strategy-list
4. load-history
5. analyze
6. backtest
7. backtest-run
8. backtest-performance
9. backtest-history
10. runner-start
11. runner-history
12. runner-ticks
13. performance-session
14. performance-history
15. session-compare
16. portfolio-analytics

## Demo command

```powershell
.venv\Scripts\python .\scripts\demo_traders_pipeline.py --symbol BTCUSDT --interval 15m --days 7 --ticks 3 --initial-cash 1000
```

## Expected terminal result

- health: OK
- async-health: OK
- strategy-list: OK
- load-history: OK
- analyze: OK
- backtest: OK
- backtest-run: OK
- backtest-performance: OK
- backtest-history: OK
- runner-start: OK
- runner-history: OK
- runner-ticks: OK
- performance-session: OK
- performance-history: OK
- session-compare: OK
- portfolio-analytics: OK

## Safety

- live trading was not added
- Binance private API was not added
- real order execution was not added
- server deploy was not touched

## Validation

Final local validation completed:

- tests/test_demo_traders_pipeline.py: passed
- pytest: passed
- ruff: All checks passed
- alembic current: 0007_backtest_metrics (head)
- demo_traders_pipeline.py: success
- backtest-run: OK
- backtest-performance: OK
- backtest-history: OK
- session-compare: OK
- demo output language: Russian
