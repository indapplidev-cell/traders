# TRADERS_SCALPING_V2_AUTHORITATIVE_PAPER_EXECUTION_BRIDGE_FIX_01

## Interim production verdict

```text
TASK_STATUS = IN_PROGRESS_NATURAL_VALIDATION_PENDING
FINAL_VERDICT = FIXED_DEPLOYED_E2E_PASS_NATURAL_POSITION_OPEN_PENDING

SCALPING_V2_PROFILE_ID = trade-5m-v2
SCALPING_V2_VERSION = trade-5m-v2
SCALPING_V2_AUTHORITATIVE = PASS

SCALPING_V1_ACTIVE_NEW_CANDIDATES = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_APPROVALS = FORBIDDEN
SCALPING_V1_SELECTOR_PARTICIPATION = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_COMMANDS = FORBIDDEN
SCALPING_V1_ACTIVE_NEW_POSITIONS = FORBIDDEN

TRADE_15M_VERSION = trade-15m-v1
TRADE_15M_CONFIG_CHANGED = NO
TRADE_15M_BEHAVIOR_CHANGED = NO
TRADE_15M_REGRESSION = PASS

SELECTOR_ID = eligible-approval-ranking-v1
MAX_NEW_COMMANDS_PER_CYCLE = 1
MAX_OPEN_POSITIONS = 1
MULTI_APPROVAL_POLICY = DETERMINISTIC_RANKING_ONE_WINNER_NON_WINNERS_EXPLICIT_NOT_SELECTED
RANKING_FIELDS = risk_score_desc,planned_risk_reward_desc,strategy_score_desc,closed_until_ms_desc,source_run_id_asc,final_approval_id_asc,candidate_id_asc,symbol_asc
TIE_BREAK = candidate_id_asc_then_symbol_asc

ROOT_CAUSE = CONTROL_CONSUMER_3S_HTTP_TIMEOUT_ON_AUTHORITATIVE_READONLY_SNAPSHOT_PLUS_V1_RUNTIME_AUTHORITY_AND_V2_PROVENANCE_PROJECTION_GAPS
ROOT_CAUSE_FIXED = YES

READINESS_STATE = READY_CONTROL_ARMED_GENERATION6_MUTATION_READY_LIVE_FALSE
READINESS_REASONS = NONE

NATURAL_WINNER_SYMBOL = PENDING_NEW_POST_FIX_SIGNAL
NATURAL_WINNER_RANK = PENDING
NATURAL_WINNER_PROFILE_VERSION = PENDING
NATURAL_WINNER_CANDIDATE_ID = PENDING
NATURAL_WINNER_APPROVAL_ID = PENDING
NATURAL_WINNER_PLAN_ID = PENDING

COMMAND_ID = PENDING_NATURAL_WINNER
COMMAND_STATUS = NOT_REACHED_NO_NEW_SIGNAL
POSITION_ID = PENDING_NATURAL_WINNER
POSITION_STATUS = NOT_REACHED_NO_NEW_SIGNAL

EXPIRY_RACE_FIXED = PASS_POLL30_TO5_SECONDS_AND_READINESS_TIMEOUT3_TO10_SECONDS
READINESS_REGRESSION_FIXED = PASS
GENERIC_UNAVAILABLE_VALUES_AFTER = 0_FOR_REQUIRED_REACHED_V2_PLAN_FIELDS
FUNNEL_PAPER_PARITY = PASS_CONTRACT_AND_POSTGRES_E2E; NATURAL_OPEN_IDENTITY_PENDING
POSTGRES_E2E = PASS_6
NATURAL_V2_POSITION_OPEN = PENDING

SERVER_HEAD = b2f23ea894dc45088b0537cf7ab1773938d9446d
DEPLOYED_COMMIT = 033f57335628375eb52f1ab0f59a81702e8495c4
DESKTOP_HEAD = 78f124aa9dce0131b759939ef02962edb8d2bb16
MOBILE_HEAD = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
ALEMBIC_HEAD = 0021_independent_scalping_profile_v2

LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0
SECRET_OUTPUT = 0

REMAINING_BLOCKERS = NONE_TECHNICAL; WAITING_FOR_NEXT_NATURAL_V2_PAPER_PLAN
NEXT_ACTION = HEARTBEAT_EVERY5MIN_UNTIL_NATURAL_SELECTED_COMMAND_CREATED_POSITION_OPEN_THEN_FINAL_RECONCILIATION
```

## Proven implementation and deployment

- New runtime admission is restricted to `trade-5m-v2`; `trade-5m-v1` remains
  registered only for historical reconstruction. Production approval, selector
  ingestion, command and position paths reject a new v1 identity.
- The 5m orchestrator command is `--trade-profile trade-5m-v2`. The independent
  v2 collector writes a separate lineage at schema `0021`.
- The canonical selector remains `eligible-approval-ranking-v1`; no ranking or
  capacity threshold was changed.
- Continuation cadence is five seconds. The authoritative readonly snapshot
  timeout is ten seconds. The post-deploy snapshot is `READY`, generation 6,
  market/approval/WAL/PITR true, current mutation ready, denials empty and LIVE
  forbidden.
- Runtime images for 5m, collector, readonly and control carry source identity
  `033f57335628375eb52f1ab0f59a81702e8495c4`. The 15m container was not
  rebuilt or restarted and still runs its pre-task image.
- Production DB reports schema head `0021_independent_scalping_profile_v2`.
  There are zero v1 pipeline rows after the first v2 cutover row.

## Tests and natural observation

- Required focused authority/selector/readiness/expiry/15m/UI suite: `78 passed`.
- Isolated PostgreSQL 16 E2E: `6 passed`, including v2
  plan/approval/selection/command/fill/open, blocker recovery, identity mismatch,
  expiry and 15m regression cases.
- The first natural v2 winner (LINKUSDT, boundary `1788385800000`) was selected
  before the final timeout fix and durably expired with
  `READONLY_RUNTIME_NOT_READY`; it was not replayed.
- Five complete natural boundaries after the fix (`22:00` through `22:25` UTC)
  produced explicit `NO_PLAN` or `REJECT` outcomes and no new final approval.
  This is not a technical blocker. Completion correctly remains pending until a
  new natural v2 approval creates a command and opens a PAPER position.
- Heartbeat `scalping-v2-natural-paper-acceptance` is active every five minutes
  and stays quiet while no actionable state change exists.

## UI evidence limitation

The running Desktop window was found and activated, but Windows Graphics Capture
returned `SetIsBorderRequired ... 0x80004002` for this Python custom-rendered
window and its accessibility tree exposes no named navigation controls. No blind
coordinate actions were taken. The deployed readonly contract consumed by the
Desktop was verified directly: reached v2 fields expose setup/entry/stop/target
policy versions, 5m provenance, geometry decision, cost decision, RR decision,
selector reason, command state and position state without a generic unavailable
value.

This file is an interim evidence snapshot, not final natural acceptance.
