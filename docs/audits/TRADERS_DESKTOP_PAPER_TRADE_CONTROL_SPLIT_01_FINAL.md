# TRADERS Desktop Paper / Trade Control split 01 — final evidence

```text
TASK = TRADERS_DESKTOP_PAPER_TRADE_CONTROL_SPLIT_01
FINAL_STATUS = PASS
FINAL_VERDICT = PAPER_INFORMATION_PROJECTION_AND_TRADE_CONTROL_ARE_SEPARATE_LAZY_LIFECYCLE_SCOPES_AND_THE_DEPLOYED_READONLY_CATALOG_IS_INTEGRATED
SERVER_IMPLEMENTATION_COMMIT = 44f97d3b2e45f677744ab5feceed602e4cf684be
CLIENT_IMPLEMENTATION_COMMIT = e502ca5
CLIENT_TEST_COMMIT = 9a646a4
MODE = PAPER
LIVE_STATE = DISABLED; live_allowed=false
REAL_BINANCE_ORDER_CALLS = 0
STRATEGY_CHANGED = NO
TRADING_THRESHOLDS_CHANGED = NO
RISK_CHANGED = NO
SELECTOR_CHANGED = NO
YAML_CHANGED = NO
UNIVERSE_CHANGED = NO
LEGACY_15M_CHANGED = NO
```

## Delivered integration

- Navigation order is `PAPER Trading -> Trade Control -> Settings`; RU/EN labels
  and keyboard shortcuts are server-catalog owned.
- `PAPER Trading` owns only `Paper calculation`, bounded trade history, active
  position, reconciliation, and an on-demand trade report.
- Criteria, readiness, reporting-control state, operator-control state, canary
  state, and every control action belong to the lazily constructed `Trade
  Control` page.
- Leaving a page cancels its request scope. Request keys are page-specific, the
  canary sequence gate rejects stale control snapshots, and lazy construction
  prevents duplicate widgets and background polling before first entry.
- Paper history is requested with `limit=20`; reconciliation/history use the
  slow 60-second projection path; the active position is fetched by the exact
  runtime identity; reports are fetched only after a closed-trade selection.
- A failure in the reporting scope does not invalidate the control scope and a
  control failure does not replace the Paper information projection.

## Performance proof

The pre-change client did not persist a comparable end-to-end timing or byte
trace, so those cells are intentionally `NOT_MEASURED`. Static call counts are
from the parent source at `f9e0c6b`; after counts are from the tested source at
`9a646a4`.

| Measure | Before | After | Evidence |
|---|---:|---:|---|
| Paper refresh base Paper/control calls | 11 | 6 first/slow, 4 fast | before: 9 reporting + 2 control; after: runtime x2, account, positions, plus history/reconciliation only on slow path |
| Optional active-position call | 0/1 | 0/1 | exact active runtime identity only |
| Automatic trade-report call | 0/1 | 0 | report is selection-driven |
| History page size | 50 | 20 | bounded latest projection |
| Reconciliation frequency | every refresh | first refresh and at most once per 60 seconds | controller policy and deterministic tests |
| Calls from Paper to Trade Control endpoints | 2 base control calls plus reporting-control projection | 0 | `PAPER_TRADING_CALLS_TRADE_CONTROL_ENDPOINT=NO` test invariant |
| Before aggregate bytes/time | NOT_MEASURED | n/a | no pre-change request telemetry; no reconstructed numbers |
| After first/slow Paper API bytes | n/a | 33,324 bytes without active detail | six HTTP 200 responses, including two runtime identity reads |
| After first/slow sequential endpoint time | n/a | 21,491.47 ms | local production Readonly, dominated by two runtime status reads; not presented as a client parallel wall time |
| Client parse/render time | NOT_MEASURED | NOT_MEASURED | no production-grade per-widget profiler was introduced; call removal and endpoint ownership are the acceptance criterion |

Measured endpoint sample on `2026-09-20T21:22Z`:

| Endpoint | HTTP | Bytes | ms |
|---|---:|---:|---:|
| `/api/v1/paper/runtime/status` | 200 | 2,436 | 10,869.26 |
| `/api/v1/paper/account` | 200 | 5,115 | 392.17 |
| `/api/v1/paper/positions?limit=20` | 200 | 10,463 | 25.31 |
| `/api/v1/paper/trades?limit=20` | 200 | 12,547 | 136.75 |
| `/api/v1/paper/reconciliation` | 200 | 327 | 112.04 |
| second `/api/v1/paper/runtime/status` | 200 | 2,436 | 9,955.94 |

## Validation

```text
CLIENT_FOCUSED = 77 passed; 18 deselected; 28 subtests passed
CLIENT_RELEVANT = 101 passed; 2 skipped; 18 deselected; 1648 subtests passed
CLIENT_GUI_SPLIT = TradeControlLifecycle 2 passed; criteria GUI 1 passed
CLIENT_FULL_DISCLOSURE = 145 passed; 2 skipped before intermittent local Tcl init/install race; all affected GUI tests pass in isolated reruns
SERVER_RELEVANT = 47 passed; 2 deselected
SERVER_KNOWN_UNRELATED = stale public-enum expectation missing NET_PNL_PROTECTION; stale route count 28 versus 29
COMPILE = server PASS; client PASS
```

Deterministic coverage proves the five-block Paper composition, lazy single
construction of Trade Control, strict navigation adjacency, request ownership,
leave-page cancellation, stale sequence rejection, bounded history, slow
reconciliation, on-demand report loading, and independent failure domains.

## Deployment and Desktop acceptance

Only the Readonly API was rebuilt and force-recreated. The healthy container
`traders-readonly-api-readonly-api-1` has immutable image revision
`44f97d3b2e45f677744ab5feceed602e4cf684be`. The deployed catalog version is
`i18n-b2b08df419169a86`; `/api/v1/i18n/catalog/ru` contains
`trade_control.title = Контроль сделки`. Other production services were not
rebuilt or restarted.

Desktop acceptance used the mandatory PID/HWND preflight and
`FULL_DESKTOP_CROPPED_BY_HWND`. UIA/CUA native discovery was unavailable and is
non-blocking under `TRADERS_TK_WIN32_FALLBACK_V1`; pages were selected inside
isolated read-only source-tree acceptance processes and no mutation control was
invoked.

```text
PAPER = PASS; PID 5904; HWND 859564
PAPER_CAPTURE = C:\Users\ZENOL\AppData\Local\Temp\traders-desktop-acceptance\traders-hwnd-d1dac-20260920T211816Z.bmp
PAPER_SHA256 = 53066936ED482FA29AFC989B0BAA06D9559ADFC292CD89776C669926C11960BB
PAPER_VISIBLE_BLOCKS = Paper расчет; История сделок; Активная позиция; Сверка; Отчет по сделке
PAPER_CRITERIA_VISIBLE = NO
PAPER_CONTROL_VISIBLE = NO
TRADE_CONTROL = PASS; PID 2232; HWND 334870
TRADE_CONTROL_CAPTURE = C:\Users\ZENOL\AppData\Local\Temp\traders-desktop-acceptance\traders-hwnd-51c16-20260920T211920Z.bmp
TRADE_CONTROL_SHA256 = E8DA3791A9FC5DE433AB16B87B8856F45E34F305B8092AB7B9E8FE83BF966421
TRADE_CONTROL_CRITERIA_VISIBLE = YES
TRADE_CONTROL_PAPER_CONTROL_VISIBLE = YES; initial unloaded frame captured separately before data expansion
NAVIGATION = PASS; PAPER immediately followed by Trade Control immediately followed by Settings
SAFETY = READ_ONLY_NAVIGATION; LIVE DISABLED; no Disable/Emergency Stop/LIVE/settings/strategy/risk/selector actions
```

## Post-task state

The new display policy is integrated into the client runtime and server-owned
catalog; it is not a widget-only refactor. Existing Paper execution logic,
control API contracts, trading policy, profile, universe, risk limits, selector,
YAML authority, and legacy 15m shutdown remain unchanged.

```text
CURRENT_STAGE = NORMAL_CONTINUOUS_PAPER_OPERATION_WITH_SPLIT_INFORMATION_AND_CONTROL_PROJECTIONS
CURRENT_BLOCKER = NONE_FOR_DESKTOP_SPLIT; LIVE_REMAINS_DISABLED_BY_POLICY
NEXT_ACTION = CONTINUE_NORMAL_PAPER_OBSERVATION_WITHOUT_TRADING_POLICY_CHANGES
```
