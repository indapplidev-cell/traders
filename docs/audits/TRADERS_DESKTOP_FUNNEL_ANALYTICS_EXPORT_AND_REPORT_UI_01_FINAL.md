# TRADERS_DESKTOP_FUNNEL_ANALYTICS_EXPORT_AND_REPORT_UI_01

## Decision

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_DESKTOP_FUNNEL_ANALYTICS_EXPORT_AND_REPORT_UI_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE
```

## Architecture and contract

The existing calibration persistence reader, `export_record` normalization and
`aggregate` funnel/reason/geometry/cost/RR/churn/quota analytics are reused.
The former HTTP Funnel projection could not serve a bounded file export, so one
additive GET-only route was added:

```text
GET /api/v1/trading/funnel/export
trade_profile_id = trade-15m-v1 | trade-5m-v1
from/to = required UTC timestamps
symbol = optional authoritative symbol
format = jsonl | csv | summary-json | summary-md
include_candles = false; true fails closed
MAX_EXPORT_RANGE = 24h
MAX_EXPORT_ROWS = 2880
EXPORT_SCHEMA_VERSION = trading-funnel-export-v1
```

The repository performs one bounded ordered funnel query (`LIMIT 2881`) and
one bulk outcome query. It performs no write, lock acquisition, Control call,
exchange call, or per-row query. Unknown authoritative values remain null.
The allowlisted export contains provenance, market/analysis, closed-only
multi-timeframe boundaries, canonical eleven-stage trace, setup, strategy,
risk/quota, rejected geometry, costs/economics, RR cohorts, PAPER plan and
available command/position/outcome facts. Raw machine codes remain present;
free-form reasons are allowlisted and secret-like text is dropped.

## Desktop

The Funnel toolbar now contains `Refresh` and `Export report`. The modal maps
`Trade 15m` exactly to `trade-15m-v1` and `Trade 5m` exactly to
`trade-5m-v1`; its default follows the active Funnel profile and JSONL is the
default format. It supports current cycle, last completed cycle, 1h, 4h, 12h,
24h, custom UTC range, all/specific symbol, JSONL, CSV, summary JSON and
summary Markdown. The controller uses an independent asynchronous export lane,
does network and atomic file replacement off the Tk main thread, prevents
overlap, leaves refresh independent, and reports localized safe errors and the
saved path. RU/EN strings are generated from the server catalog.

## Runtime evidence

```text
READONLY_ROUTE_INVENTORY = 28_GET_0_WRITE
READONLY_REPLACEMENTS_BY_TASK = 3
FINAL_READONLY_CONTAINER = 8d3c0c95737295adc562f36e2797d650cb6e487279118840a88e15b7b4232366
FINAL_READONLY_IMAGE = sha256:24ee3ab79a2032b386a122a269a25f33c15eeac9ff372be24811152b265c524f
FINAL_READONLY_SOURCE = 2ca5e9c8533bdf4051c8307304f1420223810431
FINAL_READONLY_HEALTH_RESTARTS = healthy_0
15M_5M_CONTROL_POSTGRES_MARKET_DATA_RESTARTS_BY_TASK = 0
CONTROL = ARMED_GENERATION6_UNCHANGED
LIVE = DISABLED_UNCHANGED
```

One-hour production samples returned 40 rows/4 boundaries for 15m and 120
rows/12 boundaries for 5m, each with ten symbols, exact profile isolation and
deterministic ordering. JSONL, CSV, summary JSON and summary Markdown returned
200. The JSONL provenance reported catalog `i18n-32ca1702c73e2e56` and schema
`trading-funnel-export-v1`; the canonical trace contained analysis, setup,
strategy, geometry, cost, risk, paper_plan, final_approval, paper_command,
position and exit. In the sampled rejected row setup was `REJECTED`, later
stages were distinct `NOT_REACHED`, and unavailable spread was null. POST,
25-hour range and `include_candles=true` failed closed. Runtime scans across
all four formats found zero secret fields.

## Observer isolation

The active process identity was verified, not inferred from PID alone:

```text
PID = 23308
IMAGE = C:\Program Files\Python311\python.exe
COMMAND = scripts\observe_5m_scalping_calibration.py --wait --poll-seconds 60 --output-dir reports\5m_scalping_calibration_baseline_01
CREATED_LOCAL = 2026-08-24T21:44:51.267780+03:00
BOUNDARIES_BEFORE = 50
BOUNDARIES_AFTER_RUNTIME_ACCEPTANCE = 55
TASK_CAUSED_BOUNDARY_LOSS = 0
```

The observer PID, command, parentage, configuration, counting window and sample
semantics stayed unchanged. Its sealed JSONL, summary and manifest retained
their pre-task sizes, UTC modification times and manifest hashes; only the
observer-owned stdout advanced naturally. No observer artifact was opened for
write by this task.

## Recovery and validation

Canonical post-deployment diagnosis reported WAL health PASS, archive mode ON,
PITR lineage contiguous, active unresolved failures/backlog/pending all zero,
and `physical_wal_gap=false`. ACK owner PID 4912 retained the expected daemon
identity and healthy cadence. The known safe-inspection metadata limitation did
not expose a secret and did not contradict the canonical recovery inspector.

```text
SERVER_EXPORT_FOCUSED = 26 passed
SERVER_READONLY_SECURITY_REGRESSION = 776 passed, 7 skipped
DESKTOP_EXPORT_FOCUSED = 68 passed, 13 subtests
DESKTOP_FULL_REGRESSION = 1460 passed, 2 skipped, 3029 subtests; isolated Tcl rerun 1 passed
SECURITY_RUNTIME_SECRET_HITS = 0
SERVER_RAW_FULL_SUITE = KNOWN_BASELINE_STALE_SCHEMA_AND_MISSING_OPT_IN_POSTGRES_FAILURES_OUTSIDE_CHANGED_SCOPE
PUSHED = NO
```

No trading trigger, threshold, geometry, RR, risk, validity, cost policy,
production 5m minimum RR, Control state, LIVE mode, database schema or mobile
source was changed.

