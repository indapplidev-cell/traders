# TRADERS 15m first-class domain execution funnel and architecture forensic audit 01

## Verdict

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_15M_FIRST_CLASS_DOMAIN_EXECUTION_FUNNEL_AND_ARCHITECTURE_FORENSIC_AUDIT_01_COMPLETED
FORENSIC_AUDIT_COMPLETE = YES
15M_FIRST_CLASS_DOMAIN = PARTIAL
15M_FUNNEL_COMPLETE = PARTIAL
15M_EXECUTION_LIFECYCLE_OBSERVABLE = PARTIAL
15M_DESKTOP_FIRST_CLASS = PARTIAL
15M_MOBILE_FIRST_CLASS = PARTIAL
15M_READONLY_FIRST_CLASS = PARTIAL
15M_REASON_PROVENANCE_PRESERVED = PARTIAL
15M_NULL_ZERO_SEMANTICS = PASS
15M_SCALPING_CROSS_PROFILE_CONTAMINATION = 1
REMEDIATION_REQUIRED = YES
PROPOSED_REMEDIATION_TASK = TRADERS_15M_FIRST_CLASS_DOMAIN_EXECUTION_FUNNEL_AND_ARCHITECTURE_REMEDIATION_01
NEXT_ACTION = PREPARE_SEPARATE_BOUNDED_REMEDIATION_FROM_PROVEN_AUDIT_FINDINGS
```

The forensic task passes because the architecture, defects and gaps were proven without changing production. It does not certify 15m as a complete first-class domain.

## Scope, versions and safety

| Item | Proven value |
|---|---|
| Server baseline | `cf05ce3341f44522cbb00426f8ef987226cca70c`, branch `feature/engine-platform` |
| Desktop baseline | `ae7f200c42540e1294fc31afe14b18c334e04d6b`, branch `main` |
| Mobile accepted baseline | `013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db`, branch `main` |
| Production source revision | `d7d072df4b924d675c4bb1de447635f0b6b0e41d` on both orchestrators, Readonly and Control |
| Production Alembic | `0018_promote_5m_production_search`, one head |
| 15m/5m orchestrator image | `sha256:85c36e2c8474954c7e509bc9a91bf33c2759cf8d570d60179932acdc24c44612` |
| Readonly image | `sha256:96ef6773189d69d79a2b68de3e4491ad70a1d6210d7ff316b04fcbffa042fd4d` |
| Control image | `sha256:b7d50beeb5e9286bf2582216dd0d575335e8f0bdf37047e02ce9ffe57d95b80c` |
| Inspection policy | GET-only APIs, allowlisted Docker state fields, read-only source/Git and `BEGIN TRANSACTION READ ONLY` SQL |
| Prohibited effects | no POST, restart, schema/parameter/policy change, deployment, order, LIVE or Binance order API call |

Mobile had pre-existing modified and untracked profile/funnel work before the audit. It was preserved byte-for-byte and is not treated as an accepted production baseline. Server and Desktop were clean before the audit.

## Runtime health and continuity

At baseline, 15m and 5m orchestrators were running with restart count 0; Readonly was healthy/restart 0; Control was semantically `ARMED`, generation 6, but its Docker health state later read `unhealthy` while the Readonly readiness projection still reported `paper_control_health=HEALTHY`. PostgreSQL was healthy/restart 0. Both orchestrators continued producing exact profile-specific cycles throughout the audit.

The scalping collector was already unhealthy. During the audit it restarted autonomously from count 131 to 134; no task command restarted it. Its current `health.json` was `FAILED`, `owner_active=false`, singleton owner count 0, records 8620, boundaries 630, errors 1. The observation segment remained `scalping-calibration-segment-d8a498357af94ae584b3b691`. Both mixed-lineage exclusions, `1787936400000` and `1788090000000`, remain append-only with `calibration_eligible=false` and `raw_records_mutated=false`.

## 15m identity, universe and closed-candle proof

```text
trade_profile_id = trade-15m-v1
trade_mode = TRADE_15M
profile_mode = PRODUCTION_SEARCH
primary_timeframe = 15m
entry_timeframes = [15m]
context_timeframes = [1h,4h]
trigger_timeframe = 15m
universe_id = trading-universe-v2
universe_count = 10
universe = BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,LINKUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,SUIUSDT
selection_policy_version = eligible-approval-ranking-v1
```

The most recent 96 persisted 15m boundaries contained 960 rows: every boundary had exactly 10 rows and 10 distinct symbols, with zero `future_bars_used`. Current boundary `1788110100000` and previous boundary `1788109200000` were both exact10 with no missing or duplicate symbol. Readonly reported `CURRENT`, exact expected windows of 4 completed 15m boundaries in 1h and 16 in 4h.

## Domain ownership and execution map

| Stage | Owning production authority | 15m state | Persistence/observation |
|---|---|---|---|
| Market Data | `engine_market_data` candle repository/snapshot | implemented, closed-candle-only | snapshot identity persists; active universe reports 59/60 streams because BTC has 5/6 |
| Analysis | `engine_analysis` via orchestrator | implemented | payload and reason provenance persist |
| Setup | `engine_setup` | implemented | setup id and causal opportunity id persist |
| Strategy | `engine_strategy` | implemented | decision, score, type, reasons persist |
| Geometry | `engine_paper.PaperLevelBuilder` | implemented for successful plan construction | rejected attempted derived geometry is discarded |
| Target | causal setup/risk context then `PaperLevelBuilder` | causal | successful source persists; rejected source/derived target not exposed end-to-end |
| Costs | only diagnostic `gate_enabled=false` in legacy 15m path | not an admission gate | no authoritative 15m net-cost pass |
| RR | `PaperLevelBuilder` gross reward/risk | implemented, floor 1.5 | successful RR persists; rejected computed RR is discarded |
| Risk | `engine_risk.RiskPolicy` | implemented research preapproval | not account exposure risk; quota is in-memory reservation |
| Portfolio | runtime parameters and `FutureCrossProfileArbiter` exist | not wired into production 15m admission | no independent persisted portfolio decision |
| Final Approval | `NaturalFinalApprovalMaterializer` | implemented for ready plans | immutable triplet persists with one-boundary validity |
| PAPER Plan | `engine_paper.PaperRunner` | implemented | plan-ready fields persist; rejection lacks attempted math |
| Entry eligibility/selector | production approval adapter + `ProductionEligibleApprovalSelector` | implemented | deterministic classification/ranking persists or is projected |
| Order/Fill/Position/Closed Trade | shared controlled PAPER execution domain | implemented but unused in current production history | tables and 13 GET routes exist; all current counts are zero |

The production 15m pipeline is therefore real and separately identified, but it is not the complete requested first-class domain: cost and portfolio admission are absent, rejected economics are not durable, and the canonical downstream view is disabled for 15m.

## Funnel, counting and windows

The legacy 15m stage counts use the unit `SYMBOL` consistently: Analysis, Structural Setup, Strategy Eligible, Risk Approved, PAPER Trade Plan, Quantity Approved, Validity Approved, Final Approval, Eligible and Selector Winner. Zero means the stage is applicable and no symbol passed. Null is reserved for the canonical 12-stage projection that source explicitly sets to `NOT_APPLICABLE` for any non-5m profile.

Current observed 15m cycle at audit time: 10 analysis, 6 setup, 5 strategy, 5 research-risk preapprovals, 0 plan, 0 quantity, 0 validity, 0 final approval, 0 eligible, 0 winner. Previous: 10, 5, 4, 4, then zero. Rolling 1h: 40 analysis, 17 setup, 10 strategy/risk, then zero. Rolling 4h: 160 analysis, 55 setup, 11 strategy/risk, then zero. These values changed naturally between GETs as a new closed boundary arrived; no task mutation caused the change.

Canonical downstream order is present in the DTO:

`ANALYSIS_QUALIFIED -> STRUCTURAL_SETUP -> STRATEGY_ADMITTED -> RISK_COMPATIBILITY_ADMITTED -> GEOMETRY_VALID -> TARGET_VALID -> NET_COST_PASS -> RR_PASS -> RISK_ADMITTED -> PORTFOLIO_ADMITTED -> FINAL_APPROVAL -> PAPER_PLAN`.

For 15m, every canonical downstream count and dominant rejection is null and every trace is `NOT_APPLICABLE`; for 5m these fields are populated. This is an explicit source branch in `app/server_api/trading_funnel.py`, not absence of current candidates.

## Per-symbol visibility, reasons and identity

The 15m symbol row exposes symbol, run/setup candidate id, direction, deepest legacy stage, status, source/terminal reason, eligibility, rank, winner, market watermark, approval validity and timestamps. It does not expose the causal `opportunity_id`, successful/rejected target/stop source, attempted rejected geometry, or canonical downstream details. For 15m, `profile_market`, `profile_analysis` and `profile_scenario` are empty/unavailable in this funnel projection.

The 24h export was paged using GET-only JSONL records: 960 rows over 96 exact10 boundaries, profile `trade-15m-v1` only in that export, zero future leakage. First terminal/rejection distribution was dominated by `NO_STRUCTURAL_SETUP`/`PAPER_NO_PLAN_SOURCE_NO_DECISION`, then source strategy rejections, seven waits, five missing-causal-level rejections and one low-planned-RR rejection. Raw payloads preserve analysis/setup/strategy/risk/PAPER reason arrays and causal inputs, but the friendly first-rejection projection can label an affirmative analysis reason; reason provenance is therefore partial rather than fully normalized.

`opportunity_id` is durable in setup/risk/PAPER causal context, while Readonly uses setup `candidate_id` and omits opportunity id for 15m. A successful plan can be reconstructed through run -> analysis -> setup -> strategy -> risk -> plan -> final approvals in PostgreSQL, but a rejected candidate cannot be reconstructed end-to-end from Readonly/export alone.

## Target, stop, costs and RR forensic samples

Natural rejected AVAX sample, run `orchestrator:1b155c3151de455aa42a0afe2706ebc3`, boundary `1788109200000`:

```text
entry = confirmation_close = 7.447
causal invalidation/support = 7.389
ATR/volatility buffer = 0.02671428571428588
derived stop = 7.389 - 0.02671428571428588 = 7.36228571428571412
causal target = 7.471
target provenance = 15m / schwager_resistance_zone / validated / future_safe / still_relevant
risk distance = 0.08471428571428588
reward distance = 0.024
recomputed gross RR = 0.283305227655985955...
minimum RR = 1.5
decision = PAPER_REJECT_LOW_PLANNED_RR
```

The stop uses a causal invalidation plus ATR/volatility buffer. `default_stop_buffer_pct=0.001` is only a fallback and `allow_fallback_stop=false`; `allow_fallback_target=false`, so no silent synthetic target was used. The rejection payload retains causal primitives in `paper_context` but sets derived entry/stop/target/RR and source fields to null because `PaperLevelError` is raised before `PaperLevels` is returned.

Natural accepted historical samples prove formula consistency:

| Sample | Stored geometry | Recomputed RR | Stored RR | Result |
|---|---|---:|---:|---|
| SOLUSDT `1787963400000` | 104.42 / 103.63428571428571 / 105.72 | 1.65454545 | 1.65454545 | PASS |
| SUIUSDT `1787206500000` | 0.6994 / 0.70495 / 0.6905 | 1.60360360 | 1.6036036 | PASS |

The 15m decision uses gross RR only. A diagnostic cost floor is computed with fee 10 bps/fill, adverse slippage 2 bps/fill and safety margin, but `gate_enabled=false`; authoritative spread/depth and net RR do not gate legacy 15m admission.

## Quantity, validity, risk, portfolio and selector

Quantity policy is controlled PAPER authority v1: paper equity × 1% / absolute entry-stop risk, capped by cash balance and instrument maximum, then floored to Binance quantity step and validated against min/max quantity/notional. It does not use leverage.

```text
SOL equity = 100 USDT
risk budget = 1 USDT
risk/unit = 0.78571428571429
raw quantity = 1.27272727272726...
cash cap = 100 / 104.42 = 0.95767094426355...
step = 0.001
recomputed normalized quantity = 0.95700000
stored approved quantity = 0.95700000

SUI risk/unit = 0.00555
raw quantity = 180.180180...
cash cap = 142.979696...
step = 0.1
recomputed normalized quantity = 142.90000000
stored approved quantity = 142.90000000
```

Validity ends at the next profile trigger boundary minus 1 ms and is bounded by the strictest strategy/quantity/risk approval. SOL source boundary `1787963400000` had `valid_until_ms=1787964299999`.

Risk policy allows only `ALLOW_RESEARCH_TRADE_PLAN`, allowed strategy types, minimum strategy score 65, required risk review, no future/executable source, and `LOW` risk; medium is denied. Research quotas are 20/symbol/day, 50 total/day and 30/direction/day. They are process-memory counters keyed by profile/day and reserve at research preapproval before PAPER plan success; there is no release or durable account-exposure accounting. This is not a portfolio gate.

The separate `FutureCrossProfileArbiter` and portfolio runtime parameters are currently only future/test/collector constructs, not invoked in the production 15m approval path. Production selector policy `eligible-approval-ranking-v1` is deterministic: risk score desc, RR desc, strategy score desc, newest close, then stable run/final-approval/candidate/symbol identity.

## PAPER execution and persistence

PostgreSQL counts at audit time: commands 0, orders 0, fills 0, positions 0, exits 0, journal 0, order events 0. Two canary records exist; current canary waits for an eligible approval with command/open-position budgets 1/1. PAPER account baseline is 100 USDT, balance 100, PnL/fees/trades/open positions all zero, and reconciliation is healthy.

Plan and execution semantics are distinct: plan readiness does not mean order/fill/position. The shared execution lifecycle is implemented and regression-tested, but current natural production has no row to correlate, and the 15m funnel exposes `UNAVAILABLE/NOT_OPENED` rather than a joined lifecycle. Classification is therefore `PARTIAL`, not `NO`.

## Readonly, Desktop and Mobile

Source route inventory is 28 GET and 0 POST/PUT/PATCH/DELETE: 15 core GET plus 13 PAPER GET. There is no per-symbol HTTP fan-out in the funnel; server query-budget tests passed. `/markets` and `/analysis` are exact10 aggregate endpoints but accept no profile parameter, so their identity is implicitly legacy/latest rather than first-class profile-scoped.

Desktop accepts both profile ids, validates identity/window semantics and renders canonical details. For 15m, however, server downstream/economics values are N/A, so Desktop cannot be first-class end-to-end. Accepted Mobile HEAD is explicitly 15m-only, uses the parameter-free funnel GET, supports only legacy counts/trace and three scores, and lacks profile identity/canonical downstream/economics. Current uncommitted Mobile work passed tests but is not accepted evidence.

| Capability | Readonly | Desktop | Mobile accepted HEAD |
|---|---|---|---|
| explicit 15m profile identity | yes in funnel | yes | no |
| exact10 current/previous/1h/4h | yes | yes | yes legacy |
| canonical 12 stages | schema only; N/A for 15m | renders N/A | absent |
| target/stop/cost/RR/sizing provenance | absent for current 15m rows | unavailable | absent |
| order/fill/position/trade | separate PAPER GET, current empty | separate views | separate legacy read-only views |
| profile-aware Market/Analysis | no query parameter | 5m via funnel contexts, 15m legacy routes | no |

## 15m versus Scalping and cross-profile isolation

Profiles have distinct ids, triggers, contexts, expected windows and persisted run/result fields. Current cycles show no live cross-profile projection mix. Nevertheless, a 7-day SQL identity audit found exactly one persisted mismatch:

```text
run_id = orchestrator:845788b878834a769887c100a5e27d48
symbol = BTCUSDT
boundary = 1787936400000
run trade_profile_id = trade-5m-v1
result trade_profile_id = trade-15m-v1
```

This is the previously documented mixed-runtime-lineage incident. It remains quarantined in the collector manifest and excluded from calibration, but it is still a factual persisted cross-profile contamination count of 1. A second excluded mixed boundary `1788090000000` is also preserved; it did not add another run/result profile-id mismatch under the SQL predicate.

## WAL/PITR, Control and security

Readonly readiness after audit: WAL ready true, PITR ready true, lineage valid, physical gap false, contiguous lineage from `2026-08-11T07:54:19.615Z`; the safe ACK inspector reported owner PID 27564 healthy with backlog/pending zero. Control projection was `ARMED`, generation 6, but mutation-ready false with fail-closed denial reasons; LIVE remained false. Docker reported the Control container unhealthy, a runtime discrepancy requiring operations follow-up outside this read-only audit.

No secret-bearing environment, raw container configuration, credential, archive path or token was printed. No task call reached Binance order APIs. Production mutations, parameter promotions, DB writes, service restarts and behavior changes by this task are all zero.

## Natural tests

```text
SERVER_TESTS = PASS_1941
DESKTOP_HEADLESS_TESTS = PASS_62_PLUS_17_SUBTESTS
DESKTOP_GUI_TESTS = ENVIRONMENT_BLOCKED_2_TCL_TK_INITIALIZATION_FAILURES_NO_PRODUCT_ASSERTION
MOBILE_TESTS = PASS_220_ON_PREEXISTING_DIRTY_WORKTREE
READONLY_TESTS = PASS_INCLUDED_SERVER_SUITE
I18N_TESTS = PASS_STATIC_SERVER_AND_DESKTOP_HEADLESS_GUI_ENVIRONMENT_BLOCKED
SECURITY_TESTS = PASS_INCLUDED_SERVER_SUITE
```

The first server attempt used the repository `.venv` without FastAPI and failed collection; the canonical `.task-env-control-0017` rerun passed 1941. The GUI failures are host Tcl/Tk packaging failures and do not change the product verdict.

## Required findings table

| ID | Layer | Finding | Severity | Evidence | Behavior impact | Observability impact | Remediation needed |
|---|---|---|---|---|---|---|---|
| F-001 | Domain/Readonly | canonical 12-stage 15m funnel is hard-coded N/A | High | source branch plus live null counts | no decision change | hides true stage attrition | yes |
| F-002 | Economics | 15m cost diagnostic has `gate_enabled=false`; RR is gross only | High | pipeline source and accepted samples | admission can ignore net costs | no net RR/edge | yes |
| F-003 | Portfolio | no active production portfolio/cross-profile exposure gate | High | arbiter has no production caller | no account-level exposure admission | portfolio status unavailable | yes |
| F-004 | Persistence | rejected derived entry/stop/target/RR/source are discarded | High | AVAX natural rejection | rejection outcome correct, forensic replay incomplete | UI/export cannot reproduce rejection directly | yes |
| F-005 | Risk | research quota is in-memory and reserved before plan success with no release | Medium | risk limits source and AVAX context counters | process-local quota pressure can outlive rejected idea until restart/day | not account exposure | yes |
| F-006 | Readonly | 15m row omits opportunity and target/stop/economic provenance | High | live funnel and export | none | candidate not end-to-end reconstructable | yes |
| F-007 | Readonly | Market/Analysis aggregate routes lack profile parameter | Medium | route inventory | latest legacy projection can be mistaken for explicit profile | profile identity implicit | yes |
| F-008 | Persistence/isolation | one 5m run has a 15m result profile id | High | read-only 7d SQL | quarantined from calibration but durable mismatch remains | mixed-lineage incident visible only in audit/manifest | yes |
| F-009 | Desktop | client supports schema but receives N/A 15m downstream | Medium | Desktop models/UI plus live DTO | none | first-class 15m details unavailable | yes after server |
| F-010 | Mobile | accepted HEAD is legacy 15m-only and lacks first-class profile/downstream model | High | `git show HEAD` models/repository/UI | none | parity incomplete | yes |
| F-011 | Operations | collector failed/restart storm and Control Docker health unhealthy during audit | High | restart counts, health file, Docker state | no task-induced behavior; background reliability risk | readiness sources disagree | separate ops action |

## Gap counts and classification

```text
DOMAIN_DEFECT_COUNT = 4
PERSISTENCE_GAP_COUNT = 2
READONLY_GAP_COUNT = 3
DESKTOP_GAP_COUNT = 1
MOBILE_GAP_COUNT = 2
UX_GAP_COUNT = 3
LEGACY_DEBT_COUNT = 4

15M_TARGET_CAUSAL = YES
15M_TARGET_SOURCE_OBSERVABLE = NO
15M_STOP_CAUSAL = YES
15M_STOP_SOURCE_OBSERVABLE = NO
15M_RR_RECOMPUTE_MATCH = PASS
15M_QUANTITY_RECOMPUTE_MATCH = PASS
15M_PORTFOLIO_GATE = NO
15M_PORTFOLIO_OBSERVABILITY = NO
15M_OPPORTUNITY_IDENTITY = PARTIAL
15M_SINGLE_CANDIDATE_END_TO_END_RECONSTRUCTABLE = PARTIAL
READONLY_N_PLUS_ONE = NO
```

## Remediation proposal

Do not repair in this audit. A separate bounded, repair-first task should:

1. persist a profile-neutral canonical 15m stage trace and rejected attempted economics without changing decisions;
2. expose opportunity, geometry, target/stop provenance, cost/RR, sizing, validity and lifecycle through additive Readonly fields, then consume them in Desktop/Mobile;
3. decide and prove an active 15m net-cost gate and portfolio authority only from separately authorized requirements—no algorithm redesign or silent Scalping backport;
4. make risk quota semantics durable or explicitly release rejected reservations;
5. repair/prevent run/result profile identity mismatches while preserving incident records;
6. preserve production continuity and validate exact10, profile isolation and natural PAPER behavior before any acceptance.

## Git and evidence resolution

```text
SERVER_PROJECT_STATE_COMMIT_RESOLUTION = git log -1 --format=%H -- docs/audits/TRADERS_15M_FIRST_CLASS_DOMAIN_EXECUTION_FUNNEL_AND_ARCHITECTURE_FORENSIC_AUDIT_01_FINAL.md
EVIDENCE_FILE = D:\disk_E\game_projects\traders\evidence_inbox\TRADERS_15M_FIRST_CLASS_DOMAIN_EXECUTION_FUNNEL_AND_ARCHITECTURE_FORENSIC_AUDIT_01_FINAL.md
EVIDENCE_SHA256_RESOLUTION = Get-FileHash -Algorithm SHA256 <EVIDENCE_FILE>
PUSHED = NO
```
