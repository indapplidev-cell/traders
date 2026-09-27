# Traders post-remediation natural continuation and freshness latency — final audit

## A. Prior remediation state

This audit starts from the already deployed full-cycle remediation. It does not
reopen the Binance ingestion stack, readiness architecture, exit policy, risk,
strategy, geometry, selector ranking, causal entry window, or trade-plan TTL.
The earlier deterministic PostgreSQL coverage for TARGET, STOP, TIME_EXIT, and
NET_PNL_PROTECTION remains valid. LIVE remained disabled and no real Binance
order call was made.

The prior state already demonstrated a natural ADAUSDT PAPER lifecycle through
OPEN and CLOSED. This task narrowed the remaining work to continuation pickup,
20-symbol release timing, lightweight rolling UI aggregates, and immutable
selector export facts.

## B. Natural cases

All times below are UTC and were reconstructed from canonical production rows
and durable runtime telemetry. A command row's `created_at` is a causal domain
timestamp. Where present, `command inserted` is the separately persisted
wall-clock telemetry and is the correct value for runtime latency.

### DOGEUSDT, boundary 2026-09-27 11:35:00

| Event | UTC | Delta from boundary |
|---|---:|---:|
| analysis start | 11:35:26.396268 | 26,396.268 ms |
| analysis finish / 20-of-20 complete | 11:35:30.670465 | 30,670.465 ms |
| plan created | 11:35:30.611 | 30,611 ms |
| selector start | 11:35:37.842973 | 37,842.973 ms |
| SELECTED / first durable observation | 11:35:37.843053 | 37,843.053 ms |
| first claim | 11:35:37.879422 | 37,879.422 ms |
| later pending observation | 11:36:03.851674 | 63,851.674 ms |
| terminal ENTRY_FILL_WINDOW_MISSED | 11:36:03.958420 | 63,958.420 ms |
| required 1m persisted | 11:36:15.190918 | after terminal |

`BOUNDARY_TO_CYCLE_COMPLETE_MS=30670.465`,
`CYCLE_COMPLETE_TO_SELECTOR_MS=7172.508`, first selected-to-claim was only
`36.369 ms`, but the strict deadline elapsed before the required closed 1m row
became locally available. Primary class: **F. 1M_INGEST_DELAY**. Secondary:
**E. REQUIRED_1M_NOT_YET_AVAILABLE**, with a later fixed-poll/heavy-retry
observation. The causal rule correctly rejected the command.

### ADAUSDT, boundary 2026-09-27 11:40:00

| Event | UTC | Delta from boundary |
|---|---:|---:|
| analysis start | 11:40:26.521364 | 26,521.364 ms |
| analysis finish / 20-of-20 complete | 11:40:30.949478 | 30,949.478 ms |
| plan created | 11:40:30.759 | 30,759 ms |
| selector start | 11:40:43.306057 | 43,306.057 ms |
| SELECTED | 11:40:43.306107 | 43,306.107 ms |
| first claim | 11:40:43.321686 | 43,321.686 ms |
| command wall insertion | 11:40:59.375332 | 59,375.332 ms |
| required 1m persisted | 11:41:14.709660 | 74,709.660 ms |
| SHADOW refinement | 11:43:43.095 | non-blocking |
| position OPEN / STOP decision / CLOSED | 11:41 / 11:42 / 11:43 | — |

The approximate 130 ms derived from the command row's causal `created_at` was
not wall-clock continuation latency. Canonical telemetry gives
`SELECTED_TO_COMMAND_MS=16069.225`. The command legitimately preceded the
required 1m row because refinement was SHADOW, then the natural position closed
with realized PnL `-0.11228237`. This is a successful lifecycle, but it exposes
an artificial durable rehydration/DB-read delay after the fast claim.

### ADAUSDT, boundary 2026-09-27 11:45:00

Analysis started at `11:45:42.515097`; the complete-cycle record was durable at
`11:45:47.469856`; the plan was created at `11:45:47.122`. Selector start and
SELECTED were `11:46:02.005435` and `11:46:02.005533`; claim/terminal was
`11:46:02.089777`. The plan still had `12,878 ms` at creation, but selection
occurred `2,005 ms` after the strict entry boundary. The required 1m row was
persisted at `11:46:14.417881`.

Primary class: **B. SELECTOR_DELAY** (`~14.536 s` cycle-complete-to-selector and
`~14.884 s` plan-to-selected). Secondary: **A. PLAN_CREATED_TOO_LATE** and the
normal not-yet-available causal candle. The terminal rejection was correct.

### FETUSDT, boundary 2026-09-27 11:55:00

Analysis started at `11:55:40.797462`; 20-of-20 completed at
`11:55:47.149265`; the plan was created at `11:55:47.093`. Selector start and
SELECTED were `11:56:04.950676` and `11:56:04.950754`; claim/terminal was
`11:56:04.967252`. The plan still had `12,907 ms` at creation, while selection
was `4,950 ms` after the boundary. The required 1m row persisted at
`11:56:16.887303`.

Primary class: **B. SELECTOR_DELAY** (`~17.802 s` cycle-complete-to-selector).
Secondary: **A. PLAN_CREATED_TOO_LATE** and the causal candle availability.

### Natural post-fix observation: AVAXUSDT, boundary 13:35:00

No trade was forced. Analysis started at `13:35:22.077267`; the twentieth
symbol started at `13:35:22.547889`; 20-of-20 completed at
`13:35:26.963612`; the plan was created at `13:35:26.924`. Selector start and
SELECTED were `13:35:33.601337` and `13:35:33.601430`; first claim was
`13:35:33.645492` (`44.062 ms`). Exact-run rehydration was observed at
`13:35:48.300400`, and command wall insertion at `13:35:49.841623`, giving
`SELECTED_TO_COMMAND_MS=16240.193`.

The position opened causally at `13:36:00`, closed at `13:38:00` through
MOMENTUM_REVERSAL, and persisted realized PnL `-0.019124506`. The required 1m
row closed at `13:35:59.999` and persisted from REST at
`13:36:15.894893`. Later SHADOW refinement rejected price drift at
`13:38:37.721012`; it did not block or rewrite the command/lifecycle decision.

## C. Continuation root cause

`CONTINUATION_TRIGGER=BOUNDED_POLL_OF_DURABLE_SELECTED_OUTCOME`.
Before the change, the worker had a hard 5-second minimum poll and retried a
broad 20-symbol approval/refinement scan before prioritising an already durable
winner. The fix lowers the default/minimum poll to `500/250 ms`, rehydrates the
durable selected run first, and skips unrelated broad scanning when that run is
available.

Natural first selected-to-claim pickup is fast (`p50=36.4 ms`). Nevertheless,
the two successful natural commands with wall-insertion telemetry still show
about 16 seconds selected-to-command. AVAX specifically spent about 13.4
seconds before exact-run rehydration under production load. No lock wait was
proven; the remaining blocker is the exact durable read/DB-load segment, not
readiness, selector policy, or a causal grace period. Therefore the overall
verdict is **PARTIAL**, not PASS.

Across the five natural selected cases:

```text
PLAN_TO_SELECTED_P50_MS = 12547.1
SELECTED_TO_CONTINUATION_VISIBLE_P50_MS = 0 (selection row is the durable visibility event)
CONTINUATION_VISIBLE_TO_PICKUP_P50_MS = 36.4 (first claim proxy)
PICKUP_TO_CLAIM_P50_MS = NOT_SEPARATELY_PERSISTED
CLAIM_TO_1M_AVAILABLE_P50_MS = 31388.0
1M_AVAILABLE_TO_REFINEMENT_P50_MS = 141826.1 (three persisted pairs; SHADOW and non-blocking)
REFINEMENT_TO_COMMAND_P50_MS = NOT_APPLICABLE_SHADOW_NONBLOCKING
DATA_AVAILABLE_TO_CONTINUATION_PICKUP_P50_MS = NOT_OBSERVED
DATA_AVAILABLE_TO_CONTINUATION_PICKUP_P95_MS = NOT_OBSERVED
```

The last two values are deliberately not fabricated: no post-fix natural case
entered a persisted-data-wait state from which that metric could be measured.

## D. 1m causal timing

| Winner | Required open/close | Actual persisted | Close-to-persist | Refinement relation | Valid until |
|---|---|---:|---:|---|---:|
| DOGE 11:35 | 11:35 / 11:36 | 11:36:15.190918 | 15,191.918 ms | snapshot timestamp 748.9 ms before authoritative persistence; returned stale | 11:35:59.999 |
| ADA 11:40 | 11:40 / 11:41 | 11:41:14.709660 | 14,710.660 ms | SHADOW about 148.4 s later | 11:40:59.999 |
| ADA 11:45 | 11:45 / 11:46 | 11:46:14.417881 | 14,418.881 ms | terminal before data | 11:45:59.999 |
| FET 11:55 | 11:55 / 11:56 | 11:56:16.887303 | 16,888.303 ms | terminal before data | 11:55:59.999 |
| AVAX 13:35 | 13:35 / 13:36 | 13:36:15.894893 | 15,895.893 ms | SHADOW 141.826 s later | 13:39:59.999 plan validity; entry causal boundary unchanged |

Local receive is not separately persisted from ingestion for these REST rows,
so `LOCAL_RECEIVE_TO_PERSIST_MS` is unavailable. The observed REST persistence
lag is real. It must not be hidden by open/future candle use, a wider entry
window, TTL, grace, or fabricated timestamps. No causal rule was weakened.

## E. 20-symbol freshness release

The pre-change production cohort contains 67 complete cycles. Values are delta
from each 5m boundary:

| Metric | pre-change p50 | pre-change p95 | post-change bounded sample (n=1) |
|---|---:|---:|---:|
| first ready | 28,196.2 ms | 66,009.0 ms | 22,077.3 ms |
| tenth ready | 32,494.7 ms | 67,981.2 ms | 22,265.9 ms |
| twentieth ready | 35,294.6 ms | 67,981.2 ms | 22,547.9 ms |
| tenth-to-twentieth | 206.0 ms | 13,931.6 ms | 281.9 ms |

Root cause was fixed-cohort market-data boundary sync (`workers=4`) combined
with boundary retry cadence, rather than the canonical 20-symbol universe.
Workers were raised to eight, still below the configured DB pool plus overflow
ceiling. The first post-change cycle released all 20 analysis starts within
471 ms and completed at `+26,963.6 ms`. This is encouraging but `n=1` is not a
stable post-change p95; longer passive observation, not a forced trade, is the
next evidence step.

## F. Fix

Project-state commits:

- `b836cdcc1d6c497d70677e1bdfd7174bf9e97916`: fast bounded polling, durable
  winner priority, eight market-data boundary workers, scalar rolling
  aggregates, and durable selector export facts.
- `ff55238d3b51fc0efdbf4eba3cc30706e77313ab`: remove historical per-symbol
  detail from the interactive Funnel response; detail remains export-only.

The change does not alter decisions. It only removes artificial scheduling and
materialization work from the execution/observation path.

## G. True 1h/4h aggregates

The API performs two small SQL aggregate queries over scalar
`online_pipeline_runs` fields, one for one hour and one for four hours. It does
not materialize historical result JSON or lifecycle detail, and results use a
30-second cache. Production-like tests prove exact 12-by-20 and 48-by-20
mathematics (`240` and `960` analysis rows) and stage reached/passed/rejected/
conversion values. Interactive detail contains only current and previous
cycles; `historical_paper_plans_4h=[]`; detailed history remains in export.

The initial post-deploy production sample was p50 `297.9 ms`, p95 `392.3 ms`.
After the final export-only correction and cold restart, 20 warm calls measured
p50 `672.1 ms`, p95 `920.9 ms`, max `939.7 ms`: the `<1000 ms` p95 target still
passes. A deliberately tested historical JSON aggregate was rejected before
commit because it took about 99.7 seconds and violated the latency contract.

## H. Selector observability

Export now prefers the immutable `paper_plan_execution_outcomes` selector
decision over mutable/derived strategy JSON. It includes durable
`selector_status`, `selector_rank`, `selector_winner`, `selector_reason`, and
`selector_decided_at`. Later OPEN/CLOSED/STOP/expiry state is reported
separately and cannot rewrite the historical selector decision. UI semantics
remain separated into final approval, selector, command, position, terminal
reason, and 1m refinement.

## I. Tests

```text
compile = PASS
focused continuation/freshness/API/export = 60 passed
final Funnel/export regression = 47 passed
real PostgreSQL selected/refinement/deadline suite = 4 passed, 9 deselected
exact 20-symbol selected winner creates one command = PASS
authoritative 1m wait then expiry/no command = PASS
expired natural approval/no command = PASS
duplicate commands = 0
shared-session thread-safety regression = PASS
```

The broad continuation file also had 58 passes and three stale failures caused
by older readiness semantics/current-date fixtures. A separate old
`trade-5m-v1` owner test had seven stale-profile failures, five passes, and five
skips. Neither suite indicates a regression in the changed v2 path.

## J. Production smoke

Only market-data sync, operator-control, and read-only API were rebuilt/recreated
for the applicable commits. Orchestrator/lifecycle logic was not changed or
restarted. Read-only and operator containers are healthy with zero restarts;
market-data sync is running with zero restarts; PostgreSQL is healthy. Alembic
remains `0035_scalping_v2_ingestion_policy_contract`. Bounded affected-service
logs contained no ERROR, traceback, 429, or 5xx signal.

Readiness after the final read-only restart measured n=20, p50 `295.2 ms`, p95
`453.7 ms`, max `474.6 ms`; it is not the root cause. A direct Binance public
time probe was geo-blocked with HTTP 451 and excluded from RTT health evidence.
Production candle ingestion continued and affected-service logs showed no
429/5xx/retry regression, so `BINANCE_REGRESSION=NO` for the deployed path.

The bounded smoke naturally observed AVAXUSDT SELECTED → command → OPEN →
CLOSED. No trade was forced and profitability was not an acceptance criterion.
No new four-hour or twelve-hour Funnel collection was awaited.

## K. Invariants

```text
STRATEGY_CHANGED = NO
STRUCTURAL_SETUP_CHANGED = NO
GEOMETRY_CHANGED = NO
TARGET_CHANGED = NO
STOP_CHANGED = NO
RR_CHANGED = NO
COST_MODEL_CHANGED = NO
COMMISSION_POLICY_CHANGED = NO
RISK_CHANGED = NO
SELECTOR_RANKING_CHANGED = NO
PORTFOLIO_LIMITS_CHANGED = NO
MAX_OPEN_CHANGED = NO
MAX_NEW_COMMANDS_CHANGED = NO
TRADE_PLAN_TTL_CHANGED = NO
ENTRY_CAUSAL_WINDOW_CHANGED = NO
EXIT_POLICY_CHANGED = NO
NET_PNL_PROTECTION_CHANGED = NO
UNIVERSE_CHANGED = NO; EXACT_20_RETAINED
TRADE_15M_CHANGED = NO
LIVE_CHANGED = NO; LIVE_DISABLED
REAL_BINANCE_ORDER_CALLS = 0

FINAL_STATUS = COMPLETED_WITH_PARTIAL_VERDICT
FINAL_VERDICT = PARTIAL
DOGE_1135_ROOT_CAUSE = F_1M_INGEST_DELAY; SECONDARY_E_AND_FIXED_RETRY
ADA_1140_SUCCESS_TIMELINE = SELECTED_TO_COMMAND_16069.225MS; OPEN_TO_CLOSED_STOP
ADA_1145_ROOT_CAUSE = B_SELECTOR_DELAY; SECONDARY_A
FET_1155_ROOT_CAUSE = B_SELECTOR_DELAY; SECONDARY_A
INTERMITTENT_CONTINUATION_DELAY = IMPROVED_BUT_NOT_CLOSED
20_SYMBOL_STAGGERED_RELEASE = FIXED_IN_ONE_BOUNDED_SAMPLE; STABLE_P95_NOT_YET_PROVEN
CAUSAL_RULES_WEAKENED = NO
TRUE_1H_AGGREGATES = PASS
TRUE_4H_AGGREGATES = PASS
HISTORICAL_DETAIL_STILL_EXPORT_ONLY = YES
SELECTOR_RANK_EXPORT = DURABLE
SELECTOR_STATUS_EXPORT = DURABLE
SELECTOR_WINNER_EXPORT = DURABLE
HISTORICAL_RANK_NOT_REWRITTEN_BY_LIFECYCLE = YES
NATURAL_POST_FIX_WINNER = OBSERVED_AVAXUSDT_2026-09-27T13:35Z_CLOSED_MOMENTUM_REVERSAL
CURRENT_BLOCKER = EXACT_DURABLE_RUN_REHYDRATION_REMAINS_ABOUT_13S_UNDER_NATURAL_LOAD
NEXT_ACTION = PROFILE_AND_BOUND_EXACT_RUN_DB_READ; PASSIVELY_COLLECT_MORE_POST_FIX_COMPLETE_CYCLES; KEEP_LIVE_DISABLED
```
