# TRADERS — полный аудит server Scalping v2 и evidence-first cleanup

REPORT_STATUS = FINAL
GENERATED_AT_UTC = 2026-10-31T15:25:00Z
WORKSPACE = D:\disk_E\game_projects\traders
SERVER_REPO = D:\disk_E\game_projects\traders\traders-ml
LOCAL_HEAD = 3487534fe7ba7adddef0602f3c982f14981c2b00
BRANCH = feature/engine-platform
UPSTREAM = origin/feature/engine-platform
AHEAD = 0
BEHIND = 0

ACTIVE_PROFILE = trade-5m-v2
ACTIVE_PARAMETER_SET = scalping-v2-set-2
ACTIVE_UNIVERSE = trading-universe-v3 / 20 symbols
MODE = PAPER
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
TRADING_LOGIC_CHANGED = NO
PARAMETERS_CHANGED = NO
PRODUCTION_DB_MUTATED = NO
PRODUCTION_MIGRATIONS_APPLIED = NO
PRODUCTION_SERVICES_RESTARTED_BY_AUDIT = NO
PRODUCTION_DEPLOY_PERFORMED = NO

## Evidence labels

- [RUNTIME_PROVEN] — current container, read-only PostgreSQL, health payload or persisted runtime fact observed on 2026-10-31.
- [STATIC_PROVEN] — current HEAD source/config/import/call path.
- [TEST_PROVEN] — isolated current-source test.
- [HISTORICAL_ONLY] — persisted or documented observation from an earlier bounded window.
- [INFERRED] — supported inference without direct measurement.
- [UNPROVEN] — evidence is unavailable or insufficient.

## EVIDENCE_INDEX

| ID | Status | Evidence | Result |
|---|---|---|---|
| E01 | [STATIC_PROVEN] | Git HEAD/status/branch/remotes | HEAD 3487534, clean upstream relation; 92 deleted, 1 modified and 2 untracked pre-existing user changes |
| E02 | [RUNTIME_PROVEN] | Docker inspect | orchestrator source 9fb4eef; readonly a429fe0; operator c5e8db6; restarts 0 |
| E03 | [RUNTIME_PROVEN] | production_control paper state/health | CONTINUOUS_ARMED, PAPER, live_allowed=false, max open/new=2/2 |
| E04 | [RUNTIME_PROVEN] | PostgreSQL transaction_read_only | read-only transaction confirmed; Alembic 0037_continuous_two_lifecycle_slots |
| E05 | [RUNTIME_PROVEN] | trading_universe_runtime_state | trading-universe-v3, generation 3, 20-symbol activation |
| E06 | [RUNTIME_PROVEN] | commission status | READY, 20 symbols, refresh failure count 0 |
| E07 | [STATIC_PROVEN] | runtime parameter resolver | Set #2 hash 1105f809..., stop 36 bps, target 40 bps, RR 0.476674, risk 5 bps |
| E08 | [TEST_PROVEN] | focused v2 profile suite | 12 passed |
| E09 | [TEST_PROVEN] | broad static-focused selection | 162 passed, 53 failed, 5 skipped; failures classified below |
| E10 | [RUNTIME_PROVEN] | latest complete 20-symbol DB boundaries | 2026-10-31 15:00, 15:05, 15:10, 15:15 and 15:20 UTC all completed 20/20; uninterrupted 4h/12h/24h not yet available after downtime |
| E11 | [RUNTIME_PROVEN] | 24h persisted cohort ending E10 | 1679 runs, 1632 analyzed, 125 setup/strategy/risk pass, 22 plan ready |
| E12 | [RUNTIME_PROVEN] | natural PAPER history | 193 closed, 47 wins, 146 losses, PF 0.3059, net -17.10577658 USDT |
| E13 | [RUNTIME_PROVEN] | cleanup inventory and exact manifest execution | 1,949 unique generated files / 40,063,426 bytes targeted outside .venv; 14 files / 276,335 bytes regenerated and retained; reports 80.8 GB retained |
| E14 | [HISTORICAL_ONLY] | prior 4h/12h/24h forensic report | detailed 2026-10-09 cohort and pure replay; not promoted to current runtime truth |

# 1. Executive technical verdict

[STATIC_PROVEN] The active Scalping v2 path is connected end to end from closed Binance-derived candles through analysis, setup, strategy, risk, geometry/economics, PAPER planning, selector, simulated execution, position, exit and persistence.

[RUNTIME_PROVEN] The current safety state is PAPER with LIVE disabled. No audit action changed runtime, DB, migrations or configuration.

[RUNTIME_PROVEN] After the multi-day Docker interruption, five consecutive current boundaries from 2026-10-31 15:00 through 15:20 UTC completed for all 20 symbols. The bounded 4h/12h/24h analysis still ends at the last pre-outage complete boundary, 2026-10-27 17:50 UTC, and is persisted historical evidence rather than a wall-clock-fresh continuous window.

[RUNTIME_PROVEN] In that cohort, commission authority is no longer the blocking stage seen in the older October 9 report. The dominant downstream rejection is causal stop width: 87 of 103 PAPER-stage rejections. Ten projected plans reached the selector; every selected plan missed its entry-fill window because plan creation was already more than 30 seconds after the candle boundary.

[STATIC_PROVEN] Seven setup families are configured, but runtime output is concentrated in SCALP_MOMENTUM_CONTINUATION. The family diagnostic contract also exposes a recognized breakout-retest producer/consumer mismatch when it occurs.

FINAL_TECHNICAL_VERDICT = PASS_STATIC_ARCHITECTURE; CURRENT_20_SYMBOL_PROCESSING_RECOVERED; FRESH_24H_CONTINUITY_UNPROVEN; FAIL_TRADING_OUTCOME_AND_DEADLINE_ACCEPTANCE
CLEANUP_STATUS = DONE_PROVEN_SAFE_GENERATED_ARTIFACTS; ACTIVE_REGENERATED_CACHES_REVIEW_REQUIRED

# 2. Repository/root inventory

| Name | Git | Purpose | Snapshot size | Action |
|---|---:|---|---:|---|
| traders-ml | yes | active server/runtime | 82,482,453,231 bytes | functional audit + safe cleanup |
| traders-client | yes | desktop client | 11,194,011 bytes | top-level inventory only |
| traders-mobile | yes | mobile client | 27,602,348 bytes | top-level inventory only |
| traders_ml_recovery | no | PostgreSQL backup/WAL/PITR | 138,158,607,252 bytes | KEEP; no cleanup |

# 3. Active server identification

[STATIC_PROVEN] traders-ml owns Docker Compose, PostgreSQL, market-data sync, orchestrator, PAPER operator, readonly API, Alembic and the Python packages imported by all active processes.

[STATIC_PROVEN] Client repositories are not imported by the server runtime and were not inspected below their top level.

# 4. Active Scalping profile/config/universe

| Item | Effective value | Authority | Status |
|---|---|---|---|
| Profile | trade-5m-v2 / PRODUCTION_SEARCH | runtime_policy + resolver | [STATIC_PROVEN] |
| Parameter set | scalping-v2-set-2-v1 | trade_parameters.yaml | [STATIC_PROVEN] |
| Universe | trading-universe-v3 / 20 symbols | DB runtime state + PAPER state | [RUNTIME_PROVEN] |
| Compose seed | 10 symbols | compose/runtime policy | [STATIC_PROVEN] seed only |
| Entry timeframes | 1m, 5m | resolver | [STATIC_PROVEN] |
| Context timeframes | 15m, 1h | resolver | [STATIC_PROVEN] |
| Required windows | 60/120/64/50 | resolver | [STATIC_PROVEN] |
| Mode | PAPER / CONTINUOUS_ARMED | production control | [RUNTIME_PROVEN] |
| LIVE | disabled | health + state | [RUNTIME_PROVEN] |

The apparent 10-vs-20 mismatch is intentional layering: Compose supplies startup seed symbols while trading_universe_runtime_state and production-control scope hold the activated 20-symbol universe. Historical complete cycles contain all 20 symbols.

# 5. Runtime services map

| Service | Entrypoint | Revision | Dependencies | State |
|---|---|---|---|---|
| postgres | postgres 16 | schema 0037 | recovery volume | healthy |
| market-data-sync | engine_market_data_continuous_sync.py | image label UNSET | Binance REST/WS, PostgreSQL | running; provenance defect |
| online-orchestrator-5m | engine_orchestrator_online_pipeline.py | 9fb4eef | DB, market data, commission | running |
| scalping collector | scalping_prospective_collector.py | d93d3a5 | DB | running |
| readonly API | traders-readonly-api | a429fe0 | DB, projections | healthy |
| operator-control | traders-operator-control-api | c5e8db6 | DB, control state | healthy |

~~~mermaid
flowchart LR
  B[Binance public/account data] --> M[market-data-sync]
  M --> PG[(PostgreSQL)]
  PG --> O[5m orchestrator]
  O --> PG
  PG --> R[readonly API]
  PG --> P[PAPER operator/lifecycle]
  P --> PG
  O --> C[calibration collector]
~~~

# 6. Full A→Z call graph

[STATIC_PROVEN]

~~~mermaid
flowchart TD
  A[closed candles] --> B[PipelineRunner]
  B --> C[analysis OnlineRunner]
  C --> N[Nison]
  C --> AT[Altunina]
  C --> S[Schwager]
  N --> M[BookEvidenceMatrix]
  AT --> M
  S --> M
  M --> RC[RegimeComposer]
  RC --> I[Impulse/micro context]
  I --> SD[SetupDetector]
  SD --> ST[StrategyRunner]
  ST --> RK[RiskPolicy]
  RK --> G[scalping_shadow geometry]
  G --> E[cost/RR/EV]
  E --> FA[final approval]
  FA --> PP[PAPER plan]
  PP --> SEL[selector]
  SEL --> CMD[command/order/fill]
  CMD --> POS[position]
  POS --> EX[exit evaluator]
  EX --> CL[close/PnL/persistence]
~~~

# 7. Runtime sequence diagram

~~~mermaid
sequenceDiagram
  participant MD as Market data
  participant DB as PostgreSQL
  participant OR as Orchestrator
  participant OP as PAPER operator
  participant EX as Lifecycle/exit
  MD->>DB: persist closed OHLCV
  OR->>DB: claim profile/symbol/boundary
  OR->>DB: load causal multi-TF snapshot
  OR->>OR: analysis → setup → strategy → risk
  OR->>OR: geometry → costs → RR/EV → approval
  OR->>DB: persist run/result/PAPER plan
  OP->>DB: select bounded winners
  OP->>DB: create command/order/fill/position
  EX->>DB: evaluate closed 1m boundary
  EX->>DB: exit decision/fill/close/PnL
~~~

The compute path is per-symbol; authoritative writes are serialized through owned sessions. Network calls occur in market-data and cost sources, not in the pure analysis functions. Advisory ownership, idempotency and DB constraints protect duplication.

# 8. Market data ingestion

[STATIC_PROVEN] Binance kline mapping normalizes symbols, millisecond timestamps and OHLCV into timeframe-specific tables. Continuous sync uses warmup, boundary scheduling, gap detection/recovery, retries and freshness reports.

| Timeframe | Store | Active consumer | Window |
|---|---|---|---:|
| 1m | candles_1m | refinement and exit | 60 |
| 5m | candles_5m | primary analysis/setup | 120 |
| 15m | candles_15m | context | 64 |
| 1h | candles_1h | context | 50 |
| 4h/1d | dedicated tables | sync/recovery/adjacent profiles | not active decision windows |

Duplicates are checked by symbol/open-time identity; conflicting duplicates fail explicitly. Gap recovery fetches bounded missing ranges. Freshness gates fail closed or retry until deadline.

# 9. Candle causal integrity

[STATIC_PROVEN] SetupDetector rejects future_bars_used. Snapshot builders cap rows at decision boundary. Higher-timeframe bars are unavailable until their close. Exit logic consumes closed 1m candles.

[TEST_PROVEN] engine_analysis causal tests cover deterministic closed input, future-close rejection and higher-timeframe close alignment.

[UNPROVEN] A fresh independent replay of every current 2026-10-31 boundary was not performed because the runtime had just resumed after downtime.

# 10. Nison analysis

[STATIC_PROVEN] Nison consumes normalized closed 5m morphology and catalogued single/pair/triple/multi-candle relations. Effective morphology thresholds are body/range 0.10, 0.25, 0.30, 0.60, 0.70; extended shadow 0.55; shadow/body 2.0; opposite shadow/range 0.10; hammer body position 0.60; star position 0.40.

Trend-context and follow-through warnings are evidence qualifiers, not automatic directional confirmation. Evidence is signed and later normalized by the matrix.

# 11. Altunina analysis

[STATIC_PROVEN] Pivot/swing structure uses tolerance 0.001, Fibonacci pullbacks 0.38/0.50/0.62 and correction limit 0.62. Confirmed direction requires coherent swing highs and lows; insufficient pivots and TREND_NOT_CONFIRMED remain explicit non-directional evidence.

# 12. Schwager analysis

[STATIC_PROVEN] Zone tolerance 0.003; minimum zone touches 2; range touches 4; inside-close ratio 0.60; range width 0.003–0.20; duration 4; alternations 2. Breakout buffer 0.001, confirmation closes 3, distance 0.005; follow-through/retest/false-break lookaheads 2/5/3.

# 13. Evidence Matrix

[STATIC_PROVEN] BookEvidenceMatrix converts Nison, Altunina and Schwager evidence into bullish, bearish and flat buckets, coverage, confluence and conflict. Material directional magnitude is 0.05 and balance tolerance 0.03. Presence of a source increases coverage but does not imply direction.

# 14. Regime Composer

[STATIC_PROVEN] UP/DOWN/FLAT candidates are scored and clamped 0..1. The minimum winning score is 0.30 and minimum margin 0.08. Invalid OHLC, partial analysis, low coverage, unresolved opposition, high conflict or insufficient score/margin produce UNKNOWN conservative fallback. UNKNOWN confidence is capped conservatively.

# 15. Impulse/micro context

[STATIC_PROVEN] Impulse uses eight closed 5m bars. It searches causally ordered low→later high and high→later low excursions. Required move is max(3.0%, 2.5 × ATR%). This is a 40-minute context gate and is materially larger than the 40 bps target floor; it is not by itself terminal because structural rules and micro routes interact.

# 16. Setup families

| Family | Active source route | Main first-unmet condition in latest persisted 24h | Reachability |
|---|---|---|---|
| Momentum Continuation | v2 micro route | 1478 no momentum; 18 entry evidence; 11 direction | reachable; 124 candidates |
| Breakout | legacy structural mapping | direction/breakout trigger | reachable; 1 candidate |
| Breakout Retest | structural retest mapping | no recognized retest evidence | source-reachable; no candidate in window |
| Range Bounce | range rejection | no edge rejection/range regime | source-reachable; no candidate |
| Liquidity Sweep | false breakout reversal | no false-breakout evidence | source-reachable; no candidate |
| Trend Pullback | pullback continuation | direction/pullback trigger | source-reachable; no candidate |
| Compression Break | breakout + COMPRESSION | direction/breakout trigger | source-reachable; no candidate |

[STATIC_PROVEN] The micro route requires direction, momentum and normal/strong entry evidence, with quality not POOR/INVALID. Indicator votes can choose direction but cannot manufacture momentum while authoritative regime/impulse remains UNKNOWN/NO_IMPULSE.

[STATIC_PROVEN] diagnose_legacy_family_gates records producer/consumer mismatch BREAKOUT_RETEST_HELD_WITHOUT_RECOGNIZED_RETEST_CODE when applicable. [RUNTIME_PROVEN] no such occurrence appeared in the latest persisted 24h cohort.

# 17. Strategy scoring

[STATIC_PROVEN] Strategy rejects absent/invalid setup, future bars, source trade signals, hard invalidation, conflicts, unsupported family, neutral direction and poor/unknown quality. The effective minimum score consumed by risk is 87.75. Allowed current decisions use ALLOW_RESEARCH_TRADE_PLAN semantics before downstream PAPER authority.

# 18. Risk compatibility

[STATIC_PROVEN] Risk validates source status, review flag, minimum quality/score, supported strategy type and direction. Risk score is strategy score +5 for GOOD or +2 otherwise, minus up to 10 warning points; ≥80 LOW, ≥65 MEDIUM, otherwise HIGH. Set #2 position risk is 5 bps, max open positions 2, max new commands per cycle 2, total open risk 50 bps.

# 19. Stop geometry

[STATIC_PROVEN] LONG raw stop = causal invalidation − ATR×0.25; SHORT = causal invalidation + ATR×0.25. Distance is abs(entry−stop)/entry×10,000. Stops are rejected, not clipped, above 36 bps.

[RUNTIME_PROVEN] Latest persisted 24h PAPER rejection reasons: 87 SCALP_REJECT_CAUSAL_STOP_TOO_WIDE, 11 ECONOMIC_GEOMETRY_NOT_FEASIBLE, 5 duplicate opportunity.

# 20. Target selection

[STATIC_PROVEN] SCALPING_NEAREST_VIABLE_TARGET_V3 orders causal targets from local 5m structure through validated structural/higher-timeframe candidates, removes future/wrong-side/unreachable candidates and does not synthesize a target. Active target floor is 40 bps.

# 21. Cost model

[STATIC_PROVEN] Costs include authenticated Binance taker commission, public spread, fixed 2+2 bps slippage, adverse-fill reserve 3 bps and bounded depth impact up to 20 bps. Snapshot freshness limit is 86400 seconds and missing/stale authority fails closed.

[RUNTIME_PROVEN] Current commission snapshot is READY for all 20 symbols with zero refresh failures.

# 22. RR/EV

[STATIC_PROVEN] Gross RR = gross reward/gross risk. Net reward subtracts round-trip costs; effective risk includes entry-side adverse costs. Net RR and break-even probability are computed from these values. Minimum planned RR is 0.476674, minimum net edge 5 bps, probability confidence 0.85 and bucket minimum sample 20. Static RR fallback is disabled. Empirical negative EV is diagnostic in the current policy, while missing authority remains explicit.

# 23. Portfolio/final approval

[STATIC_PROVEN] Portfolio authority owns open-position capacity and total open risk; selector owns cycle ranking/max winners; execution owns claim/idempotency/readiness. Duplicate opportunity is enforced by one-execution-per-opportunity and structural reset policy.

# 24. PAPER plan

[STATIC_PROVEN] Plans bind symbol, profile, parameter/config identity, causal entry/stop/target, quantity approval, cycle boundary and validity. TTL/entry window is 30 seconds. Plans remain PAPER-only and non-LIVE.

# 25. Selector

[RUNTIME_PROVEN] In the latest persisted 24h cohort, 10 plan outcomes were projected: 9 selected and 1 lower-rank rejection. Twelve additional PAPER_PLAN_READY rows have no paper_plan_execution_outcome projection; all cluster at 13:00–13:10 UTC and are classified as an observability/lifecycle gap pending a direct worker trace.

# 26. Execution readiness

[RUNTIME_PROVEN] Current runtime health reports DB durability ready, scheduler/selector/execution workers active, mutation enabled for PAPER, LIVE disabled. Commission is ready.

# 27. Command/fill

[RUNTIME_PROVEN] All 9 selected outcomes in the latest persisted cohort terminated ENTRY_FILL_WINDOW_MISSED before command creation. No commands, orders, fills or positions were created for that cohort.

~~~mermaid
stateDiagram-v2
  [*] --> PlanReady
  PlanReady --> NotSelected: lower rank/capacity
  PlanReady --> Selected
  Selected --> Command: valid window + readiness
  Selected --> Expired: entry window missed
  Command --> Order
  Order --> Fill
  Fill --> Position
~~~

# 28. Position

[STATIC_PROVEN] Position persistence links command→order→entry fill→position and stores quantity, notional, entry/exit fees, stop/target, source IDs and configuration fingerprint.

# 29. Exit evaluator

[STATIC_PROVEN] Exit evaluation covers entry invalidation, causal stop, take profit, structure failure, momentum failure, time stop and safety/recovery paths. Same-candle stop/target ambiguity is resolved conservatively. Stale-position net-PnL protection remains governed by explicit policy.

[RUNTIME_PROVEN] Natural compatible history: 91 STOP_LOSS, 68 SYSTEM_SAFETY_EXIT, 29 TAKE_PROFIT, 4 NET_PNL_PROTECTION and 1 recovery close.

~~~mermaid
stateDiagram-v2
  [*] --> Open
  Open --> StopLoss: causal stop
  Open --> TakeProfit: target
  Open --> NetProtection: protected net PnL
  Open --> SafetyExit: structure/momentum/time/system
  StopLoss --> Closed
  TakeProfit --> Closed
  NetProtection --> Closed
  SafetyExit --> Closed
  Closed --> [*]
~~~

# 30. Persistence/schema

| Entity | Writer | Reader | Purpose |
|---|---|---|---|
| candles_* | market-data sync | orchestrator/exit | closed OHLCV |
| online_pipeline_runs/results | orchestrator | funnel/collector | A→Z decision trace |
| paper_plan_execution_outcomes | selector/lifecycle | readiness/funnel | selection and terminal result |
| paper_execution_commands | executor | order service | immutable command |
| paper_orders/fills | simulator | position service | simulated execution |
| paper_positions | position service | lifecycle/reporting | position/PnL |
| paper_exit_decisions | exit evaluator | simulator/reporting | causal close |
| scalping_opportunities | orchestrator/operator | selector | one-execution policy |
| trading_universe_runtime_state | activation workflow | runtime | authoritative universe |
| commission snapshot files | orchestrator | cost model | authenticated fee authority |

~~~mermaid
erDiagram
  ONLINE_PIPELINE_RUNS ||--|| ONLINE_PIPELINE_RESULTS : has
  ONLINE_PIPELINE_RUNS ||--o| PAPER_PLAN_EXECUTION_OUTCOMES : projects
  PAPER_PLAN_EXECUTION_OUTCOMES ||--o| PAPER_EXECUTION_COMMANDS : creates
  PAPER_EXECUTION_COMMANDS ||--o{ PAPER_ORDERS : creates
  PAPER_ORDERS ||--o{ PAPER_FILLS : receives
  PAPER_ORDERS ||--o| PAPER_POSITIONS : opens
  PAPER_POSITIONS ||--o{ PAPER_EXIT_DECISIONS : evaluates
~~~

Alembic has one head: 0037_continuous_two_lifecycle_slots. No migration was applied.

# 31. Runtime parameter registry

| Stage | Parameter | Effective value | Source | Reject-capable |
|---|---|---:|---|---|
| setup | history/ATR/impulse/structure/regime | 120/12/8/12/24 bars | Set #1 inherited | yes |
| setup | impulse threshold | max(3%, 2.5×ATR%) | Set #1 inherited | indirect |
| strategy | minimum score | 87.75 | Set #1 inherited | yes |
| geometry | ATR buffer | 0.25 ATR | Set #1 inherited | yes |
| geometry | max stop | 36 bps | Set #2 override | yes |
| target | minimum target | 40 bps | Set #2 override | yes |
| economics | minimum net edge | 5 bps | Set #2 override | yes |
| RR | minimum planned RR | 0.476674 | Set #2 override | yes |
| probability | confidence/sample | 0.85 / 20 | Set #2/Set #1 | yes |
| risk | risk per trade | 5 bps | risk Set #2 | yes |
| portfolio | open/new/total risk | 2 / 2 / 50 bps | risk policy | yes |
| execution | TTL / drift | 30 sec / 10 bps | Set #1 inherited | yes |
| exit | soft/hard/extension | 600/1200/300 sec | Set #2 overrides | yes |

Resolved config hash = 1105f809559e2ace90236d5e8575b46ca4d055e0cf44f0b1704ee395f7b2e333.
Trade config hash = 72e32d26f84f0cb1c23bb155efb7db36ab55f81de37dcf6db74d2a4afe86cf0d.

# 32. Performance/latency

Fixed endpoint E = 2026-10-27 17:50 UTC.

| Window | Runs / completed | Setup / risk pass | Plan ready | p50 / p95 / max total duration |
|---|---:|---:|---:|---|
| 4h | 960 / 913 | 55 / 55 | 8 | 2.329 / 6.970 / 60.666 s |
| 12h | 1199 / 1152 | 122 / 122 | 22 | 2.543 / 10.987 / 60.666 s |
| 24h | 1679 / 1632 | 125 / 125 | 22 | 2.436 / 9.245 / 60.666 s |

The 12h/24h denominators are below 20×expected boundaries because the runtime was not continuously available; no missing rows were fabricated.

For the 10 plans with selector outcomes, boundary→plan delay p50/p95/max = 94.569/219.252/219.826 s; 0/10 were within the 30-second entry window. Plan→selector p50/p95 = 11.598/14.607 s. The causal deadline failure is late plan creation, followed by selector pickup; command creation was never reached.

# 33. Observability/Funnel defects

- [RUNTIME_PROVEN] Twelve of 22 PAPER_PLAN_READY rows lack paper_plan_execution_outcomes.
- [STATIC_PROVEN] Family first-unmet diagnostics are persisted for all seven families.
- [STATIC_PROVEN] Producer/consumer mismatch trace exists for breakout-retest evidence.
- [RUNTIME_PROVEN] Current readonly health is HTTP 200, operational and ready.
- [INFERRED] The missing 12 outcomes likely correspond to an inactive/unavailable selector interval; exact worker cause is UNPROVEN without logs correlated to 13:00–13:10 UTC.
- Market-data container image revision is UNSET, a provenance defect even though data health is operational.

# 34. Revision/provenance

| Role | Runtime revision | Expected relation | Result |
|---|---|---|---|
| local HEAD | 3487534 | docs + latest diagnostics | current |
| orchestrator | 9fb4eef | latest trading-path implementation | match for production code |
| readonly | a429fe0 | role-specific older API image | documented split |
| operator | c5e8db6 | role-specific lifecycle image | documented split |
| collector | d93d3a5 | role-specific collector | documented split |
| market data | UNSET | immutable revision required | defect |

No single deployed SHA represents all services; call graphs and runtime facts are labelled by role.

# 35. Tests classification

There are 497 tracked test modules/files.

| Class | Rule/examples | Result |
|---|---|---|
| CURRENT_V2 | engine_analysis, engine_exit, engine_paper, current v2 authority/profile/probability tests | retained |
| LEGACY_V1 | tests constructing trade-5m-v1 as active input | obsolete/requires migration |
| RESEARCH | tests/research and parameter sweep | retained research scope; optional optuna missing |
| MIGRATION | migration/Alembic schema contract tests | retained |
| INFRASTRUCTURE | market data, backup/PITR, control, security, API/deployment | retained |
| UNKNOWN | files not proven obsolete by this audit | retained |

Focused v2: 12 passed.
Broader selected scope: 162 passed, 53 failed, 5 skipped.
Failure classification:
- 52 failures are stale trade-5m-v1 fixtures in test_5m_scalping_geometry_quota_cost_remediation.py, engine_orchestrator/test_5m_runtime_parameterization_and_owner.py and engine_orchestrator/test_5m_shadow_full_funnel.py; production code correctly rejects removed v1.
- 1 failure is stale DEFAULT_POLL_SECONDS==5 while current source uses 0.5 seconds.
- Active-production collection also imports research/test_search_optimizer.py before deselection and fails because optional optuna is not installed.
No test was edited or deleted.

# 36. Dead/legacy code findings

- trade-15m-v1 remains disabled compatibility code.
- trade-5m-v1 runtime profile is removed; tests that instantiate it are legacy debt.
- parameter-sweep code is research-only.
- No production source module is deleted; static dead findings are DEAD_CODE_CANDIDATE only.

# 37. CLEANUP_MANIFEST_BEFORE_DELETE

| Path | Files | Size | Tracked | Category | References | Action |
|---|---:|---:|---:|---|---|---|
| .pytest_cache | 5 | 4,826,659 | no | CACHE | ignored; Docker-excluded | DELETE_PROVEN_SAFE |
| 100 verified __pycache__ directories outside .venv/.git | 1938 | 35,211,799 | no | CACHE | ignored; reproducible bytecode | DELETE_PROVEN_SAFE |
| pytest_tmp | 0 | 0 | no | TEMP | empty | DELETE_PROVEN_SAFE |
| traders_ml.egg-info | 6 | 24,968 | no | BUILD_ARTIFACT | pip-generated; ignored | DELETE_PROVEN_SAFE |
| reports | 1449 | 80,800,163,205 | no | RUNTIME/RESEARCH EVIDENCE | unique runtime/calibration history | KEEP |
| artifacts | 895 | 911,209,659 | mixed | RESEARCH_ARTIFACT | 92 pre-existing user deletions | REVIEW_REQUIRED |
| two untracked October forensic reports | 2 | 3,473,892 | no | AUDIT EVIDENCE | unique evidence used here | KEEP |
| .codex-remote-attachments | 15 | 1,393,156 | no | TASK EVIDENCE | provenance uncertain | REVIEW_REQUIRED |
| .venv | 20,062 | 635,551,985 | no | VENV | explicitly retained | KEEP |
| alembic/config/app/scripts/tests | — | — | mixed | REQUIRED | runtime/build/schema/test | KEEP |
| traders_ml_recovery | — | 138,158,607,252 | no | BACKUP/WAL/PITR | recovery authority | KEEP |
| client/mobile contents | — | — | separate repos | CLIENT | out of scope | CLIENT_CLEANUP_CANDIDATE only |

All 92 pre-existing tracked deletions remain PREEXISTING_USER_CHANGE and are excluded from audit-owned cleanup and commits.

# 38. Deleted files

[RUNTIME_PROVEN] The frozen manifest was executed by exact path, without wildcard cleanup or `git clean`. The unique initial candidates comprised 1,949 generated files totaling 40,063,426 bytes: 1,938 Python bytecode files, 5 pytest-cache files and 6 egg-info files. `pytest_tmp` was empty.

After validation activity, 14 Python bytecode files totaling 276,335 bytes regenerated in five active cache directories. They were retained as `REVIEW_REQUIRED`; the final net absence relative to the frozen candidate set is 1,935 files / 39,787,091 bytes. Physical deletion events, including one removal of regenerated validation bytecode, totaled 1,963 files / 40,339,761 bytes.

Deleted generated roots: `.pytest_cache`, `pytest_tmp` and `traders_ml.egg-info`. No tracked file, source, configuration, migration, test, client/mobile file, virtual environment, report, artifact or recovery datum was deleted by the audit.

# 39. Kept ambiguous files

Reports, calibration captures, prior forensic reports, artifacts not already deleted by the user, remote attachments, recovery data and every client/mobile file are retained. Five actively regenerated cache directories (`app`, `app/config`, `app/db`, `app/engine_safety`, `scripts`) containing 14 files / 276,335 bytes are retained as `REVIEW_REQUIRED` because validation/runtime tooling recreated them.

# 40. Post-cleanup validation

- [TEST_PROVEN] Server import/compile chain passed before cleanup; targeted imports passed again after cleanup.
- [TEST_PROVEN] Alembic graph resolves to head `0037_continuous_two_lifecycle_slots`; no upgrade or downgrade was run.
- [TEST_PROVEN] Post-cleanup curated causality, structure/regime, exit, v2 profile, probability and cadence scopes: 48 passed.
- [TEST_PROVEN] Focused independent Scalping v2 profile scope: 12 passed.
- [TEST_PROVEN] Broader selected baseline remains 162 passed, 53 failed, 5 skipped; all failures are classified in section 35 and were not introduced by cleanup.
- [TEST_PROVEN] Docker build-only validation of target `production-base` succeeded for local HEAD; no service was recreated or deployed.
- [RUNTIME_PROVEN] Read-only production observation after cleanup shows five consecutive 20/20 completed boundaries through 2026-10-31 15:20 UTC. Production services were not restarted by the audit.
- [STATIC_PROVEN] `.pytest_cache`, `pytest_tmp` and `traders_ml.egg-info` are absent; `.venv`, Alembic, configuration, source, tests, reports, artifacts and recovery data remain present.
- [STATIC_PROVEN] Git reconciliation shows no audit-owned tracked cleanup diff. The 92 deleted tracked artifacts, one modified test and two pre-existing untracked forensic reports remain user-owned and unstaged.

# 41. Root-cause ranking

ROOT_CAUSE_1
- type = PERFORMANCE
- confidence = PROVEN
- evidence = 10/10 projected plans created after 30-second window; p50 94.569 s
- affected stage = boundary→plan
- impact = selected plans terminate ENTRY_FILL_WINDOW_MISSED
- limitation = only 10 projected outcomes in the fixed persisted cohort

ROOT_CAUSE_2
- type = LOGIC/PARAMETER SCALE
- confidence = PROVEN for predicate, STRONG for runtime impact
- evidence = 87 wide-stop rejects; stop = invalidation ±0.25 ATR; cap 36 bps
- affected stage = geometry
- impact = majority of downstream PAPER rejects

ROOT_CAUSE_3
- type = LOGIC/REACHABILITY
- confidence = STRONG
- evidence = 124/125 setup candidates are Momentum Continuation; four configured families absent
- affected stage = setup
- impact = effective strategy diversity is extremely narrow
- limitation = absence in one incomplete 24h cohort does not prove dead code

ROOT_CAUSE_4
- type = OBSERVABILITY/LIFECYCLE
- confidence = PROVEN for missing projection, UNPROVEN for cause
- evidence = 12/22 PAPER_PLAN_READY rows lack outcome rows
- affected stage = plan→selector projection
- impact = terminal outcome cannot be attributed for 54.5% of ready plans

ROOT_CAUSE_5
- type = TEST_DEBT
- confidence = PROVEN
- evidence = 52 stale v1 fixture failures + one stale poll interval assertion
- affected stage = validation
- impact = broad suite cannot be treated as green current-v2 certification

ROOT_CAUSE_6
- type = PERFORMANCE/OPERATIONS
- confidence = PROVEN
- evidence = Docker/runtime gap from 2026-10-27 to 2026-10-31; incomplete 12h/24h denominators
- affected stage = continuous operation/data freshness
- impact = no wall-clock-fresh complete 24h cohort at audit time

# 42. Recommended future fixes

1. Separately diagnose boundary→plan latency with stage timestamps; do not change TTL before attribution.
2. Compare causal invalidation alternatives for the 87 wide-stop rejects without optimizing thresholds.
3. Investigate the 12 missing selector outcome rows using worker logs and claim state.
4. Migrate or delete stale v1 tests in a dedicated test-debt change; retain shared invariant coverage.
5. Add immutable source revision to market-data image.
6. Run a fresh uninterrupted 24h PAPER observation after runtime recovery.
7. Treat setup-family reachability changes as a separate behavioral proposal requiring explicit approval.

## Cleanup result summary

```text
TOTAL_FILES_BEFORE = 1,949 frozen cleanup candidates
TOTAL_SIZE_BEFORE = 40,063,426 candidate bytes
FILES_DELETED = 1,935 net absent; 1,963 physical deletion events including regenerated bytecode
SIZE_DELETED = 39,787,091 net bytes; 40,339,761 physical deletion-event bytes
TRACKED_FILES_DELETED = 0 audit-owned
UNTRACKED_FILES_DELETED = 1,935 net generated files
OLD_TESTS_DELETED = 0
OLD_TESTS_MIGRATED = 0
OLD_TESTS_KEPT = 3 LEGACY_V1 modules plus all shared/current test modules
ARCHIVES_DELETED = 0
OLD_REPORTS_DELETED = 0
RESEARCH_ARTIFACTS_DELETED = 0 audit-owned
CACHES_DELETED = .pytest_cache plus 1,938 initial non-venv bytecode files; 14 bytecode files regenerated and retained
REVIEW_REQUIRED_FILES = 924 present files across artifacts, remote attachments and regenerated caches
PREEXISTING_USER_CHANGES_PRESERVED = YES
```

## Completion criteria

```text
FULL_SERVER_CALL_GRAPH = DONE
FULL_SCALPING_A_TO_Z = DONE
BOOK_ANALYZER_REVIEW = DONE
SETUP_FAMILY_REVIEW = DONE
STOP/TARGET/COST/RR_REVIEW = DONE
EXECUTION_REVIEW = DONE
EXIT_REVIEW = DONE
PERFORMANCE_REVIEW = DONE
TEST_CLASSIFICATION = DONE
ROOT_FILE_INVENTORY = DONE
SAFE_CLEANUP = DONE
POST_CLEANUP_VALIDATION = PASS_WITH_CLASSIFIED_PREEXISTING_TEST_DEBT
MAIN_REPORT_SAVED = YES
```

# DECISION_LEDGER

| Order | Stage | Owner | Predicate/result | Terminal reason |
|---:|---|---|---|---|
| 1 | closed data | market_data snapshot | required closed TFs available and fresh | freshness/integrity failure |
| 2 | analysis | online_runner | normalized causal OHLCV | analysis error/degraded |
| 3 | Nison/Altunina/Schwager | analysis modules | evidence produced | nonterminal insufficiency |
| 4 | matrix/composer | evidence matrix/composer | score, margin, conflict | UNKNOWN nonterminal |
| 5 | impulse | impulse diagnostics | max move ≥ max(3%,2.5×ATR%) | diagnostic/micro input |
| 6 | setup | SetupDetector | family predicates and validity | NO_SETUP/SETUP_INVALID |
| 7 | strategy | strategy_rules | quality, direction, conflicts, score | STRATEGY_REJECT |
| 8 | risk | RiskPolicy | score/type/direction/account rules | RISK_REJECT |
| 9 | stop | scalping_shadow | causal stop ≤36 bps | STOP_TOO_WIDE |
| 10 | target | scalping_shadow | causal viable target ≥40 bps | no feasible geometry |
| 11 | costs | cost source | authoritative fresh fees/spread/depth | cost unavailable/invalid |
| 12 | RR/EV | scalping policy | edge, RR, empirical authority | economic rejection |
| 13 | final approval | materializer | quantity/capacity/config identity | reject |
| 14 | plan | paper runner | immutable plan + 30s validity | NO_PLAN |
| 15 | selector | plan outcomes | rank/capacity/claim | lower rank/not ready |
| 16 | execution | production executor | still valid + readiness | ENTRY_FILL_WINDOW_MISSED |
| 17 | order/fill | simulator | causal price/cost policy | rejected/expired |
| 18 | position | repositories | idempotent entry persistence | persistence failure |
| 19 | exit | exit evaluator | stop/target/invalidation/time/safety | exit cause |
| 20 | close/PnL | lifecycle worker | fill/accounting identity | closed/recovery |

# A_TO_Z_SOURCE_MAP

| Stage | Primary file/function | Input | Output/side effect |
|---|---|---|---|
| ingestion | engine_market_data continuous_sync_daemon | Binance klines | candles_* writes |
| snapshot | market_data_snapshot | closed DB candles | immutable snapshot |
| orchestrator | engine_orchestrator.pipeline_runner.PipelineRunner | snapshot/profile | run/result writes |
| analysis | engine_analysis.online_runner / engine.run_engine_analysis | normalized OHLCV | analysis snapshot |
| Nison | nison_candlestick_context | morphology/history | signed evidence |
| Altunina | altunina_trend_context | pivots/swings | structure evidence |
| Schwager | schwager_range_context | zones/touches | range/breakout evidence |
| matrix | book_evidence_matrix | three evidence streams | hypotheses/conflict |
| composer | regime_composer | matrix/integrity | regime/confidence |
| impulse | impulse_phase_diagnostics | 8 closed 5m bars | phase/quality |
| setup | setup_detector.detect | analysis snapshot | setup candidate |
| strategy | strategy_rules.evaluate_strategy_rules | setup | strategy decision |
| risk | risk_policy.RiskPolicy.evaluate_shadow | strategy | risk decision |
| geometry/economics | scalping_shadow.evaluate_scalping_shadow | causal levels/costs | approval/reject diagnostics |
| final approval | shadow_approval_materializer | approved candidate/account | executable PAPER approval |
| plan | scalping_paper_runner | risk/geometry/approval | PAPER plan |
| selector | plan selector/outcome repository | plans/capacity | winner/outcome |
| command | production_executor | selected valid plan | command |
| order/fill | paper services/simulator | command/closed price | order/fill |
| position | paper repositories | entry fill | position |
| exit | production_lifecycle_worker + exit evaluators | closed 1m/position | exit decision/fill |
| projection | server_api trading_funnel/funnel_export | persisted lifecycle | read-only API |


# Appendix A — PREEXISTING_USER_CHANGE manifest

These tracked deletions existed before the audit, remain unstaged audit-external changes and were not restored or committed.

| Path | HEAD bytes | HEAD SHA-256 | Audit action |
|---|---:|---|---|
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/CATEGORICAL_SEPARABILITY.json | 14826 | 045f62b4cf94ce3c7692e50c0d7fd9fb807bb50c65d8d3b38588e738bb8cc823 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/FEATURE_ACTIVITY.json | 8031 | 480f6958ec36dd4582bce252f8d2c66e9e66e833015cd709958ca1f0ad7b9f55 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/FEATURE_RANKING.json | 21125 | 69fb3322370f604abdeb8b66115f9b93433fccbe9dbc42f5bebb439c7493fbfe | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/FEATURE_REGISTRY.json | 26099 | 9633e181ff5acc671a367be197f8034435a6eb96e89f5148d857f9ee27423041 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/INTERACTION_SCREEN.json | 14353 | 9eb5f6731216a71e57ef77537c7bad6b1017e6bcc32ba5c11915b155ca882ce3 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/NUMERIC_SEPARABILITY.json | 23217 | 2a342253fe8c018aea5e91818351bdeb84a6456c1c0a8796272c01c054922253 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/REPORT.md | 2663 | 97ee6a1fa0bb98d1acff429fc9e11029be3a12d7c9ba494199c50a66262d9481 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/SEPARABILITY_DATASET.jsonl | 36942 | 580371cb10ada86ab22a6135bf8e428b96794498bae914251341c1c0c0da5102 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/SEPARABILITY_DATASET_MANIFEST.json | 1697 | 909006172183f00f0799f5a8f2ca16ac87edbd0c77f142db0c2c426a06f395d0 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/01_separability/SEPARABILITY_HANDOFF.json | 42131 | 35cb84eb4a52c888fe16db0c8ebc6c7df7d70f840780872f6e6a5ed0fbd25c03 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/DATA_DRIVEN_RANGE_HANDOFF.json | 23963 | 51d3986e5fb7ae5ea31970f15ab390a1abdd68d0ec1bfbca4193f3bdb81aaf27 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/DATA_DRIVEN_SEARCH_RANGES.json | 126311 | a53ec81ea0be59db5ddf8d9e46e2b7ed273b3d84ef67765e1855de228b1b45f0 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/LEGACY_RANGE_COMPARISON.json | 11731 | 7cf556f59c6fddf2a3bdd181b57cdb9dc4d31d79d00972b51304947a646b8660 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/PARAMETER_EVIDENCE_MAP.json | 39251 | 1d0ae11eab7e43866cd0cee2a102c2b6ca8c9e6b9ac65137161bc76dc131dc3a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/RANGE_GENERATION_TRACE.json | 149846 | 141f359d0787d93a402279f38eca8a453004373740312ce35c7aca8678817087 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/02_data_driven_ranges/REPORT.md | 7269 | 6dcf523f9bf32c3640714e51e217317b3828b34fe42a171684a8c68571c9524e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/BEHAVIORAL_CLUSTERS.json | 143201 | 03ae30eeb1f46ba86fb83abbd126f6a76f82b2cea5df54b7b1dea5881dd0cbe2 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/CHECKPOINT.json | 521 | c74aef4bce0500f296a5f9f1b1033b0f4a130073435490b63115365d60855144 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/EXPANDED_SEARCH_CONFIG.json | 2322 | 64d76ce8060da461f7a2f9e117d949b96d259f327da5389063f829590a5e12c1 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/EXPANDED_SEARCH_HANDOFF.json | 24695 | c33cdb76ad04e6320ca7b448bdf5c03f918c0c8e170b91c7512b7443a14504dc | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/EXPANDED_SEARCH_RESULTS.jsonl | 1375030 | ab7f1cf524d2dfe570736d67dde255df0f85b043717bd24410b4377e3d2572c4 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/LEGACY_EXPANDED_SEARCH_COMPARISON.json | 919 | 2a3a01e8ae697cc2af6ec8c885155183bcafb755512ec9978f08db24e83330dd | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/REPORT.md | 927 | a22d19703effaa899d0acf881c375f7a65d056a8018b87ae336f6be606ab6682 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/SEARCH_VALUE_NORMALIZATION.json | 2842 | b002a60db8e7ffeeb58b86bc1efae0084d08faec5068eed8362138b58fbd909a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/03_expanded_search/STATUS.json | 1792 | 4fd867b45377825864bf2a98e099f759b531c3ccf23113c3df9e004535533e0b | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_BEHAVIORAL_CLUSTERS.json | 72534 | c3e7e32c24c8f61db6bb69787f0a58392d11237bf170779add8cc6521cc06a2b | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_CANDIDATE_TRACE.jsonl | 118452 | 7746c874ec9df05273f00337d8bb1402f131b1fc77f6337d3e1aff906b2aac6a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_PARAMETER_SENSITIVITY.json | 15675 | f21f6d5db920609ffc12519d20c0c194c3e5ead43acdcb2a7f6bfabdb55fa0b5 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_REFINEMENT_CONFIG.json | 1931 | e3a0fb555670af7a2a8e3b0580ce3a511adc1dd3f5b63763c4ebc8270a334692 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_REFINEMENT_HANDOFF.json | 42978 | e7adb853882f20c070cfc231f2681208eb8d851d0630f6ce09dedb54201abfd7 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_RESULTS.jsonl | 174578 | 59c3bba1d7e80535b23f3183f544daa711b2655ffc2801b8452ee0790357d534 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/ADAPTIVE_ROUNDS.jsonl | 908 | 5cf422075c50dc927d50562fc7082d4c7c3d93c883ef95d65928370b7a404d97 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/BEHAVIORAL_TRANSITION_GRAPH.json | 84264 | 9b5e2c9e67d1cafb56a84f733bc7e3c6057b9b5ffdbb7d7a1ef150d1fa6cc2ac | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/CHECKPOINT.json | 37817 | ac5bf2b32ddba13cb9694a41339c9606d333d4411cd19c5e77d76b73b0ef0469 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/REPORT.md | 574 | 87586376be47b026dd2b7c6c0a24a40595cfb7067abb79eb4955f21f255e623a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/04_adaptive_refinement/STATUS.json | 3637 | 4c94412e05f34f988fd1c9ac5aaab58556446487e6c4b1c8234172f108d2f723 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260912_232513_652/SINGLE_SYMBOL_PIPELINE_MANIFEST.json | 3573 | 5d51919d9ca1dff73d237850e5e0ea028a19d6ebcd3318e88f2709ddaeeb5ff4 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/CATEGORICAL_SEPARABILITY.json | 14826 | 045f62b4cf94ce3c7692e50c0d7fd9fb807bb50c65d8d3b38588e738bb8cc823 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/FEATURE_ACTIVITY.json | 8031 | 480f6958ec36dd4582bce252f8d2c66e9e66e833015cd709958ca1f0ad7b9f55 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/FEATURE_RANKING.json | 21125 | 69fb3322370f604abdeb8b66115f9b93433fccbe9dbc42f5bebb439c7493fbfe | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/FEATURE_REGISTRY.json | 26099 | 9633e181ff5acc671a367be197f8034435a6eb96e89f5148d857f9ee27423041 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/INTERACTION_SCREEN.json | 14353 | 9eb5f6731216a71e57ef77537c7bad6b1017e6bcc32ba5c11915b155ca882ce3 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/NUMERIC_SEPARABILITY.json | 23217 | 2a342253fe8c018aea5e91818351bdeb84a6456c1c0a8796272c01c054922253 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/REPORT.md | 2664 | 89681f404c1d65d5ca7980aeff8612650a491d35f712c6f1aedd959f9d8b2f9f | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/SEPARABILITY_DATASET.jsonl | 36942 | 580371cb10ada86ab22a6135bf8e428b96794498bae914251341c1c0c0da5102 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/SEPARABILITY_DATASET_MANIFEST.json | 1698 | e425d053f46a5f2c51c47c098b09f05432a0fdc9a83de2b5e632499d1552be16 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/01_separability/SEPARABILITY_HANDOFF.json | 42131 | 35cb84eb4a52c888fe16db0c8ebc6c7df7d70f840780872f6e6a5ed0fbd25c03 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/DATA_DRIVEN_RANGE_HANDOFF.json | 23963 | f38d8fc0495845459ddcbb953f36936b1e26fc88979f4b7c97651333e3d46f80 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/DATA_DRIVEN_SEARCH_RANGES.json | 126311 | 14c6939cac795dac0bfb162ce930b703d92ba0b70689e8c0dcaccbd0f02648ac | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/LEGACY_RANGE_COMPARISON.json | 11731 | 7cf556f59c6fddf2a3bdd181b57cdb9dc4d31d79d00972b51304947a646b8660 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/PARAMETER_EVIDENCE_MAP.json | 39251 | 1d0ae11eab7e43866cd0cee2a102c2b6ca8c9e6b9ac65137161bc76dc131dc3a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/RANGE_GENERATION_TRACE.json | 149846 | 141f359d0787d93a402279f38eca8a453004373740312ce35c7aca8678817087 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/02_data_driven_ranges/REPORT.md | 7269 | 6dcf523f9bf32c3640714e51e217317b3828b34fe42a171684a8c68571c9524e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/BEHAVIORAL_CLUSTERS.json | 143201 | 03ae30eeb1f46ba86fb83abbd126f6a76f82b2cea5df54b7b1dea5881dd0cbe2 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/CHECKPOINT.json | 521 | f71501c349311ad2c34e70362a719d6d97a2e6591373090068702559dd2e8d3f | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/EXPANDED_SEARCH_CONFIG.json | 2322 | 3d902a29acab45b920c500f746083d4dca1e07a2696111caf9d4b334d4a7968a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/EXPANDED_SEARCH_HANDOFF.json | 24695 | 0684fd650ad4eddcb947268e8a9bc032b6f3f7f193e38dcb481d0ca02c63647e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/EXPANDED_SEARCH_RESULTS.jsonl | 1375030 | ab7f1cf524d2dfe570736d67dde255df0f85b043717bd24410b4377e3d2572c4 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/LEGACY_EXPANDED_SEARCH_COMPARISON.json | 919 | 2a3a01e8ae697cc2af6ec8c885155183bcafb755512ec9978f08db24e83330dd | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/REPORT.md | 928 | 1f74613fe75c83f19d3e0171962d6243b8311340aebe17e499c6a1ca8b1f233f | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/SEARCH_VALUE_NORMALIZATION.json | 2842 | b002a60db8e7ffeeb58b86bc1efae0084d08faec5068eed8362138b58fbd909a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/03_expanded_search/STATUS.json | 1793 | f4495f8c0a92aa37dfd5cba929e8ecfece2dd634fe4654d1c280bbde0e2c331c | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_BEHAVIORAL_CLUSTERS.json | 72534 | c3e7e32c24c8f61db6bb69787f0a58392d11237bf170779add8cc6521cc06a2b | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_CANDIDATE_TRACE.jsonl | 118452 | 7746c874ec9df05273f00337d8bb1402f131b1fc77f6337d3e1aff906b2aac6a | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_PARAMETER_SENSITIVITY.json | 15675 | f21f6d5db920609ffc12519d20c0c194c3e5ead43acdcb2a7f6bfabdb55fa0b5 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_REFINEMENT_CONFIG.json | 1931 | 4cec1e6a729c7664769395e565b58d3bc4f4f3f30d3f776e7cfb0d4822b165e3 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_REFINEMENT_HANDOFF.json | 42978 | e88277c740101083e5ac253a3b6bd6caba18384e1553088127350a0d49f47e91 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_RESULTS.jsonl | 174578 | 59c3bba1d7e80535b23f3183f544daa711b2655ffc2801b8452ee0790357d534 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/ADAPTIVE_ROUNDS.jsonl | 908 | 5cf422075c50dc927d50562fc7082d4c7c3d93c883ef95d65928370b7a404d97 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/BEHAVIORAL_TRANSITION_GRAPH.json | 84264 | 9b5e2c9e67d1cafb56a84f733bc7e3c6057b9b5ffdbb7d7a1ef150d1fa6cc2ac | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/CHECKPOINT.json | 37817 | 4deaabb36017a40697e70cf44c782d0487cef7f1d7fd7cea9a920650c92839f5 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/REPORT.md | 575 | 92f8638dd28fd0815efa5715d3f5b03c8ba0cf6abe2f304c1e02b748f4838762 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/04_adaptive_refinement/STATUS.json | 3638 | 7c59feba5cba45a83a56a408f01fd6baee75f64c7e6fc693f2941b15fe4b071e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/REPORT.md | 383 | 038169bfca6929a550f5fd04414a3b958efc36acebb527013b072060de8d87ab | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/STATUS.json | 3574 | bd543d8334ebfaf66f5d7625009ba496a6c91d1887b82cdbb0f6e80916ec60ac | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/VALIDATION_BEHAVIORAL_RANKING.json | 150745 | 56753ccf5a04811524f51d571f9f805cec9a655b8d257d0b6ebac2270424adc7 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/VALIDATION_ELIGIBILITY.jsonl | 970660 | b18bbdc26ef8dca9de4d88850fe2d6d3c6c85497ac9d3a6655394899955f6392 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/VALIDATION_NUMERIC_RANKING.json | 1666490 | 4ccd1937923643dd2cbe30ea9b7651a12b249f5a7c02449b299539fad550e71f | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/VALIDATION_RANKING_HANDOFF.json | 154725 | c79422182aca8fd7565e10b9acf6b29b83d21779f0b6ad452dce6403c8b46a0d | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/05_validation_ranking/VALIDATION_ROBUSTNESS.json | 34175 | 0b16c783448c683b12733dd0c0f9e99c69975b603aaf49affb86fd0201114918 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/06_finalist_freeze/FINALIST_FREEZE.json | 1376 | 61e10f00a400f468bcedc92c67ae0b36f98ab5da14b8b2d28b90fd79638934c4 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/06_finalist_freeze/FINALIST_FREEZE_HANDOFF.json | 1008 | 6efa51a2978a92a5504e21f4f8d0c34e3bb6ea756141c85b07c32fd2e0714513 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/06_finalist_freeze/FINALIST_FREEZE_INTEGRITY.json | 575 | b1b33b58928dff56883415199e4306ab5954cc85c93a32ebde80eb3728393aae | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/06_finalist_freeze/REPORT.md | 278 | c334a8e856d78e89ae7a7fbfaa5af0f90aae8bed5bbceeec01b96741aae3b6fe | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/06_finalist_freeze/STATUS.json | 995 | 1ae5a9470c43ee6990a4b39452284b08b425b335dfda2fc3d12a9011c31b4534 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/20260913_102614_045/SINGLE_SYMBOL_PIPELINE_MANIFEST.json | 5985 | cf6deec0026d38851b09a5eab0cd60b736697a513d07317dac102f2622bbde7e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/SYMBOL_RUNTIME_AUTHORITY_AUDIT.json | 75579 | 1a1c7551c8d3c43fa08fc8446d602582d6adc3a5d31ce4190b5c3da1fb309b4d | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/finalist_freeze_dogeusdt_01/FINALIST_FREEZE.json | 1377 | cd8e61a0f111b53aedd6f86378debb7a891c631b84c01c0aebe63fe3a26505c5 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/finalist_freeze_dogeusdt_01/FINALIST_FREEZE_HANDOFF.json | 1009 | b91af4afee1dd6b408e288dae5d62b31c5a04790627d0453b6040c3287bb83c3 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/finalist_freeze_dogeusdt_01/FINALIST_FREEZE_INTEGRITY.json | 575 | c9391bb5146ec0fc67688de6387ddcbce00e276e22a96c5a9a760c7434381308 | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/finalist_freeze_dogeusdt_01/REPORT.md | 279 | 054e31d22f51551d27b580cdc5a82d9ff65c8afec9b4376018875ee99d0ff77e | PRESERVE_USER_CHANGE |
| artifacts/scalping_v2_parameter_sweep/finalist_freeze_dogeusdt_01/STATUS.json | 996 | da38ee1d4185567c1319f7dbfe3f82289fb2395416661be5bf52dcff5e97857a | PRESERVE_USER_CHANGE |


# Appendix B — TEST_CLASSIFICATION

| Test module/file | Class | Basis |
|---|---|---|
| tests\conftest.py | UNKNOWN | retained; obsolescence not proven |
| tests\control_mobile_security\test_mobile_auth.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\control_mobile_security\test_mobile_profile_config.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\control_mobile_security\test_mobile_runtime_privilege_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\control_mobile_security\test_postgres_least_privilege.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\engine_analysis_online_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_analysis\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_analysis\test_causality.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_analysis\test_quality_online_and_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_analysis\test_scalping_semantics.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_analysis\test_structure_and_regime.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_execution\conftest.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_approval_policy.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_builder_validation.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_cli.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_gateways.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_idempotency.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_immutability.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_package_contract.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_serialization.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_execution\test_static_safety.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_exit\test_scalping_exit_policy.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_market_data_02_helpers.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\engine_market_data_03_helpers.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\engine_market_data_04_helpers.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\engine_observation_01_helpers.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_orchestrator_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\fixtures\freshness_retry_incidents.json | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_20_symbol_causal_retry.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_5m_runtime_parameterization_and_owner.py | LEGACY_V1 | active-v1 fixture rejected by current v2-only runtime |
| tests\engine_orchestrator\test_5m_shadow_full_funnel.py | LEGACY_V1 | active-v1 fixture rejected by current v2-only runtime |
| tests\engine_orchestrator\test_failed_boundary_prompt_retry_integration.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_audit_regression.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_daemon.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_production_incidents.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\engine_orchestrator\test_freshness_retry_snapshot.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_state_machine.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_freshness_retry_store.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_migration_0018.py | MIGRATION | schema/migration contract |
| tests\engine_orchestrator\test_migration_0019.py | MIGRATION | schema/migration contract |
| tests\engine_orchestrator\test_parallel_trade_profiles.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_parameter_set_cycle_binding.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_pipeline_result_json_safe.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_recovered_pair_health_integration.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_orchestrator\test_runtime_config_epoch.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_binance_account_commission.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_entry_refinement_order.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_entry_refinement.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_net_pnl_protection.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_outcome_diagnostics.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_scalping_execution_readiness.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_scalping_final_checklist.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_scalping_hold_lifecycle.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_scalping_opportunity_registry.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_scalping_statistics.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_paper\test_stale_position_shadow.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_position\__init__.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\conftest.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_builder_contract.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_cli.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_lifecycle.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_pnl.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_scalping_monitor.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_position\test_serialization.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_static_safety.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_position\test_store_idempotency.py | UNKNOWN | retained; obsolescence not proven |
| tests\engine_risk_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_risk\test_cross_profile_arbiter.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_risk\test_scalping_risk_order_and_sizing.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_setup_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_setup\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_setup\test_causality_diagnostics_quality.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_setup\test_families_and_status.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_strategy_01_helpers.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_strategy\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_strategy\test_decision_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\engine_strategy\test_score_diagnostics.py | CURRENT_V2 | active/scalping shared contract |
| tests\final_approval_generation_integration\__init__.py | UNKNOWN | retained; obsolescence not proven |
| tests\final_approval_generation_integration\test_natural_materialization.py | UNKNOWN | retained; obsolescence not proven |
| tests\fixtures\readonly_api_health_unknown_minimal.json | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\instrument_quantity_registry\__init__.py | UNKNOWN | retained; obsolescence not proven |
| tests\instrument_quantity_registry\test_registry_and_authorities.py | UNKNOWN | retained; obsolescence not proven |
| tests\integration\paper_natural_execution_e2e\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\paper_natural_execution_e2e\test_natural_approval_opens_position.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\paper_natural_execution_e2e\test_probability_authority_accumulation_postgres.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\paper_natural_execution_e2e\test_rr_dynamic_anchor_postgres.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\paper_natural_execution_e2e\test_scalping_profitability_integration.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\paper_natural_execution_e2e\test_set2_provenance.py | CURRENT_V2 | active/scalping shared contract |
| tests\integration\stale_position_shadow\test_postgres_e2e.py | UNKNOWN | retained; obsolescence not proven |
| tests\integration\test_engine_market_data_04_prod_smoke_postgres.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\integration\test_freshness_observer_combined.py | UNKNOWN | retained; obsolescence not proven |
| tests\lineage_identity_remediation\test_bounded_lineage_identity.py | UNKNOWN | retained; obsolescence not proven |
| tests\multi_position_2\test_dual_lifecycle_worker.py | UNKNOWN | retained; obsolescence not proven |
| tests\multi_position_2\test_lifecycle_slots_postgres.py | UNKNOWN | retained; obsolescence not proven |
| tests\multi_position_2\test_selector_projected_state.py | UNKNOWN | retained; obsolescence not proven |
| tests\operator_control_production_deployment\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_deployment_adapter.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_eligible_approval_continuation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_first_canary_executor_recovery.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_multi_symbol_eligible_approval_ranking.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_mutation_foundation_enablement.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_production_lifecycle_worker.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_runtime_and_binding.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\operator_control_production_deployment\test_runtime_health.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_account_balance_trade_reporting\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_balance_trade_reporting\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_balance_trade_reporting\test_contracts_and_faults.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_balance_trade_reporting\test_reporting_matrix.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_balance_trade_reporting\test_scalping_v2_performance.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_baseline_persistence_schema_extension\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_baseline_persistence_schema_extension\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_baseline_persistence_schema_extension\test_contract_matrix.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_account_baseline_persistence_schema_extension\test_postgres_0012.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\test_event_vocabulary.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\test_migration_0010.py | MIGRATION | schema/migration contract |
| tests\paper_approval_remediation\test_quantity_and_risk_approval.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\test_static_safety_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_approval_remediation\test_strategy_approval.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_backup_pitr_infrastructure_remediation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_pitr_infrastructure_remediation\test_baseline_and_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_pitr_infrastructure_remediation\test_contract_matrices.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_pitr_infrastructure_remediation\test_safe_inspector.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_pitr_infrastructure_remediation\test_storage_readiness_and_domains.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_cli_and_static_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_postgres_pitr_rehearsal.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_postgres_restore_rehearsal.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_reconciliation_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_recovery_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_backup_restore_reconciliation_readiness\test_scope_and_performance.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_close_causal_cursor_remediation\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_close_causal_cursor_remediation\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_close_causal_cursor_remediation\test_boundary_contract_and_simulator.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_close_causal_cursor_remediation\test_cursor_domain_and_bounded_progression.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_close_causal_cursor_remediation\test_mapping_recovery_and_static_guarantees.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_close_causal_cursor_remediation\test_postgres_cursor_and_migration.py | MIGRATION | schema/migration contract |
| tests\paper_command_ingestion_retry\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_command_ingestion_retry\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_command_ingestion_retry\test_postgres_ingestion_service.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_command_ingestion_retry\test_validation_matrix.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_controlled_runtime_canary\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_canary\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_canary\test_contract_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_canary\test_postgres_canary.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_canary\test_service_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_canary\test_static_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\test_configuration_loader_and_symbols.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\test_dry_run_planning.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\test_postgres_readonly.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\test_startup_gate_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_dry_run\test_static_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_sequence_canary\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_sequence_canary\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_sequence_canary\test_contract_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_runtime_sequence_canary\test_postgres_sequence.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\test_classifier_contract_and_authorization.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\test_cycle_stages_resume_and_faults.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\test_postgres_concurrency.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\test_postgres_full_lifecycle.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_controlled_worker_retry\test_static_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_domain\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_domain\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_domain\test_command_and_safety.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_domain\test_order_and_fill.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_domain\test_position_exit_accounting_identity_events.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_exit_evaluation_retry\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_exit_evaluation_retry\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_exit_evaluation_retry\test_evaluator_matrix.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_exit_evaluation_retry\test_net_pnl_protection_service.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_exit_evaluation_retry\test_postgres_service.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_fill_simulator\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_fill_simulator\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_fill_simulator\test_boundary_and_outcomes.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_fill_simulator\test_policy_and_candle_contracts.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_fill_simulator\test_price_fee_identity_determinism.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_first_canary_correlation_readiness_remediation\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_first_canary_correlation_readiness_remediation\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_first_canary_correlation_readiness_remediation\test_contract_matrix_2048.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_first_canary_correlation_readiness_remediation\test_postgres16_correlation.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_operator_bounded_runtime_runner\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_operator_bounded_runtime_runner\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_operator_bounded_runtime_runner\test_contract_and_cli.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_operator_bounded_runtime_runner\test_postgres_runner.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_operator_control_api_disabled_foundation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\test_auth_validation_and_routes.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\test_contract_matrix_1800.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\test_disabled_foundation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\test_faults_performance_evidence.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_operator_control_api_disabled_foundation\test_http_transitions.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_order_execution_service\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_order_execution_service\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_order_execution_service\test_entry_cursor_retry_postgres.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_order_execution_service\test_entry_cursor_retry.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_order_execution_service\test_postgres_service_integration.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_order_execution_service\test_service_contract_and_mapping.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_persistence\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_persistence\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_persistence\test_postgres_constraints.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_persistence\test_pure_mappings.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_plan_execution_outcomes\test_outcome_store.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_production_approval_source_adapter\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_approval_source_adapter\test_adapter_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_kill_switch_emergency_stop\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_kill_switch_emergency_stop\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_kill_switch_emergency_stop\test_concurrency_and_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_kill_switch_emergency_stop\test_control_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_kill_switch_emergency_stop\test_fail_closed_and_atomicity.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_market_data_input_adapter\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_market_data_input_adapter\test_adapter_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_backend_remediation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_backend_remediation\test_adapters_cli_security.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_backend_remediation\test_postgres16_cli_acceptance.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_disabled_wiring\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_disabled_wiring\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_disabled_wiring\test_composition_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_disabled_wiring\test_plans_principal_runtime.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_disabled_wiring\test_stage_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_preparation_resume_remediation\test_privilege_and_phase.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_readiness_review\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_readiness_review\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_readiness_review\test_contract_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_readiness_review\test_migration_and_static_policy.py | MIGRATION | schema/migration contract |
| tests\paper_production_source_contract_remediation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_source_contract_remediation\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_source_contract_remediation\test_frozen_migration.py | MIGRATION | schema/migration contract |
| tests\paper_production_source_contract_remediation\test_identity_and_executor.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_production_source_contract_remediation\test_postgres16_acceptance.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_deployment_postcondition_remediation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_deployment_postcondition_remediation\test_deployment_adapter.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\conftest.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\test_active_position_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\test_api_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\test_explicit_paper_states.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\test_postgres16.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_reporting_api\test_schema_compatibility.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_readonly_schema_preflight_remediation\test_least_privilege_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\paper_repository\__init__.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_repository\conftest.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_repository\test_atomic_lifecycle_and_concurrency.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_repository\test_repository_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\paper_trading_criteria_readonly\test_trading_criteria.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_backup_pitr_controlled_change\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_backup_pitr_controlled_change\test_catalog_retention_and_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_backup_pitr_controlled_change\test_policy_and_gates.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_backup_pitr_controlled_change\test_runtime_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_wal_archive_unresolved_failure_remediation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_wal_archive_unresolved_failure_remediation\test_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_wal_archive_unresolved_failure_remediation\test_isolated_postgres16_transient_retry.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\production_wal_archive_unresolved_failure_remediation\test_operator_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\readonly_production_runtime_observation\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\readonly_production_runtime_observation\test_observation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\research\fixtures\result_search_applicability.json | RESEARCH | research/parameter-sweep scope |
| tests\research\test_chronological_search.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_finding_verifier.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_frozen_funnel.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_historical_execution.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_historical_statistics.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_history_applicability.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_adaptive_refinement.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_all_symbols.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_artifact_v2.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_artifact_writer.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_cli_gui_v2.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_counterfactual_funnel.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_data_driven_ranges.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_dataset_selection.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_dynamic_cold_gui.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_expanded_search.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_finalist_freeze.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_gui_pipeline.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_historical_reconstruction.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_historical_replay.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_holdout_protocol.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_ranking_v2.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_replay_integrity_v2.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_report_semantics.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_separability.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_single_symbol.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_targeted.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_validation_gate_authority.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_validation_ranking.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_parameter_sweep_winners.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_research_opportunity_registry.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_result_search_contract.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_result_search_history.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_scalping_v2_parameter_sweep.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_search_optimizer.py | RESEARCH | research/parameter-sweep scope |
| tests\research\test_search_parameters.py | RESEARCH | research/parameter-sweep scope |
| tests\security_retry\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\security_retry\test_compose_policy_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\security_retry\test_control_and_quarantine_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\security_retry\test_safe_inspection_and_output_matrix.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\fakes.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_analysis_latest_available_repository.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_api_v1.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_boundary_health_policy.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_canary_configuration.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_contract_and_safety.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_dependency_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_dual_schema_capability.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_funnel_epoch_parity.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_funnel_export.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_funnel_lifecycle_traceability.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_i18n.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_persistent_service_configuration.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_runtime_config.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_runtime_entrypoint.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_setups_repository.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_trading_funnel.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\server_api\test_trading_universe_query_budget.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_15m_first_class_domain_remediation.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_5m_scalping_analysis_report_export.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_5m_scalping_calibration_baseline.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_5m_scalping_geometry_quota_cost_remediation.py | LEGACY_V1 | active-v1 fixture rejected by current v2-only runtime |
| tests\test_5m_strategy_cap_forensic_replay.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_5m_strategy_cap_shadow_calibration.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_5m_strategy_target_actionability_shadow_calibration.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_candle_repository.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_continuous_budget_semantics.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_db_constraints_indexes.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_db_models.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_dynamic_rr_calibration_forensic.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_market_data_01_binance_rest_mapping.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_candle_model.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_candle_store.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_gap_detector.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_gap_recovery.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_health.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_market_data_snapshot.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_timeframe.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_01_websocket_kline_mapping.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_alembic_migration.py | MIGRATION | schema/migration contract |
| tests\test_engine_market_data_02_boundary_scheduler.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_db_gap_reconciliation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_db_models.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_multi_timeframe_sync_15m.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_multi_timeframe_sync_1h_4h_1d.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_repository.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_snapshot_from_db.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_timeframe_sync_plan.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_02_warmup.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_backfill_config.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_backfill_planner.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_backfill_runner.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_cli_dry_run.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_closed_candle_policy.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_missing_ranges.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_report.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_03_verifier.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_alembic_version_compatibility.py | MIGRATION | schema/migration contract |
| tests\test_engine_market_data_04_boundary_aware_health.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_boundary_scheduler.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_chunked_recovery.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_cli.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_config.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_contracts.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_daemon_dry_run.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_daemon_once_mode.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_docker_compose_docs.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_downtime_recovery_logic.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_expected_closed_candle.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_failed_boundary_prompt_retry.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_freshness_monitor.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_gap_check_windows.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_health_consumers.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_prod_smoke_closed_only_validation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_prod_smoke_health_schema.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_prod_smoke_report_schema.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_prod_smoke_repository_root.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_prod_smoke_runtime_independence.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_reboot_recovery_logic.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_recovered_pair_health_reset.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_sync_state_model.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_sync_state_repository.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_systemd_docs.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_market_data_04_warmup_planner.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_engine_observation_01_cli.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_config.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_contracts.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_coverage.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_expected_windows.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_funnel.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_integrity.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_latency.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_reason_codes.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_report.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_safety.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observation_01_verdict.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observer_reliability.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_observer_semantic.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_engine_orchestrator_01_cli.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_closed_window_detector.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_config.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_contracts.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_daemon_dry_run.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_daemon_once_mode.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_dedupe.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_docker_compose_docs.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_freshness_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_pipeline_runner_happy_path.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_pipeline_runner_no_action.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_pipeline_runner_reject_path.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_result_models.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_result_store.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_orchestrator_01_safety_counters.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_direction_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_level_builder_bearish.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_level_builder_bullish.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_level_geometry.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_missing_causal_levels.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_planned_rr.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_risk_level_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_risk_preapproved_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_runner.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_safety_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_status_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_store.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_strategy_type_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01_trade_plan_model.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_paper_01b_causal_context_propagation.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_decision_model.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_direction_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_quality_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_required_review_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_research_frequency_limits.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_runner.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_safety_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_score_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_status_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_store.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_engine_risk_01_strategy_type_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_exploration_rollback.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_impulse_calibration_forensic.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_market_data_dependency_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_market_data_image_security_contract.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_negative_empirical_ev_hard_veto_removal.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_persistent_secret_binding_contract.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_postfix_setup_regime_forensic.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_postgres_connection_failure.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_probability_authority_accumulation.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_production_db_credential_rotation.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_readiness_domains.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_readonly_api_credential_rotation_control.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_readonly_api_health_classifier_diagnostic.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_readonly_api_stability_observer.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_recovery_self_healing.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_safe_control_status_inspector.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_safe_docker_inspection.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_safe_wal_ack_inspector.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_scalping_conservative_probability.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_cost_uncertainty_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_dynamic_ev_gate.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_expectancy.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_funnel_envelope.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_independent_profile_v2.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_journal.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_opportunity_cadence_calibration.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_performance_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_probability_fallback_hierarchy.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_profitability_grants_migration.py | MIGRATION | schema/migration contract |
| tests\test_scalping_prospective_collector.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_replay_safety.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_risk_strategy_type_contract.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_rr_dynamic_anchor_forensic.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_shadow_cohorts.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_v1_removed.py | CURRENT_V2 | active/scalping shared contract |
| tests\test_scalping_v2_production_authority.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_security_scanner_path_policy.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\test_set2_runtime_provenance.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_stability_acceptance.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_stability_schedule.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_strategy_edge_geometry_forensic.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_trade_15m_runtime_disabled.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_trade_parameters_config.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_trading_config_manager.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_win32_desktop_automation.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_yaml_authority_adversarial.py | UNKNOWN | retained; obsolescence not proven |
| tests\test_yaml_authority.py | UNKNOWN | retained; obsolescence not proven |
| tests\trading_universe\__init__.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\trading_universe\test_activation_and_canary_lineage.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\trading_universe\test_domain_and_readonly.py | INFRASTRUCTURE | runtime/infrastructure contract |
| tests\trading_universe\test_symbol_preflight.py | INFRASTRUCTURE | runtime/infrastructure contract |

Classification counts: UNKNOWN=74, INFRASTRUCTURE=201, CURRENT_V2=173, LEGACY_V1=3, MIGRATION=9, RESEARCH=37.


# Appendix C — exact generated-cache deletion manifest

The active virtual environment and Git metadata are explicitly excluded.

| Relative path | Files | Bytes | mtime | Action |
|---|---:|---:|---|---|
| alembic\__pycache__ | 1 | 3446 | 2026-09-19T15:13:53.7144992+03:00 | DELETE_PROVEN_SAFE |
| alembic\versions\__pycache__ | 37 | 216356 | 2026-10-03T13:47:49.9717403+03:00 | DELETE_PROVEN_SAFE |
| app\__pycache__ | 1 | 187 | 2026-09-18T22:51:01.4912784+03:00 | DELETE_PROVEN_SAFE |
| app\config\__pycache__ | 5 | 96026 | 2026-09-19T13:46:54.0755494+03:00 | DELETE_PROVEN_SAFE |
| app\db\__pycache__ | 8 | 164860 | 2026-10-03T13:47:49.3211972+03:00 | DELETE_PROVEN_SAFE |
| app\db\repositories\__pycache__ | 8 | 36843 | 2026-09-19T23:57:20.3087955+03:00 | DELETE_PROVEN_SAFE |
| app\desktop_automation\__pycache__ | 2 | 41521 | 2026-09-19T23:57:20.3327986+03:00 | DELETE_PROVEN_SAFE |
| app\engine_analysis\__pycache__ | 42 | 605978 | 2026-09-19T23:57:20.4295432+03:00 | DELETE_PROVEN_SAFE |
| app\engine_execution\__pycache__ | 13 | 99622 | 2026-09-19T23:57:20.4403317+03:00 | DELETE_PROVEN_SAFE |
| app\engine_exit\__pycache__ | 3 | 10218 | 2026-09-19T23:57:20.4493330+03:00 | DELETE_PROVEN_SAFE |
| app\engine_journal\__pycache__ | 2 | 2862 | 2026-09-19T10:53:23.8295244+03:00 | DELETE_PROVEN_SAFE |
| app\engine_market_data\__pycache__ | 34 | 256548 | 2026-09-27T16:13:59.7449969+03:00 | DELETE_PROVEN_SAFE |
| app\engine_market_data\db\__pycache__ | 6 | 26816 | 2026-09-19T23:57:20.4922569+03:00 | DELETE_PROVEN_SAFE |
| app\engine_market_data\db\migrations\__pycache__ | 1 | 244 | 2026-09-19T23:57:20.4859631+03:00 | DELETE_PROVEN_SAFE |
| app\engine_market_data\operational\__pycache__ | 2 | 45011 | 2026-09-19T23:57:20.5443800+03:00 | DELETE_PROVEN_SAFE |
| app\engine_observation\__pycache__ | 24 | 405376 | 2026-09-19T23:57:20.7094027+03:00 | DELETE_PROVEN_SAFE |
| app\engine_observation\semantic\__pycache__ | 10 | 88355 | 2026-09-19T23:57:20.6836734+03:00 | DELETE_PROVEN_SAFE |
| app\engine_orchestrator\__pycache__ | 18 | 226630 | 2026-09-27T11:56:48.2469198+03:00 | DELETE_PROVEN_SAFE |
| app\engine_paper\__pycache__ | 73 | 1854184 | 2026-10-10T09:27:58.8614125+03:00 | DELETE_PROVEN_SAFE |
| app\engine_position\__pycache__ | 16 | 99935 | 2026-09-19T23:57:21.1737014+03:00 | DELETE_PROVEN_SAFE |
| app\engine_risk\__pycache__ | 16 | 73467 | 2026-09-20T14:51:17.6390599+03:00 | DELETE_PROVEN_SAFE |
| app\engine_safety\__pycache__ | 9 | 142511 | 2026-10-03T14:06:34.0956349+03:00 | DELETE_PROVEN_SAFE |
| app\engine_setup\__pycache__ | 14 | 115514 | 2026-10-10T10:35:36.6631894+03:00 | DELETE_PROVEN_SAFE |
| app\engine_strategy\__pycache__ | 13 | 71557 | 2026-09-20T14:51:17.7023858+03:00 | DELETE_PROVEN_SAFE |
| app\i18n\__pycache__ | 5 | 192650 | 2026-10-10T09:30:45.3541387+03:00 | DELETE_PROVEN_SAFE |
| app\instrument_constraints\__pycache__ | 2 | 18246 | 2026-09-20T16:48:40.7913190+03:00 | DELETE_PROVEN_SAFE |
| app\observability\__pycache__ | 5 | 31575 | 2026-09-19T23:57:21.2966201+03:00 | DELETE_PROVEN_SAFE |
| app\operator_control\__pycache__ | 15 | 302963 | 2026-10-03T14:32:55.0359561+03:00 | DELETE_PROVEN_SAFE |
| app\research\__pycache__ | 2 | 1229 | 2026-09-19T23:57:21.3346645+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\__pycache__ | 13 | 333899 | 2026-10-03T14:38:35.5475068+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\errors\__pycache__ | 3 | 7190 | 2026-09-19T14:07:31.7316547+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\mapping\__pycache__ | 2 | 11921 | 2026-09-19T14:04:05.7712440+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\pagination\__pycache__ | 2 | 4653 | 2026-09-19T14:04:09.3655860+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\repositories\__pycache__ | 5 | 129279 | 2026-10-03T14:32:55.1301042+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\routes\__pycache__ | 3 | 21706 | 2026-09-19T14:07:33.4225050+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\schemas\__pycache__ | 4 | 54948 | 2026-10-03T14:32:55.1557215+03:00 | DELETE_PROVEN_SAFE |
| app\server_api\services\__pycache__ | 3 | 82299 | 2026-10-03T14:38:35.4944170+03:00 | DELETE_PROVEN_SAFE |
| app\trading_universe\__pycache__ | 5 | 40070 | 2026-09-20T21:56:33.8227239+03:00 | DELETE_PROVEN_SAFE |
| scripts\__pycache__ | 73 | 1292187 | 2026-10-03T13:49:21.3545015+03:00 | DELETE_PROVEN_SAFE |
| tests\__pycache__ | 528 | 5454722 | 2026-10-31T18:03:37.3099198+03:00 | DELETE_PROVEN_SAFE |
| tests\control_mobile_security\__pycache__ | 12 | 252962 | 2026-10-31T18:03:11.6847132+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_analysis\__pycache__ | 15 | 152562 | 2026-10-31T18:03:11.8732071+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_execution\__pycache__ | 30 | 318020 | 2026-10-31T18:03:12.2492302+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_exit\__pycache__ | 3 | 13521 | 2026-09-30T21:33:07.4820891+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_orchestrator\__pycache__ | 53 | 1386109 | 2026-10-31T18:03:12.9620456+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_paper\__pycache__ | 33 | 691827 | 2026-10-31T18:03:13.8731351+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_position\__pycache__ | 28 | 427992 | 2026-10-31T18:03:14.6663021+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_risk\__pycache__ | 6 | 68462 | 2026-10-31T18:03:14.7485110+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_setup\__pycache__ | 9 | 115459 | 2026-10-31T18:03:14.8762124+03:00 | DELETE_PROVEN_SAFE |
| tests\engine_strategy\__pycache__ | 9 | 138476 | 2026-10-31T18:03:15.0866347+03:00 | DELETE_PROVEN_SAFE |
| tests\final_approval_generation_integration\__pycache__ | 4 | 272770 | 2026-09-21T00:05:04.5978002+03:00 | DELETE_PROVEN_SAFE |
| tests\instrument_quantity_registry\__pycache__ | 4 | 147267 | 2026-09-21T18:35:31.5264207+03:00 | DELETE_PROVEN_SAFE |
| tests\integration\__pycache__ | 6 | 37774 | 2026-10-31T18:03:15.3629244+03:00 | DELETE_PROVEN_SAFE |
| tests\integration\paper_natural_execution_e2e\__pycache__ | 19 | 917133 | 2026-10-31T18:03:15.1736757+03:00 | DELETE_PROVEN_SAFE |
| tests\integration\stale_position_shadow\__pycache__ | 3 | 65117 | 2026-10-31T18:03:15.3014518+03:00 | DELETE_PROVEN_SAFE |
| tests\lineage_identity_remediation\__pycache__ | 3 | 44695 | 2026-10-31T18:03:15.4214460+03:00 | DELETE_PROVEN_SAFE |
| tests\multi_position_2\__pycache__ | 9 | 78475 | 2026-10-31T18:03:15.5250902+03:00 | DELETE_PROVEN_SAFE |
| tests\operator_control_production_deployment\__pycache__ | 25 | 821180 | 2026-10-31T18:03:15.6709338+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_account_balance_trade_reporting\__pycache__ | 13 | 277646 | 2026-10-31T18:03:16.1470448+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_account_baseline_persistence_schema_extension\__pycache__ | 10 | 217278 | 2026-10-31T18:03:16.4630537+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_approval_remediation\__pycache__ | 19 | 313670 | 2026-10-31T18:03:16.7312897+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_backup_pitr_infrastructure_remediation\__pycache__ | 13 | 197448 | 2026-10-31T18:03:17.3243656+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_backup_restore_reconciliation_readiness\__pycache__ | 22 | 444646 | 2026-10-31T18:03:17.8106496+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_close_causal_cursor_remediation\__pycache__ | 16 | 353214 | 2026-10-31T18:03:18.1223931+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_command_ingestion_retry\__pycache__ | 10 | 279367 | 2026-10-31T18:03:18.4029258+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_controlled_runtime_canary\__pycache__ | 16 | 359738 | 2026-10-31T18:03:18.8612546+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_controlled_runtime_dry_run\__pycache__ | 19 | 382368 | 2026-10-31T18:03:19.2103720+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_controlled_runtime_sequence_canary\__pycache__ | 10 | 236080 | 2026-10-31T18:03:19.6279696+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_controlled_worker_retry\__pycache__ | 19 | 575954 | 2026-10-31T18:03:18.7587133+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_domain\__pycache__ | 13 | 452444 | 2026-10-31T18:03:20.0702451+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_exit_evaluation_retry\__pycache__ | 13 | 364364 | 2026-09-27T11:41:31.0991008+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_fill_simulator\__pycache__ | 13 | 372638 | 2026-10-31T18:03:20.5573840+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_first_canary_correlation_readiness_remediation\__pycache__ | 10 | 278484 | 2026-10-03T14:06:41.2145776+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_operator_bounded_runtime_runner\__pycache__ | 10 | 332921 | 2026-10-31T18:03:21.7932375+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_operator_control_api_disabled_foundation\__pycache__ | 19 | 367884 | 2026-10-03T14:06:42.2876557+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_order_execution_service\__pycache__ | 16 | 581289 | 2026-10-31T18:03:22.4087321+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_persistence\__pycache__ | 10 | 239877 | 2026-10-31T18:03:22.6194272+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_plan_execution_outcomes\__pycache__ | 3 | 183137 | 2026-09-27T23:11:05.4443489+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_approval_source_adapter\__pycache__ | 4 | 228270 | 2026-09-21T18:38:28.5419964+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_kill_switch_emergency_stop\__pycache__ | 13 | 296934 | 2026-10-31T18:03:23.3209318+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_market_data_input_adapter\__pycache__ | 4 | 215477 | 2026-09-27T01:57:30.8259410+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_preparation_backend_remediation\__pycache__ | 7 | 307958 | 2026-10-31T18:03:23.6815908+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_preparation_disabled_wiring\__pycache__ | 13 | 326032 | 2026-10-31T18:03:24.4082651+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_preparation_resume_remediation\__pycache__ | 3 | 81034 | 2026-10-31T18:03:24.4765811+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_readiness_review\__pycache__ | 10 | 232727 | 2026-10-31T18:03:24.8203202+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_production_source_contract_remediation\__pycache__ | 13 | 241170 | 2026-10-31T18:03:25.0648548+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_readonly_deployment_postcondition_remediation\__pycache__ | 4 | 93957 | 2026-10-31T18:03:25.1335046+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_readonly_reporting_api\__pycache__ | 19 | 398486 | 2026-10-31T18:03:25.1819653+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_readonly_schema_preflight_remediation\__pycache__ | 3 | 32388 | 2026-10-31T18:03:25.8921685+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_repository\__pycache__ | 10 | 458547 | 2026-10-31T18:03:26.2131556+03:00 | DELETE_PROVEN_SAFE |
| tests\paper_trading_criteria_readonly\__pycache__ | 3 | 43764 | 2026-10-31T18:03:26.2820831+03:00 | DELETE_PROVEN_SAFE |
| tests\production_backup_pitr_controlled_change\__pycache__ | 10 | 151024 | 2026-10-31T18:03:26.6765822+03:00 | DELETE_PROVEN_SAFE |
| tests\production_wal_archive_unresolved_failure_remediation\__pycache__ | 10 | 239395 | 2026-10-31T18:03:27.0126453+03:00 | DELETE_PROVEN_SAFE |
| tests\readonly_production_runtime_observation\__pycache__ | 4 | 193610 | 2026-10-31T18:03:27.1402584+03:00 | DELETE_PROVEN_SAFE |
| tests\research\__pycache__ | 108 | 2767417 | 2026-10-31T18:03:30.5641314+03:00 | DELETE_PROVEN_SAFE |
| tests\security_retry\__pycache__ | 10 | 197196 | 2026-10-31T18:03:30.7701188+03:00 | DELETE_PROVEN_SAFE |
| tests\server_api\__pycache__ | 53 | 1735148 | 2026-10-31T18:03:31.5208503+03:00 | DELETE_PROVEN_SAFE |
| tests\trading_universe\__pycache__ | 10 | 190923 | 2026-09-21T00:05:07.0088626+03:00 | DELETE_PROVEN_SAFE |
| traders_ml\__pycache__ | 1 | 237 | 2026-09-19T10:53:19.1565568+03:00 | DELETE_PROVEN_SAFE |
| traders_ml\parameter_sweep\__pycache__ | 53 | 1356253 | 2026-09-20T16:46:43.5373145+03:00 | DELETE_PROVEN_SAFE |

END_OF_REPORT

