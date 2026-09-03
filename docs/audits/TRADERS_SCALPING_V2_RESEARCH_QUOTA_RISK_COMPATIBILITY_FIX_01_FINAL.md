# Scalping v2 research-quota risk compatibility fix 01

## Verdict

```text
FINAL_VERDICT = PASS
TASK = TRADERS_SCALPING_V2_RESEARCH_QUOTA_RISK_COMPATIBILITY_FIX_01
IMPLEMENTATION_COMMIT = fc06bb5810384e7c027c9da24c3ef64a454f1ca6
RECONCILED_AT_UTC = 2026-09-03T23:56:56Z
```

The production `trade-5m-v2` funnel incorrectly used the process-memory
research-frequency limits (3 preapprovals per symbol, 6 per direction, and 10
total per UTC day) as the `RISK_COMPATIBILITY_ADMITTED` gate. After the quota
was consumed, every otherwise compatible strategy candidate was rejected as
`RISK_REJECT_RESEARCH_LIMIT_EXCEEDED` for the rest of the UTC day. This caused
the rolling rejection count observed in the Desktop client to rise from 210 to
219 and later to 259.

These counters are not account exposure. The authoritative v2 execution chain
already applies controlled sizing at 10 bps per trade, at most two concurrent
positions, a 50 bps maximum total open risk, final approval, deterministic
selection, and the bounded PAPER command/position policy.

## Fix

`RiskConfig` now makes research-frequency enforcement explicit. The v2
production pipeline disables that research-only gate and records
`research_preapproval_limits_enforced=false` in the risk context. Legacy 15m
and historical 5m-v1 behavior retains the existing frequency-limit default.
All safety, strategy compatibility, score, direction, geometry, cost, RR,
quantity, portfolio, final-approval, and execution gates remain unchanged.

## Validation

```text
FOCUSED_RISK_AND_ORCHESTRATOR = 36 passed, 5 skipped
EXPANDED_RISK_ORCHESTRATOR_FUNNEL_V2 = 206 passed, 5 skipped
EXPANDED_KNOWN_STALE_FAILURE = 1 historical parallel-profile test still names retired trade-5m-v1
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
```

The known expanded-suite failure occurs before the changed risk logic: its
fixture requires `trade-5m-v1`, while the deployed parallel profile registry
now correctly requires `trade-5m-v2`.

## Controlled deployment acceptance

Only `online-orchestrator-5m` was rebuilt and recreated. PostgreSQL, market
data, the 15m orchestrator, Readonly API, and Operator Control were not
recreated.

```text
DEPLOYED_SOURCE = fc06bb5810384e7c027c9da24c3ef64a454f1ca6
DEPLOYED_IMAGE = sha256:de4bd063ab0a55d16e2e745369a0bd886d897251d6263c34835f58eda1909687
ROLLBACK_IMAGE = sha256:10166d385b1ab6a9ae954d50b92379b91410232dfe37eb9d3961ad35ead5eaed
CONTAINER_STATE = running
CONTAINER_RESTART_COUNT = 0
PROFILE_OWNER = ACQUIRED
HEALTH = OK
CONTROL = HEALTHY_ARMED_GENERATION_10
LIVE = DISABLED
```

The first natural post-deploy complete boundary was
`1788479700000` (`2026-09-03T23:55:00Z`) with 10/10 symbols. Two candidates
passed strategy and both passed risk compatibility:

```text
STRATEGY_ADMITTED = 2
RISK_COMPATIBILITY_ADMITTED = 2
RISK_COMPATIBILITY_REJECTED = 0
RISK_COMPATIBILITY_DOMINANT_REASON = NONE
```

BNBUSDT then stopped at target/economic geometry and ETHUSDT at the causal stop
envelope. That is the intended order: compatible candidates reach the actual
model gates instead of being hidden by a research-frequency counter. No signal
was forced, no private API was used, no Binance order was sent, and no position
was opened during this acceptance cycle.

The rolling one-hour/four-hour UI counters retain historical pre-fix rows until
those rows naturally age out of their windows. New post-deploy cycles no longer
add `RISK_REJECT_RESEARCH_LIMIT_EXCEEDED` for v2.
