# Autonomous multi-position continuous PAPER 1/1 -> 2/2 — final audit

## 1. Starting state / verified 1/1 baseline

`FINAL_STATUS = PASS`

The task started from backend `99513ee624306175abbbf89aa77d2c63553f7e4e`
and desktop `714432bab4f02672f24305972fd1ea229df4b353`.
Production was `CONTINUOUS_ARMED`, generation 15, with an arming scope of one
new command and one open position, Alembic
`0036_empirical_requalification_authority`, Universe20, and LIVE disabled.
At the immediate pre-migration boundary production contained 87 PAPER commands
and 85 positions: 0 open and 85 closed. No active lifecycle existed.

Pre-existing user work was preserved: parameter-sweep artifact deletions and
the lifecycle-worker test change in traders-ml, plus Funnel positive-candidate
sorting and its tests in traders-client. None was staged or claimed by this
task. The generated desktop catalog necessarily incorporates the authoritative
server catalog as one integrity-hashed generated artifact.

## 2. Migration design proof

The previous partial unique index admitted only one non-terminal lifecycle per
environment. The smallest compatible extension is a nullable
`lifecycle_slot`, constrained to 1 or 2, required only for non-terminal rows,
and a partial unique index on `(environment, lifecycle_slot)` for non-terminal
states. Existing terminal history remains nullable and untouched. Any active
row present during upgrade is assigned slot 1.

The two permitted rows retain the existing one-row/one-command/one-position
foreign keys, unique command and position indexes, and per-lifecycle counters
limited to 0..1. Thus the hard model is:

```text
slot 1 lifecycle -> command A -> position A
slot 2 lifecycle -> command B -> position B
```

There is no aggregate pseudo-position. A third active lifecycle has neither a
valid third slot nor a duplicate-free `(environment, slot)` and is rejected.
Store allocation is serialized by locking the singleton continuous-control
row. Restart reads all active rows, and lifecycle processing iterates both;
closing or fail-safing one row does not terminalize the other. Downgrade refuses
to collapse a database containing more than one active lifecycle.

This design changes capacity only. Strategy/ranking math, setup and quality,
entry/stop/target, RR/EV, fees/costs, sizing, risk per position, total risk,
TTL, exits, Universe20, trade-15m-v1, exploration/requalification and LIVE are
unchanged.

## 3. Alembic/schema change

Migration `0037_continuous_two_lifecycle_slots.py` upgraded a real PostgreSQL
16 test database from 0036, preserved its rows, admitted slots 1 and 2,
rejected a third, rehydrated both after store reconstruction, independently
closed A and B, and reused the freed slot without disturbing its peer.

Production was upgraded only through Alembic. Immediately afterward it
reported revision `0037_continuous_two_lifecycle_slots`, 87 commands and 85
positions (0 open, 85 closed), exactly matching the pre-migration counts. All
276 historical lifecycle rows remained; terminal history was not rewritten.
No synthetic command, position, trade, or empirical observation was created.

Actual production constraints include:

- `ck_paper_canary_lifecycle_slot`: NULL or 1..2;
- `ck_paper_canary_active_lifecycle_slot`: non-terminal rows require a slot;
- `uq_paper_canary_active_lifecycle_slot`: partial unique
  `(environment,lifecycle_slot)` for non-terminal states;
- existing unique `command_id` and `position_id` constraints;
- existing per-lifecycle command/position counters 0..1.

## 4. Runtime 2/2 authority

Continuous activation now performs a single safe self-transition only when
generation 15 is still armed at 1/1 and no lifecycle is active. Production
completed that transition to generation 16 with reason
`CONTINUOUS_CAPACITY_UPGRADE`; persisted arming scope is exactly 2 commands and
2 open positions. The continuous authority stayed armed and LIVE stayed false.

The executor applies `open + reserved <= 2`, dispatches durable rank-1/rank-2
selection across polls, and never expands the limit above two. The continuation
worker no longer treats one in-flight command as global exhaustion. The
lifecycle worker supervises every active lifecycle independently.

## 5. Independent lifecycle semantics

Deterministic PostgreSQL/store and worker tests prove two independent active
rows, restart rehydration, third-row rejection, close A while B remains active,
close B while its replacement remains active, and no duplicate command or
position on replay. Command and position uniqueness remains database-enforced.

## 6. Rank1/rank2 selector

The existing deterministic ordering and tie-break are unchanged. Selection is
bounded to the first two ranks only. Rank 2 is evaluated against projected
state containing existing reservations plus rank 1's reservation and risk.
When rank 2 fails, rank 3 is not promoted. Tests cover two valid candidates,
open-one/open-two capacity, rank-2 rejection, duplicate-symbol behavior,
projected risk, total-open-risk parity, and idempotent replay/restart.

## 7. API/observability

The Funnel projection compatibly adds candidate `selection_slot` and cycle
counts for selected candidates, commands, opened/closed positions, current
open positions, and maxima of two. PAPER position/trade reporting adds
`lifecycle_slot`, selector rank/status, and causal cycle boundary. Existing
command state, position state/id, reason and selector status remain canonical.

At acceptance the deployed Funnel returned a complete 20-symbol cycle and a
complete previous cycle, with selected/commands/open `0/2`, all maxima equal
to 2, and no overwritten rows.

## 8. Funnel UI + i18n

The existing screen now renders authoritative `selected`, `commands`, and
`open positions` capacity summaries; rows and detail expose selector rank,
selection/lifecycle slot, selector state, command/position status and reason.
Missing legacy optional fields remain renderable. All added visible strings use
the generated server i18n catalog; no view-local RU/EN dictionary was added.

## 9. PAPER Trading UI + i18n

The former single-position presentation is now a 0/1/2-row active-position
table. Explicit selection loads only that position's detail. The screen shows
authoritative cycle commands/opened/closed and global open-position counts,
and history/report rows include cycle boundary, selector rank and lifecycle
slot. Legacy rows without these optional fields use the existing unavailable
representation. All added labels and summaries are i18n keys.

## 10. Backend/UI tests

```text
BACKEND_COMPILEALL = PASS
BACKEND_FOCUSED_SELECTOR_API_REPORTING = 1868 passed; 1 deselected
BACKEND_MULTI_POSITION_AND_CHANGED_CONTRACTS = 9 passed; 2 skipped
POSTGRESQL_16_DIRECT_MULTI_LIFECYCLE = PASS
CLIENT_MULTI_POSITION_UI = 3 passed
CLIENT_TASK_FUNNEL_AND_INTEGRATION = 28 passed; 1309 subtests
```

Broad disclosure, not reported as a clean gate:

```text
BACKEND_FULL = 31911 passed; 54 skipped; 221 failed; 349 errors
CLIENT_FULL = 1524 passed; 2 skipped; 8 failed; 3030 subtests
```

The broad backend failures are dominated by mutually incompatible/missing
PostgreSQL fixture URLs, absent external evidence, stale revision/route-count
assertions and old configuration expectations. The remaining desktop failures
are existing source-shape/locale expectations, Tk interpreter/timing and real
HTTP environment tests. A task-caused help-catalog mismatch found in the broad
run was corrected and its focused catalog test passed. No task-required 2/2
contract remains failing.

## 11. Production migration/deployment

Backend implementation commit and immutable runtime source identity:
`c5e8db625df526eab6cc648ec29387aa148b976b`.

Only the 5m orchestrator, operator-control API and readonly API were rebuilt
and recreated; PostgreSQL, market-data sync and calibration collector were not
restarted. Accepted image IDs are:

```text
orchestrator  sha256:7530305ad728eafa2b62fa5ae3ae486b56d4e9c36bd6b9c22702616702c7b916
operator      sha256:946a16012abe94a6a871c0160fea03fe095f77ca7a09835f017d428796fdfc02
readonly      sha256:8c5545d76a895bb202375687dcbacc95dcf14ee144c74cef24c5f4636e45616e
```

Each image carries the full 40-character revision label. Restart counts are
zero; readonly and operator healthchecks are healthy. Readiness recovered after
its bounded background refresh: schema 0037, runtime/daemon/mutation ready,
commission READY 20/20 from authenticated account data, no mutation denials,
and LIVE false. Orchestrator health is OK, owner acquired, Universe20 complete,
and safety counters contain zero private API/order/position side effects.

## 12. Desktop smoke

The Tk client was restarted at desktop commit
`af5123323b18dc7a09187ab6b7628689fd28e723`. Required PID/HWND preflight passed
on PID 7780 / HWND 1903538: same session, WinSta0/Default desktop, compatible
medium integrity, responsive visible window, foreground activation and
full-desktop cropped capture. UIA absence was non-blocking by policy.

Read-only navigation showed the deployed Funnel with `0/2` summaries and PAPER
Trading with `0/2` summary plus lifecycle-slot table. PAPER/account/history and
reconciliation remained readable, LIVE visibly disabled, and no raw i18n key
or crash appeared. No control, disable, emergency, strategy, risk or LIVE
control was touched.

## 13. Regression freeze

Only the two capacity values changed from 1 to 2. Risk remains 5 equity basis
points per position and max total open risk remains 50 basis points. Target,
stop, entry/refinement/window, TTL, cost/commission/spread/slippage, RR,
dynamic RR, empirical EV, position sizing, same-symbol protection, exits, Net
PnL Protection, Universe20, trade-15m-v1, exploration/requalification and LIVE
are unchanged.

## 14. Pre-existing debt vs task-caused issues

The broad-suite debts above were retained and disclosed. Two failed one-shot
migration command wrappers were quoting-only failures and executed no DDL; the
same Alembic migration then ran successfully through a temporary in-container
runner without exposing or persisting credentials. Task-owned temporary files
were removed. No unrelated dirty file was overwritten or staged.

## 15. Final runtime state

```text
FINAL_VERDICT = AUTONOMOUS_MULTI_POSITION_2_IMPLEMENTED_TESTED_MIGRATED_DEPLOYED_AND_DESKTOP_ACCEPTED
ALEMBIC = 0037_continuous_two_lifecycle_slots
CONTROL = CONTINUOUS_ARMED_GENERATION_16_SCOPE_2_2
HEALTH = PASS
READINESS = PASS
UNIVERSE = TRADING_UNIVERSE_V3_EXACT_20
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
NATURAL_TWO_COMMAND_CASE = NOT_OBSERVED
NATURAL_TWO_ACTIVE_POSITIONS_CASE = NOT_OBSERVED
SYNTHETIC_PRODUCTION_TRADES_CREATED = NO
CURRENT_BLOCKER = NONE
NEXT_ACTION = PASSIVE_NATURAL_OBSERVATION;_DETERMINISTIC_TESTS_ARE_THE_2_POSITION_PROOF
```
