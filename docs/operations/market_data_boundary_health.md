# Market-data boundary-aware health contract

The market-data health report distinguishes an ordinary synchronization
allowance from a real recovery or failure. The public status vocabulary remains
backward compatible:

```text
OK, STALE, GAP_DETECTED, RECOVERING, DEGRADED,
DISCONNECTED, ERROR, NOT_CONFIGURED
```

The additive `MARKET_DATA_HEALTH/2.0` fields carry the operational contract.

## Boundary timing

All boundary and deadline decisions use exchange-adjusted UTC milliseconds:

```text
expected_boundary = latest expected candle open + timeframe duration
deadline = expected_boundary + configured freshness allowance
```

The exact deadline is inclusive. The existing allowances are unchanged:

| Timeframe | Allowance |
|---|---:|
| 1m | 10 seconds |
| 5m | 15 seconds |
| 15m | 20 seconds |
| 1h | 60 seconds |
| 4h | 90 seconds |
| 1d | 120 seconds |

## Operational states

`status=OK`, `reason_code=HEALTHY_CURRENT` means the latest expected candle is
stored with no active gap or error.

`status=OK`, `reason_code=BOUNDARY_WITHIN_GRACE`,
`timing_state=WITHIN_GRACE`, `operational=true`, `ready=true`, and
`acceptance_blocking=false` means a new boundary has closed, its candle is not
yet committed, the configured deadline has not expired, runtime progress is
current, and no real gap or active error exists. This state is operational and
must not create a production unhealthy incident.

After the deadline, a progressing recovery is `RECOVERING` with
`RECOVERY_AFTER_DEADLINE`. A known multi-candle or explicitly detected gap is
blocking with `REAL_GAP_RECOVERY`. Missing runtime progress is `DEGRADED` with
`RUNTIME_NO_PROGRESS`. Active exchange/database errors remain blocking.

## Compatibility

Old readers may continue to use `overall_status`; within-grace reports retain
`overall_status=OK`. New readers use `operational`, `ready`,
`acceptance_blocking`, `reason_code`, `within_grace_count`, and
`deadline_expired_count`. Unknown or non-operational new reports fail closed.
Old v1 reports without the additive fields remain readable through the legacy
`overall_status=OK` fallback.

The JSON writer continues to write a sibling temporary file and atomically
replace the target.
