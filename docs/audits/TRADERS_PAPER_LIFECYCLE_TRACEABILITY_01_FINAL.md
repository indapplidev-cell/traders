# PAPER lifecycle traceability — final evidence

`FINAL_VERDICT = PASS` for the requested technical implementation, deterministic
verification, image build, deployment, and runtime revision/health checks.
Natural post-deployment trading acceptance remains a separate operator check; this
task did not wait for a market event, position, close, or a new four-hour window.

## Scope and immutable controls

- Profile: `trade-5m-v2`; execution mode: `PAPER` only.
- Deployed implementation commit: `668dd099dcdf27d6c90d055cf7c2ed876c006c8d`.
- `MAX_OPEN_CHANGED = NO` (`max_open_positions = 1`).
- `MAX_NEW_COMMANDS_CHANGED = NO` (`max_new_commands = 1`).
- `PORTFOLIO_CONCURRENCY_POLICY_CHANGED = NO`.
- `TRADING_THRESHOLDS_CHANGED = NO`; `PARAMETER_TUNING = NO`.
- `BOOTSTRAP_CHANGED = NO`; `EMPIRICAL_POLICY_CHANGED = NO` (the empirical
  regime identity/mapping contract changed, not admission or probability rules).
- `15M_CHANGED = NO`; `V1_USED = NO` as runtime/statistical authority.
- `LIVE = DISABLED`; runtime control has `allow_live = false`.
- `REAL_BINANCE_ORDER_CALLS = 0`; deployed health safety counters report zero
  private API use, orders, positions, and executable approvals for the observed cycle.
- No file below `config/trading/` changed relative to pre-task commit
  `88f340eb57f26668d0e854259713ab84be97a1a5`.

## Root causes and corrections

1. The read projection was command-rooted. Plans without commands were invisible.
   It is now rooted in `paper_plan_execution_outcomes` and left-joins command,
   entry order, position, exit decision/fill, and the latest hold decision.
2. A continuous single-slot capacity return occurred before eligible plans were
   observed. It now persists the selector outcome and exact capacity blocker while
   preserving the same early fail-closed return and creating no command.
3. CLOSED projection used a generic close label. It now carries the canonical exit
   decision/hold reason, decision time, fill time, and modeled Net PnL diagnostics.
4. Images did not carry an immutable source revision. Both builds now require a
   revision argument, label the image, expose it to runtime, and export both row and
   projection revisions without reading the host checkout.
5. Empirical normalization silently fell back to `UNKNOWN`. A versioned mapping is
   now shared by persistence and lookup; its version is part of the bucket identity.
6. Full-window lifecycle loading selected every hold decision and exhausted the
   old 512 MiB Readonly limit. The query now selects the latest hold per position;
   the production Readonly service has a 1 GiB bound. A 10.9 MB four-hour export
   completed with no OOM or restart.

## Lifecycle state machine and terminal taxonomy

```text
FINAL_APPROVAL -> PAPER_PLAN -> SELECTED / NOT_SELECTED
SELECTED -> COMMAND_CREATED | BLOCKED_BY_POLICY | EXECUTION_FAILED |
            EXPIRED_BEFORE_EXECUTION
COMMAND_CREATED -> ENTRY_ORDER_PENDING -> POSITION_OPENED |
                   POSITION_NOT_OPENED_WITH_REASON
POSITION_OPENED -> OPEN -> EXIT_DECIDED -> EXIT_FILLED -> CLOSED
```

Export mappings are machine-readable:

| Durable fact | Export state | Required reason |
|---|---|---|
| command persisted | `COMMAND_CREATED` | `COMMAND_CREATED` |
| position persisted | `POSITION_OPENED` | `POSITION_OPENED` |
| `NOT_SELECTED` | `COMMAND_BLOCKED` | `LOWER_SELECTOR_RANK` |
| `BLOCKED_BY_POLICY` | `COMMAND_BLOCKED` | exact blocker, including `MAX_OPEN_POSITIONS_REACHED` or `MAX_NEW_COMMANDS_PER_CYCLE_REACHED` |
| `EXECUTION_FAILED` | `COMMAND_REJECTED` | canonical failure code |
| `EXPIRED_BEFORE_EXECUTION` | `COMMAND_EXPIRED` | `EXPIRED_BEFORE_EXECUTION` |
| command without a position | command state plus null position | entry-order reason or `COMMAND_PENDING_EXECUTION` |

Reprocessing remains idempotent: a plan has at most one outcome, one command, and
one position. No historical command was recreated and no historical outcome was
rewritten.

## Exit projection contract

For a CLOSED position, `exit.reached = true`, `exit.status = REACHED`,
`exit.reason` is the canonical execution/hold reason, and `exit_decision_at`,
`exit_fill_at`, and `position_closed_at` are projected separately. Supported
canonical reasons are passed through without a generic replacement, including
`STOP_LOSS`, `TARGET_REACHED`, `MOMENTUM_REVERSAL`, `STRUCTURE_INVALIDATED`,
`SETUP_INVALIDATED`, `MOMENTUM_INVALIDATED`, `STALE_SCALP`,
`NET_PNL_PROTECTION`, `MAX_HOLD_TIME`, and `SYSTEM_SAFETY_EXIT` when present.

Net PnL Protection projection includes window state, trigger state/time/1m boundary,
modeled executable Net PnL, quantized value, and the typed exit reason. Its business
logic, window, and profit threshold were not changed.

## Runtime provenance contract

```text
Git implementation commit
  -> required Docker build arg TRADERS_RUNTIME_SOURCE_IDENTITY
  -> org.opencontainers.image.revision image/container label
  -> immutable runtime environment
  -> persisted effective_configuration.source_commit/runtime_revision/image_revision
  -> export projection_runtime_revision + revision_match
```

The export code does not invoke Git or a subprocess. Historical `UNSET` values are
preserved rather than fabricated. A mismatch is explicit (`revision_match = false`).
Rows generated by revision-carrying orchestrators already show non-`UNSET` commits;
no new market cycle was awaited solely to produce a row at the final revision.

Final deployed artifacts:

- orchestrator image `sha256:48d18bf271ec36dcc8f99f79e3cb201a7b259be0eca28f566b36e1d66040a913`;
- Readonly image `sha256:62d169259f7c25c904ef0e4ebc444ff054e647b05ff5129fcd6a1fe9da2bac25`;
- both running containers label revision
  `668dd099dcdf27d6c90d055cf7c2ed876c006c8d`;
- both containers running, restart count `0`, OOM `false`; Readonly healthy with
  `1073741824` byte memory limit.

## Empirical regime mapping

Mapping version: `empirical-regime-v1`.

| Source regime | Normalized empirical regime | Reason |
|---|---|---|
| `UP` | `UP` | `DIRECTIONAL_REGIME_PRESERVED` |
| `DOWN` | `DOWN` | `DIRECTIONAL_REGIME_PRESERVED` |
| `FLAT` | `RANGE` | `ENGINE_FLAT_MAPS_TO_SCALPING_RANGE` |
| `RANGE` | `RANGE` | `SCALPING_RANGE_PRESERVED` |
| `COMPRESSION` | `COMPRESSION` | `SCALPING_VOLATILITY_REGIME_PRESERVED` |
| `EXPANSION` | `EXPANSION` | `SCALPING_VOLATILITY_REGIME_PRESERVED` |
| `UNKNOWN` | `UNKNOWN` | `SOURCE_REGIME_UNKNOWN` |
| unsupported | `UNKNOWN` | `UNSUPPORTED_SOURCE_REGIME_QUARANTINED` |

The same normalizer is used by persisted observation and probability lookup. Bucket
keys include the mapping version, so old incompatible buckets are isolated and no
mass relabel/rewrite is performed.

## Timestamp semantics

- Opportunity/event boundary: `opportunity_boundary`.
- Snapshot persistence: `snapshot_created_at`, `snapshot_updated_at`.
- Plan transition: `plan_created_at`.
- Command transition: `command_created_at`, `command_updated_at`.
- Position transition: `position_opened_at`, `position_updated_at`,
  `position_closed_at`.
- Exit causality: `exit_decision_at`, `exit_fill_at`.
- Latest durable lifecycle change: `last_lifecycle_event_at`.
- Read-model refresh: `projection_generated_at`.

## Deterministic verification

| Matrix | Result |
|---|---|
| plan -> command -> position; duplicate suppression and rollback | PASS |
| no-command selector/capacity/expiry/failure reason | PASS |
| command without position reason | PASS |
| typed STOP/TARGET/NET_PNL/MAX_HOLD exit projection and invariant | PASS |
| provenance without host Git lookup | PASS |
| all supported regime mappings; persistence/lookup parity | PASS |
| bootstrap, empirical, and `trade-15m-v1` regression | PASS |
| focused projection/regime/15m suite | 97 passed |
| relevant follow-up suite | 56 passed |
| isolated PostgreSQL transactional/idempotency suite | 285 passed, 2 warnings |
| final lifecycle/outcome/export suite | 31 passed |
| Python compile | PASS |
| Alembic local/production | `0033_net_pnl_protection` / `0033_net_pnl_protection` |

One broad security matrix remains red only on the pre-existing tracked Binance
credential reference/default policy finding; 275 other tests in that run passed.
Two pre-existing runtime-config epoch tests remain sensitive to an active winner
override. Neither was changed or weakened for this task. Ruff is not installed in
the environment.

## Read-only four-hour corroboration

At `2026-09-20T12:23Z`, the existing four-hour export returned 480 rows across 48
boundaries. It contained five pipeline `PAPER_PLAN_READY` snapshots, three persisted
lifecycle outcomes/commands, two positions, and two CLOSED positions. Both CLOSED
rows passed the exit invariant with reasons `STALE_SCALP` and `STOP_LOSS`.

Two snapshot plans in that historical window predate the final capacity-observation
fix and therefore remain without a persisted outcome; they were not backfilled with
an inferred reason. The deterministic capacity test proves the final code records
`BLOCKED_BY_POLICY / MAX_OPEN_POSITIONS_REACHED` without a second command. The user’s
next natural four-hour window is the acceptance source for all-new rows.

`WAITED_FOR_MARKET = NO`; `WAITED_FOR_4H_REPORT = NO` (the existing window was read
once as technical corroboration; no new window or event was awaited).
