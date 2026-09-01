# TRADERS PAPER execution readiness and command/open fix 01

```text
TASK_STATUS = IN_PROGRESS_NATURAL_VALIDATION_PENDING
FINAL_VERDICT = NOT_FINAL
ROOT_CAUSE = MISSING_WAL_ACK_OWNER_PLUS_NONAUTHORITATIVE_READONLY_SNAPSHOT_EXPANDED_DEFAULT_FALSE_VALUES_INTO_FALSE_MARKET_APPROVAL_LIVE_AND_BACKUP_REASONS
ROOT_CAUSE_FIXED = SOURCE_AND_RUNTIME_FIX_DEPLOYED_NATURAL_ACCEPTANCE_PENDING
IMPLEMENTATION_COMMIT = 00ab6877e3316e6c5578e0b9aeeb573447a48d4a
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
```

## Exact production reproduction

The prompt's LINKUSDT object was reproduced from the production Readonly API by
exact profile, boundary, source run, candidate, approval and plan identity.

```text
SYMBOL = LINKUSDT
PROFILE_ID = trade-5m-v1
BOUNDARY_CLOSED_AT_MS = 1788290400000
SOURCE_RUN_ID = orchestrator:13db521a0f4c4477b17d343ec735fc03
SOURCE_CANDIDATE_ID = setup:LINKUSDT:5m:1788290400000:SCALP_BREAKOUT:SETUP_CANDIDATE:7848943ee24d56e3
EXECUTION_CANDIDATE_ID = paper:production-approval-candidate:v1:1d4a16de80dec9205c46c024d9f27743e9bcfdbe8215d6c51b926e93513ba6c6
APPROVAL_ID = paper:risk-approval:v1:8e34bb2edbf503c950963b0b6c3741cf40acb01fef9b79a5f35a4b6f7a789bd0
PLAN_ID = paper:LINKUSDT:5m:1788290400000:risk:LINKUSDT:5m:1788290400000:strategy:v2:908c2fb5c367e63319d33ebb1a4c789e60d46f126955bfdb6379b767e4cc9a38:f2406a9078f1c3ba:ff3510039a02748c
ENTRY_TARGET_STOP = 11.231_11.062_11.27729167
GROSS_NET_REQUIRED_RR = 3.65076481_1.77388022_1.5
EXPECTED_NET_EDGE_BPS = 122.58727361
QUANTITY_NOTIONAL = 8.90000000_99.95590000000
SELECTED_AT = 2026-09-01T19:20:29.432Z
APPROVAL_VALID_UNTIL_MS = 1788290699999
ATTEMPT_COUNT = 8
LIFECYCLE = EXPIRED_BEFORE_EXECUTION
COMMAND_POSITION = NONE_NONE
```

The approval is terminal and was not replayed. Before remediation its durable
selector reason contained:

```text
MARKET_DATA_NOT_READY,APPROVAL_SOURCE_NOT_READY,WAL_NOT_READY,PITR_NOT_READY,LIVE_NOT_DISABLED,READONLY_RUNTIME_NOT_READY
```

Production diagnostics proved that the host ACK owner was absent and the WAL
archive had one unresolved retry, one export backlog object and two pending
archive-status objects. The canonical retry published two segments and restored
unresolved/backlog/pending to `0/0/0` without a physical gap. One canonical
hidden ACK owner was then started; PID, lock, state identity and heartbeat agree.

The additional false reasons came from `ExistingCanaryRuntimeReadiness` boolean
defaults. An unavailable or incomplete Readonly envelope was represented by
five false facts plus `READONLY_RUNTIME_NOT_READY`, and aggregation persisted
all of them. This also manufactured `LIVE_NOT_DISABLED` although the canonical
Readonly and Control contracts both reported LIVE disabled.

## Implementation

Commit `00ab6877e3316e6c5578e0b9aeeb573447a48d4a` separates snapshot authority
from individual gate values. A non-authoritative envelope now yields only
`READONLY_RUNTIME_NOT_READY`. An authoritative envelope yields only the current
false gates. The executor rejects a mismatched readiness/control generation as
`READINESS_CONTROL_GENERATION_MISMATCH` before ingestion.

Readonly lifecycle projections now expose:

```text
policy_evaluated_at
policy_generation
policy_reason_source = READONLY_PAPER_READINESS_CURRENT_SNAPSHOT
policy_source_timestamp
```

The production Funnel and PAPER runtime status consume the same persisted
identity-bound outcome. The historical LINK row now presents its terminal
result as `EXPIRED_BEFORE_EXECUTION`, while current readiness has no denials.

## Validation

```text
FOCUSED_SERVER_REGRESSION = 1891_PASSED
ISOLATED_POSTGRESQL16_E2E = 6_PASSED
POSTGRES_IDENTITY = TASK_OWNED_LOOPBACK_DATABASE_AND_NONSUPERUSER_ROLE
POSTGRES_SCENARIOS = FULL_SELECTED_COMMAND_FILL_OPEN_POSITION_IDEMPOTENCY_EXPIRED_IDENTITY_MISMATCH_EXACT_BLOCK_THEN_RECOVERY
COMPILEALL = PASS
DIFF_CHECK = PASS
```

The real PostgreSQL blocker/recovery case persisted exactly
`WAL_NOT_READY,PITR_NOT_READY`, restored readiness for the still-valid selected
candidate, created one command, and opened one PAPER position. The retry counts
remained one command and one position. Test databases and roles were removed
after each run.

## Deployment and current runtime

```text
ALEMBIC_HEAD = 0020_paper_plan_execution_outcomes
ALEMBIC_HEAD_COUNT = 1
READONLY_REVISION = 00ab6877e3316e6c5578e0b9aeeb573447a48d4a
READONLY_IMAGE = sha256:71df8f6931440e2add6310f04c3b6fd6aafdb0dca2d82d9b29c2a98daca3e1fc
READONLY_HEALTH_RESTART = HEALTHY_0
CONTROL_REVISION = 00ab6877e3316e6c5578e0b9aeeb573447a48d4a
CONTROL_IMAGE = sha256:fbc7b786deaae25f24f09c1c4d4b2a4187aedde4aa6051a06942f22f39110e3e
CONTROL_HEALTH_RESTART = HEALTHY_0
CONTROL_STATE_GENERATION = ARMED_6
RUNTIME_DAEMON_SCHEDULER_MUTATION = TRUE_TRUE_TRUE_TRUE
MARKET_DATA_READY = TRUE
APPROVAL_SOURCE_READY = TRUE
WAL_READY = TRUE
PITR_READY = TRUE
PHYSICAL_WAL_GAP = FALSE
CURRENT_MUTATION_READY = TRUE
CURRENT_DENIAL_REASONS = EMPTY
LIVE_ALLOWED = FALSE
PRODUCTION_COUNTS = OUTCOME2_COMMAND0_POSITION0
PROTECTED_SERVICE_RESTARTS_BY_TASK = READONLY1_CONTROL1_OTHERS0
```

The post-deploy logs contain no ERROR, traceback, exception or HTTP 500. The
Desktop accepted lifecycle consumer remains at commit
`78f124aa9dce0131b759939ef02962edb8d2bb16`; no Desktop process was claimed as
deployed. Mobile is unaffected at commit
`013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db`, and its pre-existing dirty user
changes were preserved untouched.

## Remaining acceptance gate

No new natural qualifying 5m candidate has appeared after deployment. The
latest observed complete cycle had zero PAPER plans, final approvals and
selector winners. A five-minute thread heartbeat is active and quiet while the
state is unchanged. It must stop only after a fresh natural selected approval
has either opened a PAPER position or produced one exact, current, authoritative
durable blocker. Overall PASS is intentionally withheld until that observation.

```text
REMAINING_BLOCKERS = NONE
CURRENT_PREREQUISITE = NEXT_NATURAL_SELECTED_APPROVAL_WITHOUT_SYNTHETIC_STIMULUS
NEXT_ACTION = HEARTBEAT_OBSERVE_SELECTED_TO_COMMAND_TO_OPEN_POSITION_THEN_FINAL_RECONCILIATION
```
