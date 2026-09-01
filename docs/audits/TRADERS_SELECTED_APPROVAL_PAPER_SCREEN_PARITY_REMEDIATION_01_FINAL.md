# TRADERS selected approval / PAPER screen parity remediation 01

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS
ROOT_CAUSE = FUNNEL_RECOMPUTED_SELECTED_FOR_HISTORICAL_PLANS_WHILE_EXECUTOR_USED_DURABLE_SELECTION_OUTCOMES_AND_PAPER_SCREEN_RENDERED_ONLY_AGGREGATE_CANARY_STATE
ROOT_CAUSE_FIXED = YES
FUNNEL_EXECUTOR_SOURCE_OF_TRUTH = CONSISTENT
SELECTED_APPROVAL_EXECUTION_CONTRACT = PASS
SELECTED_VALID_APPROVAL_CREATES_COMMAND = PASS
COMMAND_CREATION_IDEMPOTENCY = PASS
NO_SILENT_NOT_CREATED = PASS
NOT_CREATED_REASON_VISIBILITY = PASS
FUNNEL_PAPER_SCREEN_PARITY = PASS
IDENTITY_BINDING = PASS
POSTGRES_E2E = PASS
PROJECT_RECONCILIATION = PASS
SCHEMA_RECONCILIATION = PASS
RUNTIME_VERSION_RECONCILIATION = PASS
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
```

## Reproduction and exact production identity

The mismatch was reproduced for the natural SUIUSDT 5m plan. The Funnel could
derive a decorative `SELECTED` row from historical ranking while the executor
used the persisted `paper_plan_execution_outcomes` object. The PAPER screen did
not consume that exact object and therefore fell back to the aggregate canary
message `WAITING_FOR_ELIGIBLE_APPROVAL` even though the selected plan already had
a terminal executor outcome.

```text
AFFECTED_SYMBOL = SUIUSDT
AFFECTED_BOUNDARY_MS = 1788279600000
AFFECTED_BOUNDARY_UTC = 2026-09-01T16:20:00Z
PROFILE_ID = trade-5m-v1
SOURCE_RUN_ID = orchestrator:6922f5a8293c4878a572d493f086dcb3
OPPORTUNITY_ID = opportunity:5d1868bf48e554b3b4d5156a
SOURCE_CANDIDATE_ID = setup:SUIUSDT:5m:1788279600000:SCALP_BREAKOUT:SETUP_CANDIDATE:2e22981e83eabae1
EXECUTION_CANDIDATE_ID = paper:production-approval-candidate:v1:4c054cbc9dce4ec224b5e2318a715d6567131871a82325da54ae9b2a87015407
APPROVAL_ID = paper:risk-approval:v1:1d56d757049b5265a76fe037f39a7927627191157f6c4c282d5312a5009d9a06
PLAN_ID = paper:SUIUSDT:5m:1788279600000:risk:SUIUSDT:5m:1788279600000:strategy:v2:15c9977c9c29cea0f67161b9a147d597f821d472815c1086ded9e0c03462ada7:2d3e8e84e94ce679:ffe708d826b4fcf6
APPROVAL_CREATED_AT = 2026-09-01T16:20:28.936Z
PLAN_CREATED_AT = 2026-09-01T16:20:28.935Z
APPROVAL_VALID_UNTIL_MS = 1788279899999
APPROVAL_VALID_UNTIL_UTC = 2026-09-01T16:24:59.999Z
SELECTED_AT = 2026-09-01T16:20:58.794697Z
SCHEDULER_LAST_OBSERVED_AT = 2026-09-01T16:25:31.684645Z
SELECTOR_STATE = SELECTED
SELECTOR_RANK = 1
ATTEMPT_COUNT = 8
LIFECYCLE_STATE = EXPIRED_BEFORE_EXECUTION
COMMAND_STATUS = EXPIRED
COMMAND_ID = NONE
POSITION_STATUS = NOT_REACHED
POSITION_ID = NONE
TERMINAL_REASON = EXPIRED_BEFORE_EXECUTION
```

The approval had more than four minutes remaining when first selected and was
observed eight times, so scheduler cadence was not the exclusion cause. During
the validity window the executor's safety readiness failed closed because the
WAL/PITR ACK owner was not current. The approval was correctly not replayed
after expiry. The missing product behavior was durable lifecycle parity: one UI
recomputed selection, the other ignored the exact persisted terminal record.

## Implementation

Server commits:

```text
29380e7ea9cb97e6e944b745dd5977f39e7ec910 fix(paper): unify selected execution lifecycle
7713009985deb30ed5e48c5f975bd9bf1d021043 fix(readonly): serialize execution lifecycle timestamps
7f9d08dc9272fddc14aac13c53da6be12371f01e fix(funnel): project persisted approval validity
```

The Readonly runtime status now exposes the latest selected execution object
with exact run/profile/boundary/candidate/approval/plan identity, validity,
selection, command, position, lifecycle, terminal reason and attempt count.
The production Funnel obtains `SELECTED`, rank and command lifecycle from the
same persisted executor outcome instead of recomputing a winner. Durable
outcomes map to `PENDING_CREATE`, `CREATED`, `BLOCKED`, `EXPIRED` or `FAILED`
presentation semantics. An executor identity mismatch is persisted as
`NOT_CREATED_IDENTITY_MISMATCH`; it is not silently skipped.

Desktop commit:

```text
30e8a5ab7107ba6ef0a6278d2b37c2dbea84145a fix(paper): show selected execution lifecycle
```

The PAPER screen parses and renders the exact nested lifecycle. The generic
waiting message is suppressed whenever a concrete selected execution object is
available. The displayed identity and outcome now match the Funnel object.

## Tests

```text
SERVER_FOCUSED_BEFORE_FINAL_FIX = 1883_PASSED_6_SKIPPED
SERVER_TIMESTAMP_REGRESSION = 1863_PASSED
SERVER_FINAL_VALIDITY_REGRESSION = 1850_PASSED
POSTGRES16_ISOLATED_E2E = 6_PASSED
DESKTOP_FOCUSED = 44_PASSED_1309_SUBTESTS
DESKTOP_FULL = 1480_PASSED_3_SKIPPED_2_TRANSIENT_TK_FAILURES
DESKTOP_FOCUSED_AFTER_TRANSIENT_TK_FAILURES = PASS
COMPILEALL = PASS
```

The isolated PostgreSQL 16 suite used the task-owned loopback container and a
dedicated non-superuser role/database. It proves the complete real persistence
path `selected valid approval -> command -> fill -> OPEN position -> Readonly`,
explicit expired and policy-blocked outcomes, identity mismatch durability,
and idempotent no-duplicate behavior. It did not use the production database.

The broad server invocation without the repository's mandatory per-suite test
database URLs was not used as acceptance: it produced `30870 passed, 36
skipped, 445 failed, 342 errors`, dominated by absent mandatory fixture URLs
and unrelated environment/static-contract suites. Applicable focused tests and
the isolated PostgreSQL E2E are green.

## Deployment and production acceptance

Mandatory preflight and post-deploy safety gates passed. No schema migration
was required.

```text
READONLY_BIND = 127.0.0.1:8765
READONLY_DEPLOYED_COMMIT = 7f9d08dc9272fddc14aac13c53da6be12371f01e
READONLY_IMAGE = sha256:d6fa681e45572e3fbc076d0cc47df9c12c2ca1a5e2581e33b96fa6e9e7658308
READONLY_HEALTH = HEALTHY_RESTART0
CONTROL_DEPLOYED_COMMIT = 29380e7ea9cb97e6e944b745dd5977f39e7ec910
CONTROL_IMAGE = sha256:08250d80f4b22c3af85e1f0afd835e737d6902409bba8f09ed33457d113f64fd
CONTROL_HEALTH = HEALTHY_RESTART0
ALEMBIC_HEAD = 0020_paper_plan_execution_outcomes
ALEMBIC_HEAD_COUNT = 1
PAPER_RUNTIME = ENABLED
PAPER_DAEMON = ENABLED
PAPER_SCHEDULER = ENABLED
PAPER_MUTATION_READY = TRUE
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
WAL_READY = TRUE
PITR_READY = TRUE
LIVE_ALLOWED = FALSE
PRODUCTION_OUTCOME_COUNT = 1
PRODUCTION_COMMAND_COUNT = 0
PRODUCTION_POSITION_COUNT = 0
READONLY_REPORTING_CONTRACT = v1
FUNNEL_PROJECTION = trading-funnel-v1
```

After the final Readonly deployment, both endpoints returned the same durable
SUI identity and outcome: selected rank 1, validity `1788279899999`, command
`EXPIRED`, lifecycle and reason `EXPIRED_BEFORE_EXECUTION`, and no command or
position IDs. Newly completed natural 5m cycles continued normally without a
new qualifying plan; no trade was forced. The affected natural plan therefore
has an allowed explicit terminal outcome, not silent `NOT_CREATED`.

The first Readonly rollout exposed a timestamp serialization HTTP 500. It was
diagnosed, covered by regression tests, fixed in `7713009`, redeployed, and the
final container logs contain no ERROR, traceback, exception or HTTP 500 entry.

The Desktop repository had no running process at final reconciliation, so no
interactive process was killed or invented as deployed. Its committed source
and contract tests are current. The mobile repository is unaffected and its
pre-existing dirty user work was preserved untouched.

## Final decision

```text
ROOT_CAUSE_FIXED = YES
EXECUTOR_EXCLUSION_CAUSE_BEFORE = SAFETY_READINESS_FAILED_DURING_VALIDITY_THEN_APPROVAL_EXPIRED
EXECUTOR_BEHAVIOR_AFTER = EXACT_DURABLE_IDENTITY_AND_CREATED_BLOCKED_EXPIRED_FAILED_LIFECYCLE_VISIBLE_TO_BOTH_SCREENS
COMMAND_ID_AFTER_FOR_SUI = NONE_TERMINAL_EXPIRED
POSITION_ID_AFTER_FOR_SUI = NONE_NOT_REACHED
SELECTED_VALID_APPROVAL_CREATES_COMMAND = PASS_ISOLATED_POSTGRES_E2E
NO_SILENT_NOT_CREATED = PASS
FUNNEL_PAPER_SCREEN_PARITY = PASS
REMAINING_BLOCKERS = NONE_FOR_THIS_REMEDIATION
NEXT_ACTION = CONTINUE_NATURAL_PAPER_OPERATION_AND_OBSERVE_NEXT_QUALIFYING_SELECTED_APPROVAL_WITHOUT_FORCING_OR_TUNING
```
