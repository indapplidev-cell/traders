# ENGINE-TREND-23 Top Candidates Post-mortem

## MAIN_SELECTED_ENTRY: `ET-HED-0001`

`ET-HED-0001` ranked first because the additive score rewarded causal/structural clarity (86.0/86.0), level quality (88.3), conflict absence (88.0), technical agreement (82.0) and RR quality (100.0). The outcome was not used in ranking, so selection remained causal.

Known pre-entry warnings were a weak confirmation volume ratio of **0.678**, a stop only **0.676 ATR** away, a target **3.774 ATR** away, RR **5.586**, and ADX **41.07**, which can describe mature rather than early trend strength. Bollinger extension was **not present under the declared 0.25 ATR diagnostic**. The score had no explicit volume component and converted RR into a monotonic bonus capped at 100; it therefore rewarded reward/risk geometry without estimating target-hit probability.

The trade reached MFE **1.454R**, then hit SL in **3 bars**. This is not proof of an obvious invalid setup: structure, level, and candle authorization were causal. It is better classified as a statistically normal loss with identifiable probability/geometry warnings (weak volume and asymmetric stop/target distances). Filters such as minimum volume or minimum stop-in-ATR could have excluded it causally, but their cutoffs are hindsight-selected and remain `DIAGNOSTIC_HYPOTHESIS_ONLY`. One loss is not a basis for changing scoring: **NO**.

## Frozen top 10

| ID | Symbol | Setup | Dir | Entry UTC | RR | Score | Outcome | Net | Why ranked high | Why won/lost | Common risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ET-HED-0001 | BTCUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-12-01T13:30:00Z | 5.586 | 85.178 | SL_BEFORE_TP | -0.50% | rr_quality=100.0, level_quality=88.3, conflict_absence=88.0 | SL first in 3 bars after MFE 1.45R (26.0% of target distance). | stop 0.68 ATR; volume ratio 0.68; high/late ADX 41.1 |
| ET-HED-0002 | BTCUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-10-30T07:00:00Z | 8.558 | 83.912 | SL_BEFORE_TP | -0.49% | rr_quality=100.0, level_quality=88.5, conflict_absence=88.0 | SL first in 1 bars after MFE 0.47R (5.5% of target distance). | stop 0.53 ATR; target 4.50 ATR; volume ratio 0.57 |
| ET-HED-0003 | SOLUSDT | LONG_UP_CONTINUATION_RETEST | LONG | 2025-11-15T18:45:00Z | 4.096 | 83.597 | SL_BEFORE_TP | -0.58% | rr_quality=93.9, conflict_absence=88.0, level_quality=87.9 | SL first in 1 bars after MFE 0.12R (3.0% of target distance). | stop 0.65 ATR; volume ratio 0.40 |
| ET-HED-0004 | SOLUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-07-12T00:15:00Z | 4.037 | 83.336 | SL_BEFORE_TP | -0.73% | rr_quality=93.1, level_quality=89.2, conflict_absence=88.0 | SL first in 4 bars after MFE 1.20R (29.8% of target distance). | volume ratio 0.48 |
| ET-HED-0005 | BTCUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-07-30T21:15:00Z | 4.738 | 83.310 | SL_BEFORE_TP | -0.48% | rr_quality=100.0, conflict_absence=88.0, causal_context_strength=86.0 | SL first in 4 bars after MFE 0.54R (11.3% of target distance). | volume ratio 0.15 |
| ET-HED-0006 | BTCUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-10-10T23:15:00Z | 8.196 | 83.194 | SL_BEFORE_TP | -1.43% | rr_quality=100.0, conflict_absence=88.0, causal_context_strength=86.0 | SL first in 2 bars after MFE 0.17R (2.1% of target distance). | stop 0.70 ATR; target 5.71 ATR; volume ratio 0.53; high/late ADX 67.0 |
| ET-HED-0007 | SOLUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-10-16T11:00:00Z | 8.029 | 83.159 | SL_BEFORE_TP | -0.84% | rr_quality=100.0, conflict_absence=88.0, level_quality=86.4 | SL first in 1 bars after MFE 0.21R (2.7% of target distance). | stop 0.74 ATR; target 5.91 ATR; volume ratio 0.55 |
| ET-HED-0008 | SOLUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-10-22T02:30:00Z | 4.383 | 83.132 | TP_BEFORE_SL | 1.28% | rr_quality=98.2, conflict_absence=88.0, level_quality=86.3 | TP first in 12 bars; MAE 0.00R. | stop 0.51 ATR; volume ratio 0.74; high/late ADX 45.7 |
| ET-HED-0009 | BTCUSDT | SHORT_DOWN_CONTINUATION_RETEST | SHORT | 2025-10-14T11:45:00Z | 3.624 | 83.053 | TP_BEFORE_SL | 0.95% | conflict_absence=88.0, rr_quality=86.9, level_quality=86.3 | TP first in 8 bars; MAE 0.53R. | high/late ADX 51.7 |
| ET-HED-0010 | BTCUSDT | LONG_UP_CONTINUATION_RETEST | LONG | 2025-08-31T05:00:00Z | 3.279 | 83.042 | SL_BEFORE_TP | -0.40% | conflict_absence=88.0, causal_context_strength=86.0, structure_clarity=86.0 | SL first in 1 bars after MFE 0.00R (0.0% of target distance). | no selected diagnostic flag |

Top-10 aggregate: 2 TP, 8 SL, clean winrate **20.00%**, expectancy **-0.32%**, PF **0.4107**. The common ranking pattern is high structure/level/conflict scores plus monotonic RR credit; the common loss pattern is that those attributes do not directly estimate target reachability before a tight structural stop.
