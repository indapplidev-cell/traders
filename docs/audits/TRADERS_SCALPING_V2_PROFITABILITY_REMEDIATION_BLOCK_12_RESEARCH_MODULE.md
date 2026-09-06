# Block 12 — manual offline parameter sweep

```text
TASK_STATUS = PASS
MODULE = app.research.scalping_v2_parameter_sweep
SEARCH_SPACE = config/research/scalping_v2_parameter_sweep.yaml
MANUAL_COMMAND = python -m app.research.scalping_v2_parameter_sweep --config config/research/scalping_v2_parameter_sweep.yaml
OUTPUT = artifacts/scalping_v2_parameter_sweep/<run_id>/REPORT.md
SMOKE_VARIANTS = 2
FULL_SWEEP_RUN_BY_CODEX = NO
PRODUCTION_MUTATIONS = 0
BINANCE_ORDER_API_CALLS = 0
HOLDOUT_USED_FOR_SELECTION = NO
INSUFFICIENT_SAMPLE = EXPLICIT
```
