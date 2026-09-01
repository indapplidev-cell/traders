# TRADERS PAPER plan-to-execution diagnostic and fix 01

```text
TASK_STATUS = CODE_FIXED_DEPLOYMENT_BLOCKED
FINAL_VERDICT = LOCAL_AND_ISOLATED_PASS_PRODUCTION_DEPLOYMENT_FORBIDDEN
ROOT_CAUSE = WAL_AND_PITR_READINESS_EXPIRED_BEFORE_ALL_THREE_APPROVALS; THE_SAFETY_GATE_CORRECTLY_DENIED_COMMAND_INGESTION; THE_DEFECT_WAS_THAT_SELECTOR_POLICY_DENIAL_AND_EXPIRY_WERE_NOT_DURABLY_PERSISTED_AND_THE_FUNNEL_HAD_NO_PER_PLAN_4H_DRILLDOWN
ROOT_CAUSE_FIXED = YES_IN_CODE_AND_ISOLATED_POSTGRES; NOT_DEPLOYED
PRODUCTION_SCHEMA = 0018_promote_5m_production_search
REPOSITORY_SCHEMA = 0020_paper_plan_execution_outcomes
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0
```

## Exact aggregate reproduction

The authoritative production readonly response captured at
`2026-08-31T15:26:10.418Z` for `trade_profile=trade-5m-v1` returned exactly:

```text
rolling_4h.ANALYSIS = 480
rolling_4h.PAPER_TRADE_PLAN = 3
rolling_4h.QUANTITY_APPROVED = 3
rolling_4h.VALIDITY_APPROVED = 3
rolling_4h.FINAL_APPROVAL = 3
```

The counter is produced from persisted `online_pipeline_runs` joined to
`online_pipeline_results`. Its unit is one admitted symbol/run in each 5m
boundary, filtered by profile and the closed boundary in the requested rolling
window. It means that a plan object was created; it does not mean that the plan
is still valid or that a command exists. The three rows were at three distinct
boundaries, so they are neither duplicate plan versions nor a cross-profile or
cross-cycle count.

All three rows were `SOLUSDT`. This is expected: the old detail projection was
symbol-oriented and could display only one selected SOL row even though the
rolling counter correctly included three distinct run identities.

## The three plans

### Plan 1

```text
symbol = SOLUSDT
profile_id = trade-5m-v1
universe_id = trading-universe-v2
boundary = 2026-08-31T12:40:00.000Z / 1788180000000
source_run_id = orchestrator:14d0171213054637b0f7ade21c1a0763
opportunity_id = opportunity:6b22357b1bbf2639f09818b9
candidate/setup_id = setup:SOLUSDT:5m:1788180000000:SCALP_BREAKOUT:SETUP_CANDIDATE:4919ac9456db6524
selector_candidate_id = paper:production-approval-candidate:v1:e1672b3a6c37277797e697c0911b039cf290bd9cdc5965dfa2b7509497734cb6
plan_id = paper:SOLUSDT:5m:1788180000000:risk:SOLUSDT:5m:1788180000000:strategy:v2:dd1835bf0225f6c213f94b478a58a31e3e8c3f648e69931f64076ae2fdf040c5:56758a233cfd3510:f376beceba794752
plan_created_at = 2026-08-31T12:40:23.759Z
plan_status = PAPER_PLAN_READY
final_approval_id = paper:risk-approval:v1:f4299ac9c01dbaa413b9b50d7cb6908990abf9e8c8ed40ab004637ed65a761a2
approval_created_at = 2026-08-31T12:40:23.760Z
approval_valid_from = 2026-08-31T12:40:23.760Z
approval_valid_until = 2026-08-31T12:44:59.999Z
approval_status = FINAL_PAPER_APPROVAL_TRUE
selector_replay = ELIGIBLE_APPROVAL / SELECTOR_WINNER / rank 1
execution_command_id = NONE
paper_position_id = NONE
terminal_state = EXPIRED_BEFORE_EXECUTION
terminal_reason = WAL_NOT_READY,PITR_NOT_READY_THEN_EXPIRED_BEFORE_EXECUTION
```

### Plan 2

```text
symbol = SOLUSDT
profile_id = trade-5m-v1
universe_id = trading-universe-v2
boundary = 2026-08-31T13:05:00.000Z / 1788181500000
source_run_id = orchestrator:99d4c22fd15a468992b12149cff93b93
opportunity_id = opportunity:1a79091f805d3f01ee69bcd6
candidate/setup_id = setup:SOLUSDT:5m:1788181500000:SCALP_BREAKOUT:SETUP_CANDIDATE:a3639d3fec7a3843
selector_candidate_id = paper:production-approval-candidate:v1:734c78f9b8e554db63a5641f1998547965ae02e9580ef8c9f15152bdaea0cd40
plan_id = paper:SOLUSDT:5m:1788181500000:risk:SOLUSDT:5m:1788181500000:strategy:v2:2620aeaf22250b452cc732362867e88dd24cb83f5c6fb0a1ba5045bc3a85d5fb:d99908c377f5f58e:d13ed81ebad4bdb7
plan_created_at = 2026-08-31T13:05:31.528Z
plan_status = PAPER_PLAN_READY
final_approval_id = paper:risk-approval:v1:2d290fb8d6fcd893a7bfb0eb85b668ae3edadc735f4ef8c3f726b153d5ec7937
approval_created_at = 2026-08-31T13:05:31.530Z
approval_valid_from = 2026-08-31T13:05:31.530Z
approval_valid_until = 2026-08-31T13:09:59.999Z
approval_status = FINAL_PAPER_APPROVAL_TRUE
selector_replay = ELIGIBLE_APPROVAL / SELECTOR_WINNER / rank 1
execution_command_id = NONE
paper_position_id = NONE
terminal_state = EXPIRED_BEFORE_EXECUTION
terminal_reason = WAL_NOT_READY,PITR_NOT_READY_THEN_EXPIRED_BEFORE_EXECUTION
```

### Plan 3

```text
symbol = SOLUSDT
profile_id = trade-5m-v1
universe_id = trading-universe-v2
boundary = 2026-08-31T13:15:00.000Z / 1788182100000
source_run_id = orchestrator:0a73869a8a0c4d54b2c4c29d5cf55c08
opportunity_id = opportunity:27fb2f42e5bddbd776e6b56e
candidate/setup_id = setup:SOLUSDT:5m:1788182100000:SCALP_COMPRESSION_BREAK:SETUP_CANDIDATE:a50226817c61a074
selector_candidate_id = paper:production-approval-candidate:v1:ba7899cce71902136176076b4b8f996f0a4c3cc96473e169b41d7002e10215df
plan_id = paper:SOLUSDT:5m:1788182100000:risk:SOLUSDT:5m:1788182100000:strategy:v2:54c7412e4956e26296abd3ed5744781f264f1d35938fbebc2983b0d72716a871:c36ad1649b97c45a:6406436074dd208b
plan_created_at = 2026-08-31T13:15:35.259Z
plan_status = PAPER_PLAN_READY
final_approval_id = paper:risk-approval:v1:6a49c25c102f465f909dd7ce7805bf5a1774ff8930a9db172325cfd5869c21c2
approval_created_at = 2026-08-31T13:15:35.260Z
approval_valid_from = 2026-08-31T13:15:35.260Z
approval_valid_until = 2026-08-31T13:19:59.999Z
approval_status = FINAL_PAPER_APPROVAL_TRUE
selector_replay = ELIGIBLE_APPROVAL / SELECTOR_WINNER / rank 1
execution_command_id = NONE
paper_position_id = NONE
terminal_state = EXPIRED_BEFORE_EXECUTION
terminal_reason = WAL_NOT_READY,PITR_NOT_READY_THEN_EXPIRED_BEFORE_EXECUTION
```

The three `valid_until` values are exactly the next `trade-5m-v1` trigger
boundary minus one millisecond.

## End-to-end trace and root cause

For every plan, replaying the production approval adapter at `plan_created_at +
30s` and through `valid_until` classified the row as `ELIGIBLE_APPROVAL`. The
deterministic selector saw one eligible competitor and selected it at rank 1.
At the exact plan creation millisecond the approval is correctly still a future
decision because approval materialization follows by one or two milliseconds.

The selector poll interval was 30 seconds and each valid window was about 4m25s.
Therefore the next-boundary polling race did not explain these plans. There was
ample time for several selector polls.

The canonical WAL ACK daemon state stopped updating at
`2026-08-31T10:41:25.043347Z`. With `MAX_WAL_DAEMON_AGE_SECONDS=1200`, WAL/PITR
readiness became false at approximately `11:01:25Z`, before all three plans.
The executor's independent readiness gate therefore correctly returned
`INDEPENDENT_READINESS_GATE_DENIED` and command ingestion was forbidden.
Expired approvals are intentionally not replayed after permissions/readiness
recover.

The production defect was silent loss of explanation, not an omitted safe
trade: policy denial was transient, no per-plan terminal outcome was persisted,
the canary remained `NO_ELIGIBLE_APPROVAL`, and the readonly projection could
not expose all three same-symbol historical plan identities.

## Fix

Revision 0020 adds the append/update-bounded
`paper_plan_execution_outcomes` lifecycle keyed by source run and uniquely by
plan. It persists selector rank/reason/winner, control generation, observed
runtime flags, attempt count, policy blockers, command identity, execution
failure, and expiry. Terminal outcomes cannot be overwritten by later polls.

The scheduler now:

- persists every deterministic selector competitor and `NOT_SELECTED` reason;
- persists readiness and safety blocker codes before command ingestion;
- records command creation or durable execution failure;
- converts due unexecuted plans to `EXPIRED_BEFORE_EXECUTION` without replay;
- keeps command and position idempotency unchanged.

The readonly funnel now exports `historical_paper_plans_4h` by run/plan identity
instead of symbol identity. The Desktop client renders the bounded list with
symbol, boundary, approval, selector, command, position and terminal reason.
Legacy pre-0020 plans are explicitly shown as `LEGACY_NOT_OBSERVED` and
`EXPIRED_BEFORE_EXECUTION`; the server remains the source of trading truth.

## Validation

```text
SCHEMA_FUNNEL_SCHEDULER_OUTCOME = 65 passed
PAPER_RUNNER_SCALPING_CLOCK_REGRESSION = 51 passed, 5 skipped
APPROVAL_VALIDITY_AND_MATERIALIZATION = 1750 passed; 1 setup failure only because a separate legacy migration test requires PAPER_TEST_DATABASE_URL
APPLICABLE_BROAD_NO_DB_MATRIX = 4612 passed, 9 skipped; 94 setup errors solely from missing PAPER_TEST_DATABASE_URL
APPLICABLE_BROAD_SHARED_DB_MATRIX = 4667 passed, 9 skipped; 39 pre-existing cross-suite fixture conflicts caused by multiple legacy suites preparing one DB at incompatible historical revisions
DESKTOP_FOCUSED = 38 passed, 14 subtests passed
DESKTOP_FULL = 1482 passed, 2 skipped, 3029 subtests passed; 1 external Tcl init.tcl environment failure
COMPILEALL = PASS
DIFF_CHECK = PASS
```

The final isolated PostgreSQL 16 E2E used a unique loopback `paper_test_*`
database and a non-superuser/non-createdb/non-createrole/non-replication role,
migrated from empty to the single head 0020, then removed the database and role:

```text
POSTGRES_E2E = 4 passed
SCENARIO_1 = candidate -> final approval -> selector -> command -> entry order -> fill -> OPEN PAPER position -> readonly projection PASS
SCENARIO_1_RETRY = command/order/fill/position counts remain 1/1/1/1 PASS
SCENARIO_2 = selected valid plan -> WAL/PITR policy block -> no command -> expiry -> durable EXPIRED_BEFORE_EXECUTION PASS
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

## Fresh production safety reread

At the final pre-commit reread:

```text
runtime_enabled = true
daemon_enabled = true
scheduler_enabled = true
mutation_enabled = true
live_allowed = false
control = ARMED generation 6
wal_ready = false
pitr_ready = false
current_mutation_ready = false
current_mutation_denial_reasons = PITR_NOT_READY,WAL_NOT_READY
paper balance = 100 USDT
commands = 0
open positions = 0
closed trades = 0
archive unresolved_failure = YES
archive failed_count = 715
production schema = 0018
```

Consequently production migration and deployment are forbidden. No artificial
production plan or trade was created. Natural post-fix verification cannot
start before safety recovery, migration 0019/0020, established deployment, and
running-commit verification.

