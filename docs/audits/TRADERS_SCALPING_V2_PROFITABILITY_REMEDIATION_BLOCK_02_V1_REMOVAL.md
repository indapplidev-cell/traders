# Block 02 — Scalping v1 removal

```text
TASK_STATUS = PASS
ACTIVE_SCALPING_PROFILE = trade-5m-v2
SCALPING_V1_REGISTERED_PROFILE = NO
SCALPING_V1_RUNTIME_PARAMETERS = NO
SCALPING_V1_RISK_CONTRACT = NO
SCALPING_V1_GEOMETRY_ADMISSION = IMPOSSIBLE
SCALPING_V1_PAPER_EXECUTION = IMPOSSIBLE
HISTORICAL_DATABASE_ROWS = PRESERVED_READONLY
MIGRATIONS = PRESERVED
FOCUSED_TESTS = 19_PASS
LIVE = DISABLED
BINANCE_ORDER_API_CALLS = 0
FINAL_VERDICT = PASS
```

The profile enum, profile object, runtime parameter registration and risk
strategy contract no longer contain `trade-5m-v1`. Scalping setup, geometry and
PAPER execution accept only `trade-5m-v2`. Historical API/export literals and
migrations remain solely so persisted legacy rows can still be read.
