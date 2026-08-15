# TRADERS_ML_CURRENT_MUTATION_READY_ARMED_CANARY_CONTROL_SEMANTICS_REMEDIATION_01

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_ML_CURRENT_MUTATION_READY_ARMED_CANARY_CONTROL_SEMANTICS_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
PHASE_A_SEMANTIC_VERDICT = CASE_G_OTHER_PROVEN_CAUSE
```

## Proven semantic result

`current_mutation_ready` is the read-only projection consumed by
`ReadonlyPaperArmReadinessSource` for the next operator ARM operation. Its
`KILL_SWITCH_NOT_READY` condition is exactly failure of reconciled healthy
`DISABLED` control, and `CONTROL_NOT_ELIGIBLE` is exactly failure of
`state == effective_state == DISABLED && health == HEALTHY`. Both are expected
for the existing generation-6 ARMED canary and do not deny its already granted
bounded lifecycle.

The continuation worker never consumed `current_mutation_ready`; it separately
required the durable waiting state, original START lineage, zero command and
position counts, cluster advisory ownership, and the exact ARMED transition and
generation. Phase A nevertheless proved a source defect: the production first
command called ingestion without the existing mandatory
`PaperProductionMutationSafetyGate`, so current WAL/PITR readiness was not
re-observed at that boundary.

Commit `3081e2590a120eaf874e6c59ce53c8b0a4fe1305` adds an internal typed
existing-canary readiness source and wraps only first-command ingestion in the
existing safety gate. The read-only API field and routes are unchanged. The
runtime projection accepts exactly the two expected pre-control denial reasons
while requiring current schema/accounting/runtime, adapters, WAL, PITR and LIVE
denial. The gate then revalidates authoritative ARMED state, current generation,
PAPER target, symbol, candidate identity, and command/open-position budgets.

## State-machine summary

| Control state | ARM | START existing ARMED canary | Disable | Emergency stop | Existing runtime mutation |
|---|---|---|---|---|---|
| `DISABLED` | allowed only with full ARM preflight | denied | idempotent/safe-waiting only | allowed | denied every stage |
| `ARMED` | denied | exact canary/transition/generation only | allowed only for zero-trade waiting canary | allowed | stage-specific gate may allow |
| `EMERGENCY_STOP` | denied | denied | transition to disabled is source-legal; clear has explicit acknowledgement | idempotent | denied every stage |

| Canary state | Approval observation | New first command | Lifecycle advance |
|---|---|---|---|
| `RESERVED` | no | no | ARM recovery only |
| `ARMED` | START preflight only | START path only | yes |
| `ARMED_WAITING` | no continuation consumer | no | repository recovery only |
| `NO_ELIGIBLE_APPROVAL` (`WAITING_FOR_ELIGIBLE_APPROVAL` projection) | yes | yes, with all runtime gates | yes |
| `RUNNING` | no | no | yes |
| `POSITION_OPEN` | no | no | exit evaluation/close yes |
| `POSITION_CLOSING` | no | no | close completion yes |
| `POSITION_CLOSED` | no | no | reconciliation yes |
| `RECONCILIATION_PENDING` | no | no | reconciliation refresh yes |
| `COMPLETED`, `STOPPED`, `FAILED_SAFE` | no | no | terminal/no |

`current_mutation_ready` is true only in healthy `DISABLED` control with every
reporting conjunction passing. It is false in ARMED and EMERGENCY_STOP. It is
not the lifecycle-state predicate in the second table.

## Validation and production invariance

```text
FOCUSED_REGRESSION = 5558 passed, 2 skipped, 0 required failures
EXTERNAL_POSTGRES_HARNESS = NOT_RUN_MISSING_CANARY_REMEDIATION_TEST_PG_URL
PRODUCTION_DATABASE_USED_FOR_TESTS = NO
COMPILEALL = PASS
DIFF_CHECK = PASS
SCHEMA_CHANGE = NO
ROUTE_CHANGE = NO
CONTROL_API_IMAGE_REVISION = 3081e2590a120eaf874e6c59ce53c8b0a4fe1305
CONTROL_API_HEALTH = HEALTHY
CONTROL_API_RESTARTS = 1
POSTGRES_READONLY_API_ORCHESTRATOR_MARKET_DATA_RESTARTS = 0
WAL_READY_AFTER = true
PITR_READY_AFTER = true
WAL_SEGMENTS = 337 / 337
PHYSICAL_WAL_GAP = NO
ARCHIVE_BACKLOG_PENDING_UNRESOLVED = 0 / 0 / 0
CANARY_ID = 6f9858cd-f6b1-4c7f-810c-fccc1065bb9d
CANARY_STATE = WAITING_FOR_ELIGIBLE_APPROVAL
CANARY_GENERATION = 6
CANARY_COMMAND_POSITION_CLOSED_COUNTS = 0 / 0 / 0
CANARY_MAX_NEW_COMMANDS_MAX_OPEN_POSITIONS = 1 / 1
TASK_INDUCED_CANARY_OR_CONTROL_MUTATIONS = 0
PAPER_ARM_START_DISABLE_EMERGENCY_CLEAR_ACTIONS = 0 / 0 / 0 / 0 / 0
TRADING_MUTATION_POSTS = 0
BUSINESS_DATA_MUTATIONS = 0
LIVE = OFF
BINANCE_ORDER_CALLS = 0
PUSHED = NO
```

