# TRADERS PAPER execution UI sync and refresh latency fix 01

## Scope and verdict

This audit covers the production read-only PAPER projection, the continuous PAPER
execution bridge, and the Windows desktop Funnel -> PAPER refresh path. LIVE
remained disabled and no signal, approval, command, fill, or market input was
created for validation.

`FINAL_VERDICT = PASS_IMPLEMENTATION_DEPLOYMENT_AND_NATURAL_SERVER_CHAIN_WITH_USER_TERMINATED_SECOND_DESKTOP_OPEN_WATCH`

On 2026-09-05 the user explicitly cancelled the five-minute watcher and directed
final evidence, commits, push, reconciliation, and verification to complete. This
is a scope/terminal-condition amendment, not permission to relabel an unobserved
timestamp as PASS. The natural server/read-only chain is PASS; a second natural
OPEN rendered by the restarted Desktop is recorded as `NOT_OBSERVED_IN_OPEN_WINDOW`.

## Proven root causes

1. The desktop selected an active position only from the historical first-canary
   identity. Continuous runtime could therefore truthfully report `POSITION_OPEN`
   while the client left `active_position = None` and rendered `count = 0`.
2. The PAPER repaint was assembled from independent asynchronous reporting and
   control lanes without a runtime identity fence. A lifecycle from generation N
   could be combined with position/account/history data fetched around a different
   execution.
3. Refresh completion had no measured watchdog. A callback/provider failure could
   leave the page scope busy and suppress every later 10-second refresh.
4. Page activation refreshed only an IDLE page; a stale successful PAPER snapshot
   waited for the next timer instead of refreshing immediately.
5. The server Funnel and runtime projections hid terminal continuous execution
   failures behind `PENDING`, `NOT_REACHED`, or the legacy selector fallback.
6. The last pre-fix SUI command was admitted after its deterministic next-closed-1m
   entry window. Its order update timestamp was later than the required fill close,
   so opening it would violate causal ordering. The executor now rejects this exact
   case as `CONTINUOUS_ENTRY_FILL_WINDOW_MISSED` and releases the lane fail-safely.

## Fix

- Runtime is fetched before and after the complete PAPER reporting read. The exact
  profile/boundary/candidate/approval/plan/command/position identity must remain
  equal; mixed generations fail as `PAPER_SNAPSHOT_CHANGED`.
- A continuous `OPEN`/`CLOSING` runtime position ID has priority over historical
  canary identity. Its exact position is fetched and both command and position IDs
  are validated before a new immutable view model is published.
- The snapshot ID hashes the full reporting material and the control generation.
  State is swapped on the Tk thread; unchanged hashes finish as `UNCHANGED` and do
  not repaint PAPER.
- Reporting failure preserves last-good account, history, and reconciliation.
  Error provider, machine reason, elapsed milliseconds, UTC timestamp, and
  recoverability are recorded.
- PAPER refresh is single-flight. The watchdog is 30 seconds, selected from the
  measured production maximum of 16.365 seconds plus boundary/contention margin.
  Timeout releases the page scope, preserves the last-good snapshot, publishes
  `TIMED_OUT`, and permits exactly one subsequent auto refresh.
- A stale Funnel -> PAPER page switch requests an immediate refresh. Network and DB
  work remains in the bounded worker pool; the Tk thread only swaps and renders.
- New Continuous selector states never use `LEGACY_NOT_OBSERVED`; unreached stages
  are `NOT_REACHED`, while an elapsed unselected record is `EXPIRED`.
- Funnel separates plan success from execution state/reason and exposes the exact
  execution candidate identity. Runtime and Funnel expose failed-safe terminal
  state and the exact machine reason.

## Provider and snapshot inventory

| Screen part | Endpoint/provider | Generation / snapshot | Cache | Trigger | Client state |
|---|---|---|---|---|---|
| PAPER header/lifecycle | `GET /api/v1/paper/runtime/status` | identity fence, snapshot hash | none | page/F5/10s | `PaperPageState.runtime_status` |
| readiness | `GET /api/v1/paper/readiness` | `paper_control_generation` | none | coherent reporting read | `PaperPageState.readiness` |
| criteria | `GET /api/v1/paper/trading-criteria` | snapshot hash | none | coherent reporting read | `PaperPageState.trading_criteria` |
| account | `GET /api/v1/paper/account` | snapshot hash, last-good | none | coherent reporting read | `PaperPageState.account` |
| active/list positions | `GET /api/v1/paper/positions`, exact `GET /positions/{id}` | exact runtime IDs | none | coherent reporting read | `active_position`, `paper_positions` |
| history | `GET /api/v1/paper/trades` | snapshot hash, last-good | none | coherent reporting read | `trade_history` |
| reconciliation | `GET /api/v1/paper/reconciliation` | snapshot hash, last-good | none | coherent reporting read | `reconciliation` |
| report | `GET /api/v1/paper/trades/{id}/report` | exact position ID | none | coherent reporting read | `selected_trade_report` |
| reporting control | `GET /api/v1/paper/control/status` | control generation | none | coherent reporting read | `reporting_control_status` |
| operator control | localhost `8766`, read-only status lane in this task | control generation | none | parallel bounded worker | `control_status` |

The coherent PAPER operation is deliberately a sequence of bounded read-only calls,
not a parallel mixture: runtime-before -> readiness/criteria/account/positions/
history/reconciliation -> runtime-after -> identity validation -> immutable model ->
one Tk-thread swap.

## Production latency

Twenty complete production PAPER provider cycles and twenty production Funnel
calls were measured:

| Provider | median | p95 | max |
|---|---:|---:|---:|
| coherent PAPER | 15026.0 ms | 15807.9 ms | 16365.2 ms |
| Funnel `trade-5m-v2` | 226.0 ms | 302.0 ms | 2091.6 ms |

With a 10-second auto-refresh interval and the measured 16.365-second provider
maximum, the acceptance allowance is 26.365 seconds plus the measured Tk render
time. The production harness measured a 14.5 ms receive-to-render interval and a
15 ms PAPER render.

## Production causal correction evidence

The last pre-fix selected SUI record had boundary `1788584400000`, command/order
creation `2026-09-05T05:01:13.948Z`, and deterministic fill close
`2026-09-05T05:01:00Z`. The server position was never open. Post-deploy runtime and
Funnel both report `EXECUTION_FAILED`, `FAILED`, `NOT_REACHED`, and
`CONTINUOUS_ENTRY_FILL_WINDOW_MISSED`; no false `OPEN` remains.

## Natural production evidence

First post-deploy natural chain (no forced input):

- symbol `BNBUSDT`, profile `trade-5m-v2`, boundary `1788594300000`;
- candidate `paper:production-approval-candidate:v1:de26d0857f677cf5b16f21f347d29bbb1ecf9c72bfcbccf535c47855b8790433`;
- approval `paper:risk-approval:v1:3aa5037f43769252980b460ee6f216144d1f89028e43985a862c6674487ba7da`;
- plan `paper:BNBUSDT:5m:1788594300000:risk:BNBUSDT:5m:1788594300000:strategy:v2:f75fc6bd3cf51771f8f1e27988294297ae39361f35801db999a90ab16ffb37bf:5a27bd935a8f76cf:ba1d5920bdc12b01`;
- command `paper:ingestion-command:v1:b5968f24a8bb8db4b552acc9d9b4b1d1d5307fda9f0e42c0956722146c731d30`;
- position `paper:continuous:position:1c2eee48e5457cf4d7f27625598143d70db0a75f83974c71f551ff0ad80c366c`;
- selected `2026-09-05T07:45:37.394Z`, command created
  `2026-09-05T07:45:34.341Z`, entry fill/position opened
  `2026-09-05T07:46:00Z`;
- read-only OPEN observed `2026-09-05T07:46:23.034Z`, 23034 ms after the
  authoritative position timestamp and within the measured next-refresh allowance;
- exit triggered/position CLOSING `2026-09-05T08:17:00Z`; exit fill/position CLOSED
  `2026-09-05T08:18:00Z`; command `COMPLETED`; net PnL `+0.715450916 USDT`.

The Desktop was intentionally stopped for full GUI regression during this first
OPEN interval, so it is not used to invent a client-render timestamp. A later
natural SUI chain also completed before the restarted Desktop watcher began. The
user then explicitly stopped the second natural watcher. Accordingly:

- `NATURAL_PRODUCTION_SERVER_READONLY_VALIDATION = PASS`
- `POSITION_OPEN_VISIBLE_WITHIN_NEXT_HEALTHY_READONLY_REFRESH = PASS_23034_MS`
- `NATURAL_PRODUCTION_DESKTOP_OPEN_REOBSERVATION = NOT_OBSERVED_IN_OPEN_WINDOW_USER_TERMINATED_WATCH`
- `PAPER_CLIENT_RENDERED_AT_FOR_NATURAL_OPEN = NOT_OBSERVED_IN_OPEN_WINDOW`

The actual production Desktop Funnel -> PAPER harness separately passed immediate
page refresh, coherent receive/render telemetry, account/history/reconciliation,
and responsive repaint. Its tested state was the exact terminal SUI fail-safe, not
an OPEN position. OPEN/count=1 and exact identity are proven by the isolated
PostgreSQL end-to-end client chain and focused GUI tests, but are not substituted
for the missing second natural Desktop timestamp.

## Tests and safety evidence

- Server focused production/read-model suite: `1941 passed`.
- Earlier expanded relevant server suite: `1887 passed, 2 skipped`; later non-DB
  relevant run: `862 passed, 8 skipped` (remaining collection errors required an
  explicit PostgreSQL test URL).
- Isolated PostgreSQL 16 on loopback `127.0.0.1:55439`, non-superuser test role and
  test-only database: `826 passed` repository/worker tests and `8 passed` natural
  chain scenarios, including OPEN -> CLOSED, active count 1 -> 0, history +1, and
  Continuous control retention. Production DB was read only for this audit.
- Desktop focused sync/refresh suite: `29 passed`. Full suite before the final
  telemetry-only extension: `1496 passed, 2 skipped, 3029 subtests`. The final full
  rerun produced the same 1496 passes plus one host Tk file-discovery flake; the
  isolated affected GUI test and all changed focused tests pass.
- trade-15m-v1 regression: `10 passed`; container ID/image/start time/restart count
  remained unchanged and no 15m source/config path is in the diff.
- Readonly container is healthy, restart count 0, source
  `764e8834d628c1499d4a563e88650131bf8ed3d7`. Operator control is healthy, restart
  count 0, source `3c4a7c68108959321b51a7a2d184dbf36a7549ba` (later commits do not change its
  build context). Alembic is the single head `0025_paper_budget_policy`.
- Fresh final runtime observation at `2026-09-05T12:23:54Z` showed another natural
  SUI execution `COMPLETED/CLOSED`, zero active positions, 23 closed trades, account
  balance `95.069540094 USDT`, and healthy paper/accounting reconciliation.
- `LIVE = false`, real Binance order API calls `0`, no production secrets emitted,
  no production mutation was used to create validation traffic.

## Commits

Server/read-model implementation commits:

- `5bdbf57b9edfdaa613693a9a2a92f5beb6a4b839`
- `269835711c9c75e936d79fefb062bdf700698c5a`
- `3c4a7c68108959321b51a7a2d184dbf36a7549ba`
- `6d6040ee617ed8d8b593e88650131bf8ed3d7`
- `764e8834d628c1499d4a563e88650131bf8ed3d7`

Desktop implementation commits (the client repository has no configured remote):

- `786fd8a464535bac8d527dbef6116f933fbb9826`
- `e1c983ea999781628fca39e65b1027c951047a9d`
- `a03ece5dcea42090f9ad5ab90149738f887d702d`
- `0e148d9a6005b45aa36bc3cc12865657f3f7006a`
