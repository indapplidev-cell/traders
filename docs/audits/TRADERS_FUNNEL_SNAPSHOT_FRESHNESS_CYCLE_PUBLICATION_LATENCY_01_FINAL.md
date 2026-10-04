# Funnel snapshot freshness / cycle publication latency — final audit

## Verdict

```text
TASK = TRADERS_FUNNEL_SNAPSHOT_FRESHNESS_CYCLE_PUBLICATION_LATENCY_01
PROMPT_SHA256 = 1EE095CA6220944418CD706E2D9A8E702BD12761B5826F44345E93911F7B7086
FINAL_STATUS = PASS_WITH_DISCLOSED_PREEXISTING_BROAD_CLIENT_TEST_DEBT
FINAL_VERDICT = CLIENT_REFRESH_LATCH_REMEDIATED_WITH_BACKEND_PUBLICATION_UNCHANGED
ROOT_CAUSE_LAYER = DESKTOP_AUTO_REFRESH_LIFECYCLE
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
```

The missing 22:35, 22:40, and 22:45 UTC cycles were produced, completed for
all 20 symbols, and persisted normally. They were not suppressed by the Funnel
resolver and were not intentionally pinned by the view. During the stale
interval the desktop stopped issuing Funnel GETs. The client scheduler could
retain its private `in_flight` latch after the authoritative async-loader scope
had already completed if a Tk notification/render path did not reach
`auto_refresh.observe()`. There was no watchdog or scope reconciliation for the
Funnel page, so the next 10-second refresh could be suppressed indefinitely.

## Starting state

```text
BACKEND_STARTING_HEAD = bb2e8600b43bfcbeaff16779fac2b4c8bd664f3c
BACKEND_STARTING_UPSTREAM = bb2e8600b43bfcbeaff16779fac2b4c8bd664f3c
CLIENT_STARTING_HEAD = 66b3b7e0d4f090fd4d598804cafd30387e969c6f
CLIENT_STARTING_UPSTREAM = 66b3b7e0d4f090fd4d598804cafd30387e969c6f
DEPLOYED_BACKEND_SOURCE = c5e8db625df526eab6cc648ec29387aa148b976b
ALEMBIC = 0037_continuous_two_lifecycle_slots
ORCHESTRATOR_RESTART_COUNT = 0
READONLY_API_RESTART_COUNT = 0
OPERATOR_CONTROL_RESTART_COUNT = 0
```

Pre-existing backend deletions under `artifacts/scalping_v2_parameter_sweep/**`
and the modification to
`tests/operator_control_production_deployment/test_production_lifecycle_worker.py`
were preserved and excluded. Pre-existing client changes to
`trading_funnel_view.py` and `test_trading_funnel.py` were also preserved and
excluded from the task commit.

## Forensic timeline

Times below distinguish cycle boundary, persistence, server response, and
desktop render. `persisted_max` is the latest `online_pipeline_runs.updated_at`
among the 20 authoritative rows for that boundary.

| Cycle boundary UTC | Orchestrator started | Orchestrator completed | Symbols | Complete | Persisted max | Desktop/API evidence |
|---|---:|---:|---:|---|---:|---|
| 22:30 | 22:30:24.389808 | 22:30:34.858049 | 20/20 | yes | 22:30:34.859527 | Desktop showed this cycle during the reported stale interval |
| 22:35 | 22:35:28.606689 | 22:35:35.657459 | 20/20 | yes | 22:35:35.658526 | No desktop Funnel request was made after publication |
| 22:40 | 22:40:17.391944 | 22:40:24.800855 | 20/20 | yes | 22:40:24.802431 | No desktop Funnel request was made after publication |
| 22:45 | 22:45:38.855884 | 22:45:44.625142 | 20/20 | yes | 22:45:44.626278 | No desktop Funnel request was made after publication |
| 22:50 | 22:50:26.079088 | 22:50:30.549958 | 20/20 | yes | 22:50:30.551340 | Next desktop GET completed 22:54:12; reported UI jumped to 22:50 |

Readonly API access logs show regular desktop Funnel GET responses through
22:34:28 UTC, no Funnel request at all from 22:34:29 through 22:54:11, then a
successful response at 22:54:12. Server health continued returning 200 about
every 12 seconds during the entire gap. This excludes a stopped API and proves
that stale retention occurred before HTTP dispatch. A later direct API sample
returned the newest complete cycle with 20/20 rows in 1.862 seconds.

```text
MISSING_CYCLES_NOT_PRODUCED = NO
PRODUCED_BUT_NOT_PERSISTED = NO
PERSISTED_BUT_NOT_RETURNED_BY_API = NO_EVIDENCE; DIRECT_API_ADVANCED_NORMALLY
RETURNED_BUT_RETAINED_BY_CLIENT = CLIENT_DID_NOT_DISPATCH_GET_DUE_REFRESH_LATCH
INTENTIONALLY_PINNED_BY_UI = NO
```

## Root cause and fix

`PageAwareAutoRefreshController` tracked both the loader scope and a private
`_in_flight` flag. Normal completion cleared the loader registration before the
state notification rendered. If that notification/render sequence did not
reach `observe()`, the loader correctly reported no active Funnel scope while
`_in_flight` remained true. The heartbeat only reconciled this mismatch during
a manual refresh request; its ordinary automatic path suppressed all later
refreshes forever.

The heartbeat now treats `page_is_busy()` as authoritative on every tick. If a
request scope has completed while `_in_flight` is still set, it releases the
latch and schedules the existing page interval. The next Funnel GET therefore
occurs after the normal 10 seconds. No extra timer, overlapping request, direct
server access, or mutation path was added.

```text
CLIENT_IMPLEMENTATION_COMMIT = 4b9fd651e1ad89a3daa158a48ae36c601705fc2f
CHANGED_RUNTIME_FILE = src/traders_client/ui/auto_refresh.py
CHANGED_TEST_FILES = tests/test_auto_refresh.py; tests/test_client_state.py
BACKEND_CHANGED = NO
CACHE_INVALIDATION_CHANGED = NO
CYCLE_RESOLVER_CHANGED = NO
SNAPSHOT_PERSISTENCE_CHANGED = NO
UI_RENDER_SELECTION_CHANGED = NO
NEW_OBSERVABILITY_FIELDS = NONE
```

### Freshness contract

Before: a completed loader scope could leave auto-refresh latched indefinitely,
so the live Funnel could remain at T after T+5, T+10, and T+15 had completed.

After: loader completion is reconciled within one heartbeat; absent a live
request scope, the normal 10-second Funnel interval is restored. Each newer
authoritative payload replaces the prior immutable client snapshot. Historical
detail identity remains exact and is not rebound by symbol.

## Verification

```text
BACKEND_FUNNEL_TESTS = 33_PASSED
CLIENT_FOCUSED_REFRESH_STATE_FUNNEL_TESTS = 56_PASSED
CLIENT_AUTO_REFRESH_TESTS = 24_PASSED
CLIENT_COMPILEALL = PASS
LATEST_COMPLETE_ADVANCES_TEST = PASS_EXISTING_BACKEND_SUITE
MONOTONIC_CURRENT_CYCLE_TEST = PASS_EXISTING_BACKEND_AND_NEW_CLIENT_SEQUENCE
INCOMPLETE_CYCLE_FALLBACK_TEST = PASS_EXISTING_BACKEND_SUITE
API_STALE_CACHE_TEST = PASS_EXISTING_BACKEND_SUITE
CLIENT_REPLACES_OLDER_CYCLE_TEST = PASS_T_T_PLUS_5_T_PLUS_10
CLIENT_BACKWARD_COMPAT_TEST = PASS_EXISTING_FUNNEL_SUITE
AUTO_REFRESH_ROW_INTEGRITY_TEST = PASS_EXISTING_FUNNEL_SUITE
```

The full client suite completed with `1528 passed, 2 skipped, 3030 subtests`
and six failures. None touches the three task files. The failures reproduce
existing Tk/i18n and PAPER timing/contract debt in `test_i18n_gui.py`,
`test_paper_execution_sync.py`, `test_paper_foundation.py`,
`test_real_server_http_interop.py`, and `test_server_i18n_consumer.py`.
Changed-scope tests and compile are green; no task-caused regression remains.

## Desktop and runtime acceptance

The desktop was restarted on the committed client code. Mandatory Win32
preflight passed for PID 2248 / HWND 1444758 with foreground activation,
responsiveness, same session, `WinSta0` / `Default`, compatible integrity, and
full-desktop crop capture. UIA unavailability was non-blocking. Navigation was
read-only and no mutation control was used.

```text
DESKTOP_INITIAL_RENDER = CURRENT_23:05_TO_23:10; LAST_23:00_TO_23:05; 20_OF_20
DESKTOP_NEXT_AUTO_RENDER = CURRENT_23:10_TO_23:15; LAST_23:05_TO_23:10; 20_OF_20
DESKTOP_SECOND_AUTO_RENDER = CURRENT_23:15_TO_23:20; LAST_23:10_TO_23:15; 20_OF_20
API_AT_SECOND_TRANSITION = GENERATED_23:21:12.558Z; CURRENT_BOUNDARY_23:20; LAST_BOUNDARY_23:15; CYCLE_COMPLETE_TRUE; 20_OF_20
NATURAL_CYCLE_TRANSITIONS_OBSERVED = 2
MANUAL_REFRESH_USED_FOR_TRANSITION = NO
AUTO_REFRESH_INTERVAL = 10_SECONDS
HEALTH = OK
PAPER_READINESS_STATUS = READY
UNIVERSE = 20_OF_20
PAPER_CONTROL = CONTINUOUS_ARMED_GENERATION_16
LIVE_ALLOWED = FALSE
REAL_BINANCE_ORDER_CALLS = 0
```

## Regression freeze

No selector rank policy, rank #3 backfill, strategy/quality/setup logic,
Target/Stop/Entry/TTL, cost model, RR/dynamic RR/empirical EV, risk sizing,
2-command/2-position limits, lifecycle slots, exit policy, Net PnL Protection,
Universe20, trade-15m-v1, or LIVE behavior changed. Backend images, services,
database schema, and production source revision were not rebuilt or restarted.
