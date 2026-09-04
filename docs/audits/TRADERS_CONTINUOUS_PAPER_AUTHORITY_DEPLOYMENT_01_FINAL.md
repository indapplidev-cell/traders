# Continuous PAPER authority deployment — final evidence

```text
TASK = TRADERS_CONTINUOUS_PAPER_AUTHORITY_DEPLOYMENT_01
FINAL_VERDICT = PASS_DEPLOYED_CONTINUOUS_PAPER
RECONCILED_AT_UTC = 2026-09-04T14:43:11Z
IMPLEMENTATION_COMMIT = d591adcf14ccba6482968687603f3f313e05bf04
READINESS_SERIALIZATION_FIX_COMMIT = d3615b093e600080b794d55a80a05bc6efa0a3bc
RESERVED_CYCLE_RECOVERY_FIX_COMMIT = ed84a649521f816560eb7c5ccd478e5007df3887
DEPLOYMENT_HEALTH_FIX_COMMIT = a122963a7d3e2c746adf652807d2be87c1675ee4
CLIENT_IMPLEMENTATION_COMMIT = 8070ef289f5431afa82feee7a2aa23a240441617
```

## Accepted state

- Production authority is `CONTINUOUS_ARMED`, generation `12`, mode version `1`.
- Production schema is exactly `0024_continuous_paper_authority`.
- Continuous entry authority is limited to `trade-5m-v2`; historical v1 and the
  15m runtime were not broadened or restarted.
- `LIVE_ALLOWED = false`. No exchange order path was enabled.
- Budgets are persistent and UTC-day scoped: 10 commands/day, 50 bps risk/day,
  and 0.5 USDT realized-loss/day; one command and 10 bps were consumed at the
  observation boundary.
- Selection remains deterministic, with at most one new command per polling
  cycle and at most one OPEN/CLOSING position globally.
- A reservation committed before a transient readiness failure is retried only
  for its exact deterministic candidate. An expired reservation is terminalized
  safely, and reservation races return a fail-safe result rather than killing
  the worker.
- Emergency stop and risk pause remain durable states.

## Verification

```text
SERVER_COMPILE = PASS
CONTINUOUS_POSTGRES16_E2E = 2 passed, 6 deselected
DEPLOYMENT_HEALTH_TESTS = 8 passed
EARLIER_FOCUSED_SERVER_REGRESSION = 1730 passed
EARLIER_SERVER_API_REGRESSION = 153 passed, 7 skipped
EARLIER_CLIENT_FOCUSED = 73 passed, 2 skipped, 1634 subtests
READONLY_CONTAINER = HEALTHY
OPERATOR_CONTAINER = HEALTHY
OPERATOR_IMAGE = sha256:defbd7a57ada6b7126c5a85d56ed3998b8df079fcc9924644755cd96a5abdf32
READONLY_IMAGE = sha256:620362c6fb89759e95507ec415103943a11edcbd40901b910868347fffb15a65
RUNTIME_HEALTH = selector_active=true, approval_watcher_active=true, execution_worker_active=true
```

The first normal production polling pass after recovery created one natural
PAPER `trade-5m-v2` / `5m` AVAXUSDT position. At the evidence boundary it was
`OPEN`; no artificial close, parameter search, strategy threshold change, or
bulk module-variant run was performed. Proof of a later natural close and a
subsequent production cycle is therefore deliberately pending and is not a
deployment blocker under the user's explicit direction.

## Production snapshot

```text
CONTROL = CONTINUOUS|CONTINUOUS_ARMED|enabled|generation12|mode_version1
BUDGET = commands1of10|risk10of50bps|realized_loss0of0.5USDT|loss_streak0
CURRENT_CYCLE = 05b4bd76-d21c-57b4-9896-c2d6616b9b7d
CURRENT_PROFILE = trade-5m-v2
CURRENT_TIMEFRAME = 5m
CURRENT_SYMBOL = AVAXUSDT
CURRENT_POSITION_STATE = OPEN
OPEN_OR_CLOSING_COUNT = 1
LIVE = FORBIDDEN
15M_CONTAINER_AT_EVIDENCE = 1e05edea0c65|UP_2_DAYS|NOT_RESTARTED_BY_TASK
```
