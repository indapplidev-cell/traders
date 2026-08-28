# TRADERS_CLIENT_SCALPING_PAPER_PLAN_DETAIL_MATH_AND_EXACT10_SYMBOL_VIEW_REFACTOR_01 — FINAL EVIDENCE

```text
TASK_STATUS = BLOCKED
FINAL_VERDICT = BLOCKED_TRADERS_CLIENT_SCALPING_PAPER_PLAN_DETAIL_MATH_AND_EXACT10_SYMBOL_VIEW_REFACTOR_01_BY_COLLECTOR_CONTINUITY
BLOCKER_CODE = SCALPING_COLLECTOR_MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY
SECONDARY_BLOCKER = NONE
STOP_CONDITION = REQUIRED_COLLECTOR_REPAIR_IS_OUTSIDE_UI_TASK_AND_WOULD_REQUIRE_PROHIBITED_RUNTIME_INTERVENTION

SERVER_HEAD_BEFORE = 80b3dac486
SERVER_HEAD_AFTER_IMPLEMENTATION = 6ac8b53
DESKTOP_HEAD_BEFORE = 382522dc65
DESKTOP_HEAD_AFTER_IMPLEMENTATION = c965dd65b6386d1b562ae4911b5c42e300135341
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_HEAD_AFTER = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db

PRODUCTION_ALEMBIC_HEAD_BEFORE = 0018_promote_5m_production_search
PRODUCTION_ALEMBIC_HEAD_AFTER = 0018_promote_5m_production_search

SERVER_API_CHANGE = ADDITIVE_DETAIL_CANDIDATES_AND_EXPORT_TRADE_MATH
READONLY_GET_ROUTES_AFTER = 28
WRITE_ROUTES_ADDED = 0
READONLY_API_BACKWARD_COMPATIBLE = YES
DESKTOP_TRADING_MATH_RECOMPUTATION = NONE
RR_MARGIN_PRESENTATION_ONLY = YES_NET_RR_MINUS_REQUIRED_RR
READONLY_N_PLUS_ONE = NO_TWO_SET_BASED_CACHED_QUERIES
FUTURE_LEAKAGE = 0_CAUSAL_PERSISTED_PAYLOAD_ONLY

PAPER_PLAN_KEY_MATH_VISIBLE = YES
RR_REJECT_KEY_MATH_VISIBLE = YES
ENTRY_STOP_TARGET_VISIBLE = YES
STOP_TARGET_DISTANCE_VISIBLE = YES
GROSS_NET_REQUIRED_RR_VISIBLE = YES
MODELED_COST_BREAKDOWN_VISIBLE = YES
EXPECTED_NET_EDGE_VISIBLE = YES
RISK_QUANTITY_NOTIONAL_VISIBLE_WHEN_AUTHORITATIVE = YES
TTL_VALIDITY_VISIBLE = YES
PORTFOLIO_UNAVAILABLE_SEMANTICS_PRESERVED = YES
NULL_STATE_PRESENTATION_CONSISTENT = YES
TERMINAL_REASON_MACHINE_CODE_VISIBLE = YES
TERMINAL_REASON_HUMAN_LABEL_SERVER_AUTHORED = YES

EXACT10_UNIVERSE_SOURCE = SERVER_TRADING_UNIVERSE_RUNTIME_STATE
EXACT10_ALL_ROWS_VISIBLE_WITHOUT_INTERNAL_VERTICAL_SCROLL = YES
EXACT10_REFERENCE_VIEWPORT_SCROLL_REQUIRED = NO_FOR_SYMBOL_TABLE
REFERENCE_VIEWPORT = 1000x680
SYMBOL_TABLE_HEIGHT = 10
SYMBOL_SELECTION_PERSISTS_ACROSS_REFRESH = YES
RESPONSIVE_LAYOUT = PASS_REFERENCE_AND_GRACEFUL_PAGE_SCROLL_FALLBACK_ON_SMALLER_VIEWPORTS

BASIC_DETAIL_FIELDS = Entry,Stop,Target,Stop distance,Target distance,Gross RR,Net RR,Required RR,RR margin,Total cost,Expected edge,Risk percent,Quantity,Notional,TTL,Terminal reason,Machine code
ADVANCED_DETAIL_FIELDS = Identity,Strategy,Geometry,Target,Costs,RR-Economics,Risk-Sizing,Validity,Lifecycle
EXPORT_MATH_FIELDS = ADDITIVE_TRADE_MATH_COMPLETE
EXPORT_BACKWARD_COMPATIBLE = YES
RU_EN_KEY_PARITY = PASS
RU_EN_PLACEHOLDER_PARITY = PASS
DESKTOP_LOCAL_DOMAIN_TRANSLATION_MAPS_ADDED = 0

DESKTOP_REFRESH_MATERIAL_REGRESSION = NO_WARM_MEDIAN153MS_ON_10S_REFRESH
15M_UI_REGRESSION = PASS
15M_TRADING_BEHAVIOR_CHANGED = NO
TRADE_15M_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PRODUCTION_BEHAVIOR_CHANGED_BY_TASK = NO
SCALPING_PARAMETER_PROMOTION_BY_TASK = NO

NATURAL_PAPER_PLAN_DETAIL_VERIFIED = YES_SUIUSDT
NATURAL_RR_REJECT_DETAIL_VERIFIED = YES_BTCUSDT
EXACT10_VISIBILITY_VERIFIED = YES_10_OF_10
F5_SELECTION_PERSISTENCE_VERIFIED = YES
AUTO_REFRESH_SELECTION_PERSISTENCE_VERIFIED = YES

15M_RUNTIME_RESTARTS_BY_TASK = 0
SCALPING_RUNTIME_RESTARTS_BY_TASK = 0
COLLECTOR_RESTARTS_BY_TASK = 0
CONTROL_RESTARTS_BY_TASK = 0
POSTGRES_RESTARTS_BY_TASK = 0
READONLY_REPLACEMENTS_BY_TASK = 7

COLLECTOR_RUNNING_AFTER_TASK = NO_STABLE_RESTART_LOOP
COLLECTOR_RUNTIME_RESTART_COUNT_OBSERVED = AT_LEAST_207
COLLECTOR_ERROR = MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY
WAL_READY_AFTER = YES
PITR_READY_AFTER = YES
PHYSICAL_WAL_GAP_AFTER = NO
ACK_OWNER_HEALTH_AFTER = HEALTHY_HEARTBEAT_OWNER_IDENTITY_MATCH_BACKLOG0_PENDING0
CONTROL_STATE_AFTER = ARMED
CONTROL_GENERATION_AFTER = 6
LIVE_STATE_AFTER = DISABLED
BINANCE_ORDER_API_CALLS_BY_TASK = 0

SERVER_TESTS = FOCUSED_40_PASS;BROADER_201_PASS_12_SKIP_1_PREEXISTING_OUT_OF_SCOPE_RISK_FIXTURE_FAILURE
DESKTOP_TESTS = FULL_1480_PASS_2_SKIP_3029_SUBTESTS;FOCUSED_38_PASS
I18N_TESTS = PASS
15M_REGRESSION_TESTS = PASS_EXCEPT_PREEXISTING_UNCHANGED_RISK_FIXTURE_EXPECTATION
SECURITY_SCANNER = BANDIT_HIGH_SEVERITY_PASS
SECRET_SCANNER = TRACKED0_EVIDENCE0_TASK_LOG0_ACTIVE0
SECRET_OUTPUT = 0
SECURITY_FINDINGS = 0

SERVER_COMMITS = 96be866,fad2d4f,1eaa958,ed74563,817e64e,6ac8b53
DESKTOP_COMMITS = c965dd65b6386d1b562ae4911b5c42e300135341
MOBILE_COMMITS = NONE
PUSHED = NO

NEXT_ACTION = DIAGNOSE_AND_RESTORE_SCALPING_COLLECTOR_LINEAGE_WITHOUT_CHANGING_TRADING_ALGORITHM_THEN_RERUN_FINAL_ACCEPTANCE
```

## Authoritative field mapping

| Persisted source | Readonly field | Desktop field | Unit / null |
|---|---|---|---|
| paper shadow plan / geometry diagnostic | entry_price, stop_price, target_price | Entry, Stop, Target | raw Decimal precision; Unavailable if absent |
| causal geometry diagnostic | stop/target distance absolute, percent, bps; ATR/buffer | Geometry / Target | absolute, %, bps; no current quote |
| boundary economic diagnostic | spread, depth, fees, slippage, safety, total cost | Costs | bps; computed zero remains 0 |
| paper economic decision | gross_rr, net_rr, required_rr, expected_net_edge_bps, break_even_win_rate | RR-Economics | RR/bps/%; undefined client margin is em dash |
| persisted risk/quantity approvals | risk_percent, risk_amount, paper_equity_basis, quantity constraints, planned_quantity/notional | Risk-Sizing | authoritative only; otherwise Unavailable/N/A by stage |
| approval validity payload | created/valid-from/valid-until/TTL/expiry/source boundary | Validity | UTC/ms; expired is explicit |
| persisted stage/reason/checklist | stage statuses, terminal/machine reasons, plan/order/fill/position | Identity/Lifecycle | Plan never implies order/fill/position |
| no serialized portfolio decision | portfolio=null | Portfolio | Unavailable |

## Natural production examples

SUIUSDT authoritative PAPER Plan:
- source run `orchestrator:21b5a0108c164f7fb284bb24ccdd9da0`
- Entry 0.7639; Stop 0.761690625; Target 0.7734
- stop 0.002209375 / 0.2892230658% / 28.92230658 bps
- target 0.0095 / 1.2436182746% / 124.36182746 bps
- Gross RR 4.29985856; Net RR 1.67828718; Required RR 1.5
- spread 1.3098434737; depth 0; fee 20; slippage 4; total 28.30984347 bps
- expected edge 96.05198399 bps; risk 1%; quantity 130.90000000; notional 99.994510000000; TTL 300000 ms
- final approval PASS; now expiry EXPIRED; order/fill UNAVAILABLE; position NOT_OPENED.

BTCUSDT authoritative RR reject:
- source run `orchestrator:e26a5a7ad4be4165b1e081e9e66ecf10`
- reason `PAPER_REJECT_LOW_NET_RR`
- Entry 77530; Stop 77829.3903125; Target 76888
- Gross RR 2.14435796; Net RR 0.85046661; Required RR 1.5
- total modeled cost 27.00129036 bps; expected edge 55.80536513 bps
- risk/quantity/notional/TTL are correctly not reached, not fabricated.

## Exact10 / performance / runtime evidence

The 1000x680 natural GUI check rendered the server-provided exact10 universe with table height 10, ten non-empty visible row bounding boxes, no internal vertical scrollbar, and SUI selection unchanged across repeated render/refresh. F5 and automatic refresh share that render path. A smaller window may use the existing outer page-scroll fallback.

Final deployed Readonly image: `sha256:78d53e63c990afca66fcb8be5e0a5eee45a3c7eb2b1d7d24e8fc12f0e50c8060`; healthy, restart count 0. Final response: 121382 bytes; warm min/median/max 114/153/207 ms. This is immaterial relative to the 10-second refresh interval and adds no per-symbol HTTP or SQL calls.

Protected 15m, 5m, Control and Postgres container identities remained unchanged with restart count 0. WAL/PITR and ACK owner are healthy and LIVE remains disabled. The calibration collector kept the same container identity but independently entered a fail-closed restart loop with `MIXED_RUNTIME_LINEAGE_WITHIN_BOUNDARY`. The task did not restart or modify it; remediation would violate this task's explicit scope, so the required overall PASS is blocked.

