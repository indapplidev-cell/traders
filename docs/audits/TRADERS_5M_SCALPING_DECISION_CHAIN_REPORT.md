# TRADERS 5m scalping decision-chain report

Task: `TRADERS_5M_SCALPING_DECISION_CHAIN_TARGET_STRATEGY_AND_ECONOMICS_REMEDIATION_01`

## Production baseline used by this task

The current homogeneous predeploy snapshot is 2026-08-24T21:50:00Z through
2026-08-25T11:30:00Z. It supersedes the older 170-setup/4-admit snapshot for
task decisions.

```text
PRODUCTION_ALEMBIC_HEAD = 0018_promote_5m_production_search
5M_PARAMETER_SET_ID_BEFORE = trade-5m-v1-runtime-v1-c141aece87c7f6a0
5M_RUNTIME_SOURCE_COMMIT_BEFORE = 6650f5f13e03342613518584633c90b020e945ed
5M_RUNTIME_ARTIFACT_ID_BEFORE = sha256:b3928a801238a21032fa53e1d34fde02a6036e902b41d23182a05aea5e00bee8
5M_SINGLETON_OWNER_COUNT_BEFORE = 1
WAL_READY_BEFORE = true
PITR_READY_BEFORE = true
CONTROL_STATE_BEFORE = ARMED
CONTROL_GENERATION_BEFORE = 6
LIVE_STATE_BEFORE = DISABLED
BOUNDARIES = 165
EVALUATIONS = 1650
PARAMETER_HOMOGENEOUS = YES
EXACT10 = YES
MISSING_BOUNDARIES = 0
DUPLICATE_BOUNDARIES = 0
```

| module | decision | key inputs | authoritative threshold/policy | pass | reject | top reason | suspected issue |
|---|---|---|---|---:|---:|---|---|
| market data | closed-only snapshots | persisted 5m/15m/1h/4h candles | profile minimum windows, no future/unclosed candle | 1650 | 0 | none | none |
| analysis | regime, confidence, impulse, entry quality | closed 5m primary snapshot | 5m runtime windows in parameter set | 1650 | 0 | none | no threshold bottleneck proved |
| setup | structural candidate and direction | analysis plus causal levels | setup causal policy v1 | 235 | 1415 | `NO_STRUCTURAL_SETUP` 1412 | market mostly had no structural trigger; no null score defect |
| strategy | research-plan admission | setup quality/components/context | minimum quality `ACCEPTABLE`, numeric boundary 65 | 7 | 228 | weak 194; conflict 34 | weak score tier cap creates a large boundary cohort; calibrate only in SHADOW |
| geometry | causal stop and target evidence | risk context, ATR, causal levels | ATR .25; stop envelope 80 bps, reject not clip | 4 | 3 | causal stop too wide 3 | no stop mutation required |
| target actionability | causal target becomes trade target only if economic | ordered causal levels plus mandatory costs | cost floor + 1 bps positive edge + gross/net RR 1.5 | 0 | 4 | target not economically actionable | previous runtime stopped at the 3.0383 bps local level and never considered another tier |
| cost | fail-closed net economics | fee, slippage, spread, depth, margin | all seven cost components mandatory | 0 | 4 | old code: negative net edge | current median total cost 27.9831 bps |
| risk | preapproval and downstream shared authority | strategy decision and profile counter | separate research counters; shared account authority | 0 | 0 | not reached monotonically | no leak |
| paper plan | immutable plan | valid geometry/actionable target/cost/risk | production min RR 1.5 | 0 | 0 | not reached | correct NO_PLAN outcome |
| final approval/execution/position | bounded PAPER lifecycle | valid unexpired plan and existing authorities | existing global authority and Control | 0 | 0 | not reached | unchanged |
| exit | stop/target/validity/time/invalidation | persisted OPEN position and closed candles | existing profile-aware exit evaluator | 0 | 0 | no positions | source and isolated tests only; no policy change |

## Module contracts

| module | INPUTS | AUTHORITATIVE_CONFIG | PROFILE_SPECIFIC_PARAMETERS | DECISION_OUTPUT | REJECTION_CODES | PERSISTED_DIAGNOSTICS | NEXT_STAGE_CONTRACT |
|---|---|---|---|---|---|---|---|
| `engine_market_data` | public closed candles | snapshot boundary contract | minimum window map | `MarketDataSnapshot` | gap/freshness/not-enough-data | counts, source, first/last close, gaps | analysis receives one closed primary snapshot |
| `engine_analysis` | primary snapshot | `AnalysisConfig` | 24 ATR, 12 impulse, 48 structure, 72 regime, 36 volume | `AnalysisSnapshot` | degraded/invalid/error reasons | regime, confidence, impulse, entry quality, causal context | setup receives non-actionable analysis evidence |
| `engine_setup` | analysis snapshot | causal setup detector | `engine-setup-01-causal-v1` | `SetupCandidate` | no setup, invalidation, confirmation waits | type, direction, quality score/components, causal levels | strategy consumes one setup candidate |
| `engine_strategy` | setup plus quality diagnostics | `StrategyConfig` | threshold 65/ACCEPTABLE; policy `engine-strategy-01-shadow-v1` | `StrategyDecision` | weak, conflict, hard invalidation, neutral, unsupported | raw/component/penalty/final/threshold/margin; diagnostic-only deltas | only production ALLOW reaches risk |
| `engine_risk` | strategy decision | risk policy v1 | separate 5m research key; minimum score 65 | `RiskDecision` | quality, score, exposure/quota | attempt counts, no execution reservation | preapproved research candidate reaches geometry |
| `engine_paper` | risk decision and causal primitives | 5m scalping runner | ATR .25, stop 80 bps, min positive edge 1 bps, RR 1.5 | ready plan or NO_PLAN/REJECT | missing invalidation/target/cost; stop wide; target non-actionable | complete stop/target consideration/cost/net metrics/opportunity id | only valid plan may enter approval authority |
| `engine_execution` | final approval | immutable PAPER command policy | none changed | command/order | existing fail-safe codes | command lineage | position service |
| `engine_position` | fills/orders | existing PAPER domain | none changed | OPEN/CLOSING/CLOSED | existing state-machine codes | position/journal lineage | exit evaluator |
| `engine_exit` | OPEN position and closed candles | existing exit policy | existing timeframe-aware validity | exit decision | stop/target/time/validity/invalidation | causal exit boundary | fill/accounting |
| orchestrator/profile | closed boundary and symbols | explicit registry lookup | `trade-5m-v1-runtime-v1-4e257e4cff2a5b9a` after | persisted per-module payloads | module error/freshness | parameter id on every payload | readonly export |
| readonly export | persisted run/results | allowlisted GET-only schema | explicit profile required | canonical Funnel record | safe raw reason codes | all task diagnostics | offline audit only |

```text
5M_SILENT_FALLBACK_TO_15M = NO
5M_SILENT_FALLBACK_TO_DEFAULT = NO
```

`resolve_runtime_parameters()` indexes the exact profile and fails on a missing
or mismatched identity. The pipeline chooses `ScalpingPaperRunner` only for
`trade-5m-v1`; the 15m runner and its parameter identity remain unchanged.

## Analysis and setup findings

`regime` is a market-state description, not a trade direction. `UP` can coexist
with direction `UNKNOWN/NONE` when no confirmed structural setup establishes a
directional hypothesis. LONG/SHORT appears only after setup evidence yields a
`BULLISH/BEARISH` direction and strategy/risk preserve it. Confidence is a
0..1 contemporaneous evidence value. In setup scoring it contributes at most
15 context points; strategy's existing diagnostic adjustment is `(confidence -
0.5) * 4`, bounded by the setup quality tier. No analysis threshold was changed.

For all 235 structural setup records, persisted `quality_score` and
`source_confidence` were non-null (`0/235` null for each). The setup score is
the actual sum of structure, confirmation and context less conflict/invalidation
penalties, capped by source analysis entry quality. The data supports a market
without a trigger in 1412/1650 evaluations, not a parser/DTO null defect.

## Strategy decomposition

```text
STRATEGY_WEAK_QUALITY_COUNT = 194
STRATEGY_CONFLICTING_CONTEXT_COUNT = 34
WEAK_QUALITY_SCORE_MIN = 64.466
WEAK_QUALITY_SCORE_P50 = 64.999
WEAK_QUALITY_SCORE_P90 = 64.999
WEAK_QUALITY_MARGIN_TO_THRESHOLD_P50 = -0.001
WEAK_QUALITY_MARGIN_TO_THRESHOLD_P90 = -0.001
CONFLICTING_CONTEXT_COMPONENTS = LOW_CONFIDENCE:34
SHADOW_DELTA_MINUS_0_10_COUNT = 146
SHADOW_DELTA_MINUS_0_25_COUNT = 155
SHADOW_DELTA_MINUS_0_50_COUNT = 185
PRODUCTION_THRESHOLD_CHANGED = NO
```

The narrow margin is largely a semantic tier cap (`WEAK <= 64.999`), so count
alone is not evidence for promotion. New rows persist the actual structure,
candle-confirmation and context-alignment components, penalties, raw/final
score, threshold and margin. Breakout strength, volume, liquidity, volatility,
entry location and shadow/exhaustion are not falsely synthesized as independent
numeric components where the existing Strategy model has no such score.

## Target, stop and economics

The remediation separates `causal_target_exists` from
`economically_actionable_target_exists`. It inspects only the nearest favorable,
validated, future-safe target in each tier: LOCAL_5M, STRUCTURAL, HIGHER_TF. A
farther target from the same tier is deliberately ignored so RR cannot be
manufactured. Every considered target records its distance, actionability,
reason and next tier.

```text
minimum_actionable_target_bps = entry_fee + exit_fee + entry_slippage
                              + exit_slippage + spread + depth_impact
                              + safety_margin + minimum_positive_edge_bps
minimum_positive_edge_bps = 1.0 (explicit 5m diagnostic/economic profile value)
production_min_rr = 1.5 (unchanged)
```

The stop remains causal invalidation plus the profile ATR buffer. It is never
clipped toward entry. ATR `.25/.50/.75/1.00`, stop `50/65/80` bps and RR
`1.0/1.2/1.5` remain SHADOW cohorts. Missing spread or depth fails closed and
never becomes zero. If net reward is non-positive, net RR and break-even win
rate remain null.

## Same-data replay

| semantics | analyses | setups | strategy admits | unique opportunities | geometry | actionable targets | cost pass | risk/plans/final | stop P50/P90 bps | target P50/P90 bps | gross RR P50 | net RR P50 | edge P50 bps | BE win rate P50 |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---:|---:|---:|---:|
| A current production evidence | 1650 | 235 | 7 | 2 | 4 | 0 | 0 | 0/0/0 | 70.5451/257.218 | 3.0383/3.0383 | .0433 | null | -24.9448 | null |
| B target-actionability remediation | 1650 | 235 | 7 | 2 | 4 | 0 | 0 | 0/0/0 | 70.5451/257.218 | 3.0383/3.0383 | .0433 | null | -24.9448 | null |
| C bounded Strategy diagnostic cohorts | 1650 | 235 | 146/155/185 diagnostic hits | not promoted | not evaluated | not evaluated | not evaluated | 0/0/0 | null | null | null | null | null | null |
| D combined remediation + Strategy cohort | 1650 | 235 | diagnostic only | not promoted | not evaluated | not evaluated | not evaluated | 0/0/0 | null | null | null | null | null | null |

B converts all four prior negative-edge rows from a cost-style reject into the
causally correct `TARGET_NOT_ECONOMICALLY_ACTIONABLE` NO_PLAN and preserves the
3.0383 bps local level as evidence. No distinct structural/higher-TF level was
present in these four persisted candidates, so fallback counts are zero. C/D
fail closed downstream: rejected setup records did not have authoritative
market cost/geometry generated, and the task does not invent it. No
configuration is selected by signal count.

## Opportunity, quota, validity and exit

The runtime now persists a stable `opportunity_id` over symbol, direction,
setup identity, causal invalidation and causal target identities; adjacent
boundary candidate IDs remain distinct while the opportunity ID remains the
same. The homogeneous report groups only contiguous equal identities and found
7 raw candidates, 2 unique opportunities and 5 repeats (71.4286%).

Execution quota remains downstream of a valid plan. The sample has reservation
leaks 0, NO_PLAN quota consumption 0 and cross-profile contamination 0.
Validity remains one profile boundary: setup creation, decision boundary and
plan/final-approval deadline are persisted; no expired plan or approval exists.
The exit policy was source-audited and isolated-tested only because there are
no closed 5m PAPER outcomes.

## Performance and safety contract

Snapshot building remains four bounded DB reads per symbol with no new N+1.
Cost acquisition remains zero calls before valid geometry and at most two
public market-data calls afterward (book ticker plus depth limit 100). The
target hierarchy is bounded to three tiers. There is no private/order API
dependency.

Postdeploy six-boundary latency, exact10/concurrency, WAL/PITR and final runtime
fields are recorded in the task final report after the natural-window gate.

## Safety incident affecting the task verdict

A predeploy metadata diagnostic used an unrestricted container-inspection
format and emitted the complete container environment into the tool transcript,
including a production database credential. The credential value is not copied
into this report, source, evidence artifacts or Git. Subsequent inspection used
only the project allowlisted safe inspector, and repository security scanners
pass. Nevertheless, this violates the task's no-secret-exposure condition.
Rotation/rebind would affect shared database clients and may require protected
runtime restarts, so it is outside this task's 5m-only authority. The technical
decision-chain remediation can be accepted as implemented, but the overall task
cannot receive PASS until separately authorized credential rotation and
invalidation are proven.
