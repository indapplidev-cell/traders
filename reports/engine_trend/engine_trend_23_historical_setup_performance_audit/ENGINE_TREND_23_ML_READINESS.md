# ENGINE-TREND-23 ML Meta-filter Readiness

## Status: PARTIAL

There are **449** rows and **444** clean binary labels (143 TP / 301 SL). This is enough for a constrained exploratory baseline, but insufficient for a credible high-dimensional production meta-filter: observations are clustered across three correlated crypto pairs and nearby market periods, and only about five and a half months are covered. There are **26** entry timestamps shared by multiple candidates, further reducing effective independence.

Usable pre-entry features include symbol, setup type, direction, planned RR, score components, stop/target distances normalized by price or ATR, ADX, RSI, EMA/MACD alignment, VWAP/Bollinger position, volume ratio, candle anatomy, causal level distance, correction bars/touch counts, and technical conflict/vote counts. `AMBIGUOUS_INTRACANDLE` and `NEITHER_EXPIRED` should be excluded from the first binary model or modeled separately.

Leakage exclusions are mandatory: outcome/label, all 24/48/96 horizon objects, MFE/MAE, bars-to-TP/SL/outcome, gross/net return, any failure bucket that uses realized path, post-entry prices, and any filter/feature definition chosen after inspecting this period. Candidate ID/rank should also be removed; `quality_score` may be retained only as a benchmark because it deterministically aggregates other features and can dominate them.

Use a chronological, embargoed split—not random rows. A reasonable research design is expanding-window folds by time, grouping equal/nearby timestamps across all symbols in the same fold, with the final contiguous month held untouched as out-of-time validation. Because the available period is short, the preferred next step is to collect additional non-overlapping months before treating that holdout as decisive. Class weighting or calibrated probabilities may address the **67.8%** loss class; do not oversample across time boundaries.

Label mechanics are deterministic and integrity is **PASS**, but same-candle ambiguity and a fixed 96-bar horizon constrain label quality. Final answer: **ML-ready now: PARTIAL**—suitable for leakage-audited exploratory baselines, not production selection.
