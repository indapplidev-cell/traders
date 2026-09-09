# Scalping v2 impulse scale — Task A final

TASK_STATUS = PASS
FINAL_VERDICT = CURRENT_THRESHOLD_TOO_RARE_FOR_5M
ANCHOR = 1788977100000 / 2026-09-09T18:05:00Z / trade-5m-v2 / scalping-v2-set-2 / config 1d0afbb4d1fb2cfb8afba03f718c28796a47e23b9d17c1f6e0109ace3d3717e7 / deployed a115cbcd5c7d796ccd9a0962b5d8296df617b0ae / schema 0031_scalping_parameter_sets
V3_COHORT_COUNT = 2722
MOVE_PCT_MEDIAN = 0.651338
MOVE_PCT_P90 = 1.2430532
MOVE_PCT_P95 = 1.5295891
MOVE_PCT_P99 = 2.14232
ATR_PCT_MEDIAN = 0.22518
ATR_PCT_P90 = 0.4234898
CURRENT_THRESHOLD_REACH_COUNT = 5
CURRENT_THRESHOLD_REACH_RATE = 0.183688%
ABSOLUTE_3_PERCENT_DOMINANT_COUNT = 2722
ATR_COMPONENT_DOMINANT_COUNT = 0
CONFIRMED_IMPULSE_COUNT = 5
BEST_MOVE_INTENSITY_BANDS = 1.00–1.50% diagnostic only: n=405, candidates=279, scoreable=19, win=47.37%, expectancy=-0.146985R, PF=0.581208
WORST_MOVE_INTENSITY_BANDS = 1.50–2.00% scoreable sample n=1, expectancy=-0.822741R; lower bands are also negative
HIGHER_INTENSITY_IMPROVES_EDGE = NO_NOT_MONOTONIC_AND_NO_POSITIVE_FULL_SAMPLE_EDGE
ENTRY_EXHAUSTION_FOUND = YES_HIGH_INTENSITY_ENTERED_N218_MEDIAN_MOVE_ALREADY_COMPLETED91.2794BPS_VS_REMAINING_MFE18.1546BPS
ROOT_FINDING = ABSOLUTE_3_PERCENT_FLOOR_IS_OUTSIDE_NORMAL_5M_SCALE_AND_DOMINATES_100_PERCENT_OF_ROWS
PRODUCTION_CHANGE_REQUIRED = NO_TASK_A_RESEARCH_ONLY
NEXT_TASK = TASK_B_THRESHOLD_PROVENANCE

## Frozen evidence and causality

The primary evidence is the exact decision-anchored v3 segment only. The
frozen file contains 2,722 unique result/observation identities through the
latest exact-ten completed 5m boundary. Its identity SHA-256 is
`1d0fac07bcd3c3ae1ce6f203e5f5b09c5e96558424d744958fd0ee325d083258`.
The joined v3 outcomes contain 1,182 expired and 229 entered opportunities;
entered rows using a candle opened before decision time are zero. Legacy v2
outcomes are excluded.

PostgreSQL read-only corroboration returned 10 rows / 10 symbols for the
anchor, all `trade-5m-v2`, Set #2, and the exact config hash above.

## Market-scale results

| Move threshold | Reach count | Rate |
|---:|---:|---:|
| 0.25% | 2624 | 96.400% |
| 0.50% | 1878 | 68.993% |
| 0.75% | 1081 | 39.713% |
| 1.00% | 549 | 20.169% |
| 1.50% | 144 | 5.290% |
| 2.00% | 35 | 1.286% |
| 2.50% | 18 | 0.661% |
| 3.00% | 5 | 0.184% |

ATR-normalized reach is 100.000% at 1.0 ATR, 99.963% at 1.5 ATR,
93.350% at 2.0 ATR, 68.883% at 2.5 ATR and 42.285% at 3.0 ATR. The observed
move/ATR ratio median is 2.84150, p90 3.99025 and p95 4.27782. Nevertheless,
the effective detector selects the 3% branch in every row because ATR p90 is
only 0.42349%; the ATR term never dominates.

## Causal quality by intensity

The complete numeric per-symbol distributions and both required band tables
are stored in `artifacts/scalping_v2_impulse_calibration_01/TASK_A_REPORT.json`.
All scoreable absolute bands have negative full-sample expectancy. The apparent
improvement at 1.00–1.50% reverses at 1.50–2.00%, while 2.00–3.00% and >=3.00%
have no scoreable candidate economics. ATR bands are likewise negative:
1.5–2.0 ATR is -0.521725R, 2.0–2.5 ATR is -0.347168R, and >=2.5 ATR is
-0.388517R. Thus stronger intensity is not monotonically associated with edge.

For high-intensity entered rows, 91.2794 bps was already completed before the
entry decision versus only 18.1546 bps median remaining favorable excursion;
median post-entry adverse excursion is 14.2547 bps. This is direct exhaustion
evidence, but not authority to lower a threshold.

Safety: PAPER only, production policy unchanged, LIVE disabled, real Binance
order calls zero, no production deploy.
