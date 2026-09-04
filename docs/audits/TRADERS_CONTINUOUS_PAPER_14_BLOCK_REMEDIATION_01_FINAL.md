# TRADERS_CONTINUOUS_PAPER_14_BLOCK_REMEDIATION_01

Reconciliation time: 2026-09-04 UTC

```text
TASK_STATUS = BLOCKED_EXTERNAL_ACCOUNT_COMMISSION_SNAPSHOT
FINAL_VERDICT = PARTIAL
BLOCKER_CODE = BINANCE_ACCOUNT_COMMISSION_SNAPSHOT_NOT_PROVISIONED
PAPER_AUTHORITY_MODE = CONTINUOUS
CONTROL_GENERATION = 12
CONTROL_PERSISTED_STATE = CONTINUOUS_ARMED
CONTROL_EFFECTIVE_STATE = PAUSED_BY_RISK_AFTER_DAILY_LOSS_BUDGET
LIVE = DISABLED
REAL_BINANCE_ORDER_API_CALLS = 0
SECRET_OUTPUT = 0
ALEMBIC_HEAD = 0024_continuous_paper_authority
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS
SCALPING_V2_AUTHORITATIVE_IMPLEMENTATION = PASS
SCALPING_V1_NEW_EXECUTION = FORBIDDEN
```

## Block commits 01-13

```text
01 046e8d6beaa27928d49a25d9d01e9f4cd4283ab5 paper: enforce continuous authority after normal close
02 2ee2bd5644f611c10a6e5e5dfbb614830bb3a08c paper: allow next natural winner without rearm
03 46d31d7bc3036a78a8f8225c23f51e8ececa894a selector: harden deterministic one-winner paper semantics
04 6e0786ad06b46cba302c99d165a7a55d904310c7 paper: reconcile command lifecycle after entry fill
05 cb72af7bccfe989fe09d1b308087c081615bacbb readonly: remove remaining generic unknown paper states
06 00bb8246a22f139e7268963320f91f3d6948b74e funnel: expose scalp cadence and winner execution metrics
07 f9068558640e415c3825ea7ff5dbc52ae18d68e9 analytics: add scalp v2 paper expectancy telemetry
08 a3e9a0929aeeee7aed24d691ef01a42d6806f765 costs: expose authoritative dynamic binance commission
09 187c7b287b8347e61d620f28a7765ebd71ffd378 client: separate active and closed paper positions
10 f23e9e76e181c44188a70d1e115d7e1460a1ea19 paper: replace continuous first-canary identity
11 869484515defd1cebb1e66fbfed1dcfe84606d87 readonly: define continuous budget semantics
12 b4e42573fe92fdeb54bc47bb70796ca125dfeca4 analytics: clarify paper performance sample context
13 bd23ce3d3075c6c3c164908f717c97957e7cba54 paper: harden restart-safe continuous budget accounting
```

Desktop commits for blocks 09-12 are `fbc7ebd`, `ec887c0`, `287cf5d`, and
`650b0ec`. The sibling desktop repository has no configured remote, so those
commits are local-only and cannot satisfy a push assertion.

## Verified acceptance

- Continuous authority remains persisted after normal close. Production
  generation 12 created and closed AVAX, then opened/closed ETH, then
  opened/closed BNB and ADA without manual re-arm.
- The isolated PostgreSQL 16 natural chain proves plan -> approval -> unique
  rank-1 winner -> command -> OPEN -> CLOSED -> next winner without re-arm.
- Command lifecycle projects PROCESSING after entry and COMPLETED after close;
  idempotent replay repairs stale legacy projection without duplicating rows.
- Readonly projections contain no generic UNKNOWN/UNAVAILABLE placeholders in
  the remediated PAPER fields. Closed positions are separated from active
  positions and the production active count is zero at this reconciliation.
- New continuous identity generation uses `paper:continuous:*`; existing
  `paper:first-canary:*` rows remain immutable historical records.
- Budget values expose unit, source, UTC window, reset boundary, and update
  time. Restart/double-close/day-reset tests prove durable exact-once counters.
- Funnel cadence distinguishes plan, selector winner, command, OPEN, and
  CLOSED counts. PAPER account telemetry exposes factual profile-isolated v2
  expectancy, costs, period, and sample count with
  `sample_status=THRESHOLD_NOT_DEFINED` and no automatic conclusion.
- Production account at reconciliation: seven closed v2 trades, three wins,
  four losses, net PnL `-0.575528638` USDT, profit factor
  `0.6651144417909044036226700043`. These losses are not masked.
- Daily loss `0.754155432` USDT exceeds the configured `0.5` USDT budget.
  Durable authority therefore blocks mutation with
  `DAILY_LOSS_BUDGET_EXHAUSTED`; the readonly effective state reconciliation
  is corrected to `PAUSED_BY_RISK` while persisted operator authority remains
  `CONTINUOUS_ARMED`.

## Tests

```text
FOCUSED_SERVER = 3422 passed, 2 skipped
DESKTOP_FULL = 1489 passed, 2 skipped, 3029 subtests passed
POSTGRES_NATURAL_E2E = 8 passed
POSTGRES_CANARY = 2062 passed
POSTGRES_REPOSITORY_LIFECYCLE = 1196 passed
POSTGRES_INGESTION_REVISION_PINNED = 261 passed
LEGACY_PREPARATION_CONTRACT = 1536 passed
TRADE_15M_PROFILE_COORDINATOR = 6 passed
MONOLITHIC_DISCOVERY = 31136 passed, 566 failed, 28 skipped, 3 errors
MONOLITHIC_FAILURE_CLASS = MUTUALLY_EXCLUSIVE_SCHEMA_PINNED_FIXTURES_PLUS_STALE_LEGACY_EXPECTATIONS
```

The monolithic command intentionally supplied every database fixture variable
at once. Several session-scoped legacy suites pin incompatible Alembic
revisions on shared URLs; their cascade is not a valid combined execution
mode. Relevant suites were rerun in separate processes and dedicated databases
with the passing results above. Remaining unrelated legacy failures are not
reported as a full-suite PASS.

## Deployment reconciliation

Readonly was rebuilt from block-13 source and became healthy with source label
`bd23ce3d3075c6c3c164908f717c97957e7cba54`. The final block-14 source labels
and container digests are resolved in the post-commit reconciliation.

The 5m orchestrator was deliberately not replaced. The host has no Binance API
credential binding and no protected value for
`TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH`. Creating a simulated or inferred
snapshot would violate the requirement for authoritative account-specific
commission, BNB-discount, special-commission, and tax-commission provenance.
Consequently the final deployed commit cannot yet be accepted, and a forced
natural proof on that commit would be misleading.

## Required next action

Provision a protected, less-than-24-hour Binance account commission snapshot
for every active symbol, mount it read-only into the 5m orchestrator, set
`TRADERS_BINANCE_COMMISSION_SNAPSHOT_PATH`, then deploy the final source and
observe one natural close followed by the next natural OPEN without re-arm.
