# TRADERS_5M_SCALPING_GEOMETRY_RISK_QUOTA_AND_NET_COST_REMEDIATION_01

## Verdict

```text
TASK_STATUS = BLOCKED_AFTER_SOURCE_IMPLEMENTATION_AND_ISOLATED_VALIDATION
FINAL_VERDICT = BLOCKED_TRADERS_5M_SCALPING_GEOMETRY_RISK_QUOTA_AND_NET_COST_REMEDIATION_01_PRODUCTION_SAFETY_AND_RUNTIME_BASELINE_CONFLICT
BLOCKER_CODE = WAL_PITR_SAFETY_GATE_FAILED
SECONDARY_BLOCKER = CURRENT_PRODUCTION_5M_EXECUTION_AUTHORITY_PREEXISTING_AND_CURRENT_STAGE_LOSS_REASON_MATRIX_NOT_CORROBORATABLE
STOP_CONDITION = NO_PRODUCTION_FACING_ACTIONS_WHILE_WAL_READY_OR_PITR_READY_FALSE
```

Source and deterministic shadow validation are implemented. Full PASS is not
claimed because the fresh production safety gate is fail-closed, production
already has pre-existing 5m execution authority, and the bounded GET contract
does not expose a complete rolling raw-reason histogram. No production-facing
action or WAL repair was attempted.

## Baseline and fresh runtime

```text
SERVER_HEAD_BEFORE = bf0e28ca8998fa82e6cef62a79c369d73b897e2e
SERVER_TREE_BEFORE = c1f2b1684016cc6e17c52b5252e14dd7bcf45365
SERVER_ROOT_CLEAN_BEFORE = YES
DESKTOP_HEAD_BEFORE = 584d8738dfa2ac5b12deed1c5ea27feaec3e94bb
DESKTOP_TREE_BEFORE = 08ce04df267b5f2de8b286a24f44df7e80364596
DESKTOP_ROOT_CLEAN_BEFORE = YES
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_TREE_BEFORE = f791937049c431725718b4a26ce7e23b2a3ea4ec
MOBILE_ROOT_CLEAN_BEFORE = YES
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
TRADE_15M_HEALTH = CURRENT_PRODUCTION_SEARCH
TRADE_5M_RUNTIME_STATE = PRODUCTION_SEARCH_COMMAND_TRUE_POSITION_TRUE_PREEXISTING
CONTROL_STATE = ARMED
CONTROL_GENERATION = 6
CANARY_STATUS = WAITING_FOR_ELIGIBLE_APPROVAL
LIVE_STATE = DISABLED
WAL_READY = false
PITR_READY = false
LINEAGE_VALID = true
PHYSICAL_WAL_GAP = false
ACTIVE_UNRESOLVED_FAILURES = UNPROVEN_NOT_EXPOSED_BY_BOUNDED_READINESS_DTO
EXPORT_BACKLOG = UNPROVEN_NOT_EXPOSED_BY_BOUNDED_READINESS_DTO
PENDING_ARCHIVE_STATUS = UNPROVEN_NOT_EXPOSED_BY_BOUNDED_READINESS_DTO
ACK_OWNER_PROCESS_IDENTITY_MATCH = UNPROVEN_NOT_EXPOSED_BY_BOUNDED_READINESS_DTO
ACK_OWNER_HEARTBEAT_HEALTH = UNPROVEN_NOT_EXPOSED_BY_BOUNDED_READINESS_DTO
```

## Current stage-loss matrix

The prompt snapshot `470 -> 121 -> 41 -> 30 -> 0 -> 0` was stale by task
start. The fresh bounded Readonly rolling-4h projection at
`2026-08-24T15:56:33.1946148Z` was:

```text
analysis 480 -> structural 26 -> strategy 0 -> risk 0 -> PAPER 0 -> final 0
CURRENT_5M_STAGE_LOSS_MATRIX_COMPLETE = NO_RAW_REASON_HISTOGRAM_UNAVAILABLE_AND_DB_CORROBORATION_BLOCKED_BY_WAL_PITR_GATE
CURRENT_MISSING_CAUSAL_LEVELS = 0_OBSERVED_DOWNSTREAM_NOT_REACHED
CURRENT_MISSING_TARGET = 0_OBSERVED_DOWNSTREAM_NOT_REACHED
CURRENT_LOW_RR = 0_OBSERVED_DOWNSTREAM_NOT_REACHED
CURRENT_RESEARCH_LIMIT_REJECTS = 0_OBSERVED_DOWNSTREAM_NOT_REACHED
CURRENT_OTHER = 480_LOST_BEFORE_STRATEGY_REASON_SUBTYPES_NOT_EXPOSED
```

## Source remediation

- Research counters are keyed by profile/day/symbol/direction and retry identity
  is profile-namespaced. Risk context exports the profile identity.
- `SharedAccountExecutionBudget` is a separate, global, locked authority.
  Reservation happens only for valid plan identity/effective risk; commit and
  retry are idempotent; downstream failure releases it.
- The dedicated 5m evaluator preserves causal invalidation. ATR cohorts are
  `0.25/0.50/0.75/1.00`; stop envelopes are `50/65/80 bps`. Stops are never
  clipped inward. Wide stops reject explicitly and preserve geometry.
- Target order is nearest known local 5m, validated structural, then relevant
  achievable higher-TF. Future-only targets are excluded. `45/60/80 bps`
  minimum-target cohorts classify but never synthesize targets.
- Existing `BinancePublicRestClient` now provides public book ticker spread and
  bounded depth VWAP. No second client, private API, or order endpoint exists.
- Fee source is `CONFIGURED_CONSERVATIVE_FEE_ASSUMPTION_NOT_AUTHORITATIVE`.
  Spread source is public book ticker; depth source is public bounded VWAP.
  Diagnostic quantity confers no execution authority.
- Missing/non-authoritative spread or depth fails closed. The gate computes
  total costs, expected net edge, effective risk, gross/net RR and break-even
  win rate. Negative edge, high depth impact and low gross/net RR are distinct.
- Every rejection returns all causally known geometry/economic fields and raw
  machine reason. Additive JSON diagnostics require no migration.
- New reason codes have server-owned RU/EN key and placeholder parity; desktop
  changed only by generated catalog synchronization.

## Shadow experiment matrix

Dataset `DETERMINISTIC_CAUSAL_5M_FIXTURES_V1`: 8 candidates, 4 ATR × 3
envelope × 3 target diagnostics × 3 RR = 108 reports. Target thresholds are
diagnostic only, so each of the following rows applies identically to target
cohorts `45/60/80`. RR columns are counts at `1.0/1.2/1.5`.

| ATR | Env | Geometry | Wide | Missing | Cost pass | Gross RR | Net RR | Valid/final | Median stop/P90/target/gross/net/edge/BE |
|---:|---:|---:|---:|---:|---:|---|---|---|---|
| .25 | 50 | 3 | 3 | 2 | 2 | 2/2/2 | 1/1/0 | 0/0 | 42.5/83.75/100/2.0833/1.1375/69/.4751 |
| .25 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1/1 | 42.5/83.75/110/2.6780/1.4016/79/.4164 |
| .25 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1/1 | 42.5/83.75/110/2.0833/1.1375/79/.4751 |
| .50 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0/0 | 45/87.5/72.5/2.0348/1.3485/41.5/.4258 |
| .50 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1/1 | 45/87.5/110/2.4804/1.3485/79/.4258 |
| .50 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1/1 | 45/87.5/110/1.9608/1.0950/79/.4844 |
| .75 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0/0 | 47.5/91.25/72.5/1.9049/1.2993/41.5/.4349 |
| .75 | 65 | 4 | 2 | 2 | 3 | 3/3/3 | 2/2/1 | 1/1 | 47.5/91.25/110/2.3105/1.2993/79/.4349 |
| .75 | 80 | 5 | 1 | 2 | 4 | 4/4/4 | 2/2/1 | 1/1 | 47.5/91.25/110/1.8519/1.0555/79/.4934 |
| 1.0 | 50 | 2 | 4 | 2 | 1 | 1/1/1 | 1/1/0 | 0/0 | 50/95/72.5/1.7907/1.2535/41.5/.4437 |
| 1.0 | 65 | 3 | 3 | 2 | 2 | 2/2/2 | 1/1/0 | 0/0 | 50/95/100/1.7544/1.0188/69/.5021 |
| 1.0 | 80 | 5 | 1 | 2 | 4 | 4/4/3 | 2/2/0 | 0/0 | 50/95/110/1.7544/1.0188/79/.5021 |

```text
OLD_GEOMETRY_RR_1_2_PASS_COUNT = 5
NEW_GEOMETRY_RR_1_2_PASS_COUNT = 4
NEW_GEOMETRY_NET_COST_PASS_COUNT = 4
PRIMARY_VALID_PLAN_FINAL_SHADOW_APPROVAL_COUNT = 1
RR_COHORT_CAN_OVERRIDE_GEOMETRY = NO
RR_COHORT_CAN_OVERRIDE_COST_GATE = NO
```

The lower new count is accepted; no configuration is selected by signal count.
Primary rejected examples preserve: BTC stop 32.5/target 120/gross 3.6923/net
1.4016 `LOW_NET_RR`; BNB stop 83.75 `STOP_TOO_WIDE`; XRP stop 37/target
25/gross .6757 `NEGATIVE_NET_EDGE`; ADA missing target; SUI future-only target
excluded as missing.

## Tests, invariance, mutations and Git

```text
TASK_FOCUSED = 25_PASSED
AFFECTED_SERVER = 131_PASSED_1_NONBLOCKING_WINDOWS_TEMP_CLEANUP_WARNING
FINAL_INCREMENTAL = 37_PASSED
COMPILEALL = PASS
SERVER_FULL = 30674_PASSED_30_SKIPPED_439_FAILED_342_ERRORS
SERVER_FULL_CLASSIFICATION = NOT_PASS_PREEXISTING_STALE_SCHEMA_EXPECTATIONS_AND_MISSING_OPT_IN_POSTGRES_URLS
DESKTOP_FULL = 1454_PASSED_2_SKIPPED_3029_SUBTESTS
SECURITY_SCANNER = 636_PASSED
MOBILE = SOURCE_UNCHANGED_NOT_RUN
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
TRADE_15M_GEOMETRY_CHANGED_BY_TASK = NO
TRADE_15M_RR_CHANGED_BY_TASK = NO
TRADE_15M_RISK_POLICY_CHANGED_BY_TASK = NO_SEMANTIC_EQUIVALENCE_TEST_PASS
PRODUCTION_5M_MIN_RR_CHANGED_BY_TASK = NO
TRADE_5M_EXECUTION_AUTHORITY_BY_TASK = NONE
CURRENT_PRODUCTION_5M_EXECUTION_AUTHORITY = PREEXISTING_TRUE_CONFLICT
TRADE_5M_PAPER_COMMANDS_ORDERS_FILLS_POSITIONS_BY_TASK = 0_0_0_0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SCHEMA_CHANGE_REQUIRED = NO
PRODUCTION_DEPLOYMENT_PERFORMED = NO
PRODUCTION_SCHEMA_BUSINESS_PRIVILEGE_CONTROL_TRADING_MUTATIONS = 0_0_0_0_0
LIVE_MODE_CHANGED_BY_TASK = NO
SERVER_IMPLEMENTATION_COMMITS = 9edcbc8e0b0c0b38bf15426deb0bc78e749fef3f,18831fd62e3fef6a3dc9e73a7b746ac98afe8176
DESKTOP_IMPLEMENTATION_COMMIT = 1aa8194740760f6011813b8f7aed44929aa82f5b
MOBILE_COMMITS = NONE
PUSHED = NO
NEXT_ACTION = RESTORE_WAL_PITR_ACK_READINESS_IN_SEPARATE_AUTHORIZED_TASK_THEN_RETRY_SOURCE_INTEGRATION_AND_SHADOW_RUNTIME_ACCEPTANCE
```
