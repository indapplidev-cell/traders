# Stage 5.5 - Terminal Demo Pipeline

## Goal

Add a single local terminal demo script that shows the current paper-only trading pipeline in Russian.

## Created files

- scripts/demo_traders_pipeline.py
- reports/stage5_5_terminal_demo_report.md

## Changed files

None expected.

## Demo command

```powershell
.venv\Scripts\python .\scripts\demo_traders_pipeline.py --symbol BTCUSDT --interval 15m --days 7 --ticks 3
```

## Demo stages

- health
- async-health
- strategy-list
- load-history
- analyze
- backtest
- runner-start
- runner-history
- runner-ticks
- performance-session
- performance-history
- portfolio-analytics

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
- demo_traders_pipeline.py: success
- archive validation: passed

The demo output is in Russian.
