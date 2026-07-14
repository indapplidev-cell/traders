# ENGINE-TREND-23 Performance Audit of Historical Setup Candidates

## Executive decision

Final status: **PERFORMANCE_AUDIT_COMPLETED_NEGATIVE_EXPECTANCY**. All **449** historical candidates were analyzed; integrity is **PASS**. Clean outcomes contain 143 wins and 301 losses, with winrate **32.21%**. Across **446** available returns (clean outcomes plus two separately identified expiry marks), expectancy is **-0.19%** and profit factor is **0.5567**; clean-binary expectancy alone is **-0.21%**. This is a candidate-label performance audit, not a production backtest. The system is **not validated profitable**, and runtime must not change from this in-sample audit.

The negative aggregate expectancy comes from a low hit rate that the realized payoff does not compensate for after 24 bps round-trip costs. Causal structure/level detection answers “is this setup narratively and temporally valid?” but the score does not estimate “will target be reached before stop?” RR is rewarded monotonically even when it is created by a narrow stop or remote structural target, while volume, stop/target reachability, trend maturity, and outer-band extension are absent or weakly represented.

## 1. Integrity and scope

All eight required source artifacts are present. JSON/CSV counts match, IDs are unique, all RR values are at least 1.5, key numeric fields are finite, every clean outcome has net return, `AMBIGUOUS_INTRACANDLE` is excluded from clean win/loss metrics, `NEITHER_EXPIRED` is separate, and `ET-HED-0001` is present. Distribution: symbols `{"BTCUSDT": 152, "ETHUSDT": 153, "SOLUSDT": 144}`, setup types `{"LONG_UP_CONTINUATION_RETEST": 160, "RANGE_MEAN_REVERSION_CANDIDATE": 93, "SHORT_DOWN_CONTINUATION_RETEST": 196}`, directions `{"LONG": 211, "SHORT": 238}`, outcomes `{"AMBIGUOUS_INTRACANDLE": 3, "NEITHER_EXPIRED": 2, "SL_BEFORE_TP": 301, "TP_BEFORE_SL": 143}`.

## 2. Aggregate performance

- Total / clean / available returns: **449 / 444 / 446**; ambiguous **3**; expired **2**. Expired setups are never counted as wins/losses but their 96-bar mark is included in return aggregates, matching the archived preliminary estimate.
- Average gross / net / median net: **0.05% / -0.19% / -0.48%**.
- Naive sum / final additive 1-unit equity / max drawdown: **-84.52% / 0.1548 / 87.48%**.
- Average winner / loser / payoff ratio: **0.69% / -0.63% / 1.0935**.
- Maximum chronological win/loss streak: **6 / 13**.

The additive curve is deliberately naive: candidates may overlap in time and across correlated symbols, so it is not portfolio equity.

### Monthly clean performance

| Month | Candidates | Winrate | Avg net | PF |
| --- | --- | --- | --- | --- |
| 2025-07 | 70 | 34.29% | -0.11% | 0.7228 |
| 2025-08 | 108 | 33.96% | -0.13% | 0.6888 |
| 2025-09 | 69 | 33.82% | -0.23% | 0.3770 |
| 2025-10 | 80 | 26.92% | -0.30% | 0.4068 |
| 2025-11 | 77 | 31.17% | -0.19% | 0.5825 |
| 2025-12 | 45 | 33.33% | -0.21% | 0.5020 |

## 3. By symbol

| Symbol | N | Winrate | Avg net | PF | Avg RR | Best | Worst |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BTCUSDT | 152 | 28.00% | -0.24% | 0.3277 | 2.3955 | ET-HED-0220 | ET-HED-0006 |
| ETHUSDT | 153 | 39.47% | -0.09% | 0.7686 | 2.2728 | ET-HED-0203 | ET-HED-0403 |
| SOLUSDT | 144 | 28.87% | -0.24% | 0.5511 | 2.4954 | ET-HED-0044 | ET-HED-0253 |

Symbol differences are descriptive only; choosing the best pair after seeing these outcomes would be hindsight selection. Detailed outcome/setup/month distributions are embedded in `ENGINE_TREND_23_PERFORMANCE_BY_SYMBOL.csv`.

## 4. By setup type

| Setup | N | Winrate | Avg net | PF | Avg RR | MFE % | MAE % | Bars | Audit disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LONG_UP_CONTINUATION_RETEST | 160 | 29.75% | -0.25% | 0.4219 | 2.1466 | 0.5281 | 0.4253 | 6.3101 | REJECT_CURRENT_FORM_PENDING_REDESIGN |
| RANGE_MEAN_REVERSION_CANDIDATE | 93 | 36.96% | -0.13% | 0.6735 | 2.4139 | 0.6137 | 0.4612 | 6.1196 | REDESIGN_AND_OOS_VALIDATE |
| SHORT_DOWN_CONTINUATION_RETEST | 196 | 31.96% | -0.17% | 0.6143 | 2.5665 | 0.6178 | 0.5026 | 8.0979 | REDESIGN_AND_OOS_VALIDATE |

“Keep” here means retain as a research candidate, never deploy. False continuation patterns concentrate around weak volume, tight stops/remote targets, mature corrections and choppy context; range failures include directional-ADX conflict and breakout-transition risk. Explicit average realized return is the average net column. Target provenance is available: continuations use the pre-confirmation impulse extreme; ranges use the confirmed range midline. More semantic fields such as explicit trend age, polarity flip, trap/failure, reclaim/failure and structural pivot breach are not stored and are `NOT_AVAILABLE` rather than inferred.

## 5. By direction

| Direction | N | Winrate | Avg net | PF | Payoff |
| --- | --- | --- | --- | --- | --- |
| LONG | 211 | 30.29% | -0.25% | 0.4309 | 0.9883 |
| SHORT | 238 | 33.90% | -0.14% | 0.6709 | 1.1722 |

Direction-by-symbol and monthly direction metrics are preserved in the summary JSON. Differences do not justify a directional runtime filter without OOS validation.

## 6. Quality score audit

Quality correlation with net return is **-0.0082** and with the clean win label is **-0.0538**. Winner/loser mean scores are **78.6170 / 78.8526**. Top-10 winrate is **20.00%** versus bottom-10 **30.00%**. Status: **NOT_PREDICTIVE**.

| Score component | Winner mean | Loser mean | Winner-minus-loser |
| --- | --- | --- | --- |
| causal_context_strength | 83.0406 | 83.0705 | -0.0299 |
| structure_clarity | 83.0406 | 83.0705 | -0.0299 |
| level_quality | 83.6142 | 83.8436 | -0.2294 |
| confirmation_candle_quality | 71.9811 | 71.6361 | 0.3451 |
| rr_quality | 66.2483 | 68.4018 | -2.1535 |
| conflict_absence | 86.5734 | 86.8439 | -0.2704 |
| technical_agreement | 76.6573 | 76.7508 | -0.0935 |
| freshness | 73.1748 | 71.6412 | 1.5336 |

High score does not predict profit in this sample. The score double-counts the same structure input as both causal context and structure clarity (33% combined weight), gives monotonically increasing RR credit (13%), and omits explicit volume and stop/target reachability terms. ADX contributes a step-like technical score for continuation candidates and can reward lagging trend confirmation.

## 7. RR and stop/target audit

RR correlation with net return / win label is **0.0038 / -0.1019**. For RR >=5, the false-setup rate is **100.00%**, expectancy **-0.81%**, PF **0.0000**. Bucket details are in `ENGINE_TREND_23_RR_AUDIT.csv`.

The evidence does not show that high planned RR improves expectancy. RR is geometry, not probability: target distance equals RR times stop distance. In this generator, narrow buffered structural stops and pre-existing swing/range objectives can manufacture attractive ratios while increasing early stop and target-unreachability risk.

Outcome path: winner MFE/MAE averages **3.0579R / 0.3769R**; loser MFE/MAE **0.6839R / 1.5762R**. **77** losers first reached at least 1R MFE; **49** winners endured at least 0.5R MAE; **148** losses and **39** wins resolved within three bars; **25** losers reached at least 80% of target distance before SL. Partial profit, break-even, trailing stop or shorter expiry are therefore research hypotheses only, not recommendations to change execution.

## 8. Pre-entry feature diagnostics

| Feature | Available | Winner mean | Loser mean | Corr net | Corr win |
| --- | --- | --- | --- | --- | --- |
| confidence | 10 | 0.6036 | 0.3836 | 0.4158 | 0.3832 |
| quality_score | 444 | 78.6170 | 78.8526 | -0.0082 | -0.0538 |
| planned_rr | 444 | 2.2499 | 2.4499 | 0.0038 | -0.1019 |
| adx14 | 444 | 27.8895 | 27.4715 | 0.0243 | 0.0183 |
| rsi14 | 444 | 49.1302 | 49.3536 | -0.0139 | -0.0128 |
| distance_to_level_atr | 352 | 0.2831 | 0.2579 | 0.1127 | 0.0623 |
| stop_distance_pct | 444 | 0.4210 | 0.3925 | 0.0354 | 0.0611 |
| stop_distance_atr | 444 | 0.9356 | 0.9133 | -0.0378 | 0.0434 |
| target_distance_pct | 444 | 0.9316 | 0.9548 | 0.0286 | -0.0150 |
| target_distance_atr | 444 | 2.0416 | 2.1331 | -0.0012 | -0.0651 |
| volume_ratio_20 | 444 | 0.7844 | 0.7271 | 0.0673 | 0.0667 |
| body_atr | 444 | 0.3774 | 0.3829 | -0.0513 | -0.0146 |
| close_location | 444 | 0.4488 | 0.4886 | -0.0649 | -0.0502 |

Confidence is available only where the prior discovery replay enriched candidates (top-10), so it cannot support a dataset-wide conclusion. ADX, RSI, MACD/EMA alignment, VWAP/Bollinger position, volume, ATR regime, vote count and conflicts are bucketed in the summary JSON. Any apparent bucket edge is exploratory and multiple-testing-prone. The stored “book” evidence with broadest coverage is causal structure classification plus objective/level construction and candle anatomy; no single stored book reason establishes robust separation without OOS testing.

Direct answers to the technical questions: high ADX did **not** rescue expectancy (ADX >=35: winrate **31.96%**, expectancy **-0.18%**), so it may be lagging but that causal interpretation is unproven. RSI midline 45-55 was less negative than adjacent 35-45 and 55-65 buckets, while extreme buckets contain too few observations to trust. Outer-band extension had only **3** candidates and cannot support a robust filter. Volume ratio >=1.5 was the only volume bucket with positive aggregate expectancy (**0.04%**, N=26), whereas volume <0.5 was materially negative; this is a useful hypothesis, not validation. MACD-aligned candidates were less negative than conflicts (**-0.10%** versus **-0.25%**), but remained unprofitable. EMA/VWAP alignment did not consistently help, which is compatible with late-entry behavior.

Altunina availability: HH/HL or LH/LL classification, confirmed pivots, impulse-extreme time, correction bars and retest extreme are available for continuations; explicit impulse-strength, correction-depth, trend-age and pivot-breach fields are not. Schwager availability: causal zone/distance/objective or range support/resistance/midline/width/touches/slope are available; explicit polarity flip, breakout/trap, reclaim/failure fields are not. Nison availability: close location, body-in-ATR, wick fractions, OHLC and interpretation are available; a separate candle-volume-confirmation flag and context-rejection taxonomy are not. The summary includes deterministic correction-age, level-distance, range-touch/width, body and rejection-wick buckets. The most repeatable stored winner association is MACD alignment/zero-conflict plus stronger volume, but it is neither uniquely “book-based” nor OOS-validated.

## 9. Timing diagnostics

Hourly UTC, exclusive sessions (Asia 00-07, Europe 07-13, overlap 13-16, US 16-24), weekday, month, and early/mid/late-month tables are in the summary JSON. These are diagnostics only. The sample covers less than six months; time filters are especially likely to encode temporary regime and must not be productionized.

## 10. Failure clustering

Primary buckets are assigned once per non-winner with deterministic precedence; they are explanatory tags, not ground truth causes.

| Bucket | N | Avg net | Setup distribution | Examples |
| --- | --- | --- | --- | --- |
| TOO_TIGHT_STOP | 64 | -0.52% | {"LONG_UP_CONTINUATION_RETEST": 25, "RANGE_MEAN_REVERSION_CANDIDATE": 12, "SHORT_DOWN_CONTINUATION_RETEST": 27} | ET-HED-0001;ET-HED-0002;ET-HED-0003;ET-HED-0006;ET-HED-0007 |
| TARGET_TOO_FAR | 2 | 1.29% | {"SHORT_DOWN_CONTINUATION_RETEST": 2} | ET-HED-0024;ET-HED-0117 |
| LATE_ENTRY_AFTER_EXHAUSTION | 57 | -0.70% | {"LONG_UP_CONTINUATION_RETEST": 30, "SHORT_DOWN_CONTINUATION_RETEST": 27} | ET-HED-0004;ET-HED-0005;ET-HED-0018;ET-HED-0022;ET-HED-0033 |
| WEAK_CONFIRMATION_VOLUME | 90 | -0.62% | {"LONG_UP_CONTINUATION_RETEST": 31, "RANGE_MEAN_REVERSION_CANDIDATE": 13, "SHORT_DOWN_CONTINUATION_RETEST": 46} | ET-HED-0011;ET-HED-0016;ET-HED-0027;ET-HED-0034;ET-HED-0039 |
| BOLLINGER_EXTENSION_RISK | 2 | -1.10% | {"LONG_UP_CONTINUATION_RETEST": 1, "SHORT_DOWN_CONTINUATION_RETEST": 1} | ET-HED-0151;ET-HED-0335 |
| RANGE_CONFLICT_IGNORED | 12 | -0.72% | {"RANGE_MEAN_REVERSION_CANDIDATE": 12} | ET-HED-0032;ET-HED-0077;ET-HED-0150;ET-HED-0188;ET-HED-0197 |
| CHOPPY_SIDEWAYS_CONTEXT | 22 | -0.66% | {"LONG_UP_CONTINUATION_RETEST": 10, "SHORT_DOWN_CONTINUATION_RETEST": 12} | ET-HED-0042;ET-HED-0068;ET-HED-0138;ET-HED-0141;ET-HED-0159 |
| TREND_TOO_OLD | 4 | 0.40% | {"LONG_UP_CONTINUATION_RETEST": 1, "SHORT_DOWN_CONTINUATION_RETEST": 3} | ET-HED-0019;ET-HED-0069;ET-HED-0106;ET-HED-0270 |
| RETEST_TOO_SHALLOW | 7 | -0.71% | {"LONG_UP_CONTINUATION_RETEST": 5, "SHORT_DOWN_CONTINUATION_RETEST": 2} | ET-HED-0021;ET-HED-0045;ET-HED-0070;ET-HED-0083;ET-HED-0087 |
| RETEST_TOO_DEEP | 3 | -0.76% | {"SHORT_DOWN_CONTINUATION_RETEST": 3} | ET-HED-0012;ET-HED-0275;ET-HED-0375 |
| LOW_RR_DESPITE_PASS | 21 | -0.62% | {"LONG_UP_CONTINUATION_RETEST": 5, "RANGE_MEAN_REVERSION_CANDIDATE": 13, "SHORT_DOWN_CONTINUATION_RETEST": 3} | ET-HED-0048;ET-HED-0086;ET-HED-0097;ET-HED-0131;ET-HED-0149 |
| OTHER | 22 | -0.65% | {"LONG_UP_CONTINUATION_RETEST": 5, "RANGE_MEAN_REVERSION_CANDIDATE": 9, "SHORT_DOWN_CONTINUATION_RETEST": 8} | ET-HED-0010;ET-HED-0013;ET-HED-0035;ET-HED-0054;ET-HED-0073 |

## 11. MAIN and top-10 post-mortem

`ET-HED-0001` was causal but combined weak volume, a 0.68-ATR stop, a 3.77-ATR target and monotonic RR credit; it made 1.45R before SL at bar 3. This is a normal statistical loss with pre-entry warning signs, not sufficient evidence to rewrite score logic. Full MAIN and frozen top-10 detail is in `ENGINE_TREND_23_TOP_CANDIDATES_POSTMORTEM.md`.

## 12. Overfit control and ML readiness

All 8 filter ablations are labeled `DIAGNOSTIC_HYPOTHESIS_ONLY`; each reports remaining candidates, clean winrate, expectancy, PF, overfit risk and mandatory OOT validation. Dataset ML readiness is **PARTIAL**: useful for a small leakage-audited baseline with chronological grouped/embargoed splits, insufficient for production validation. Remove all outcome-path and return fields, future horizons, IDs/ranks and hindsight-derived buckets.

## 13. Recommendations

### A. Keep

- Keep the causal boundary, closed-candle confirmation, unique IDs, explicit ambiguous/expired labels, cost-aware returns, and immutable pre-entry ranking freeze.
- Keep all setup families only as research candidates where their subgroup metrics are not completely degenerate; none is approved for trading.
- Keep normalized pre-entry structure, level, candle, volume and distance features for OOS research.

### B. Redesign

- Redesign `quality_score` as a calibrated probability-oriented research score; remove duplicated structure credit and test volume, stop/target ATR reachability, Bollinger extension, trend maturity and range conflict.
- Audit RR weighting, stop buffer, objective/target selection and expiry separately; do not optimize them jointly on this period.
- Add explicit causal fields for trend age, polarity/reclaim, breakout trap, pivot breach and context conflict before an ML dataset is frozen.

### C. Reject / Block

- Block high-RR ranking as the main selector, indicator-only/time filters, any in-sample-selected combination, and production trading based on these candidates.
- Do not claim profitability: **NO**. Do not change runtime now: **NO**.

## Decision

Next stage is required: **YES**—ENGINE-TREND-24 scoring redesign/failure analysis with locked hypotheses, more historical coverage, and chronological walk-forward/OOS validation. Runtime, trading runtime, thresholds, composer and setup contracts remain unchanged; no commit is created by this script.
