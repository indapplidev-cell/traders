# Scalping v2 causal stop geometry — Task B

```text
TASK_STATUS = PASS
FINAL_VERDICT = STOP_TOO_WIDE_BY_MARKET_STRUCTURE
ANCHOR = 1788961200000
COHORT_COUNT = 723
STOP_DISTANCE_BPS = min 3.7399 / p25 20.0029 / median 33.6303 / p75 53.8569 / max 219.1353
STOP_EFFICIENCY_MEDIAN = 0.9999999894
STOP_TOO_WIDE = 204
NO_CAUSAL_INVALIDATION = 0
INVALID_GEOMETRY = 75
OTHER = 444
STOP_SELECTOR_SUBOPTIMAL = NO
STOP_SOFTWARE_DEFECT = NO
PRODUCTION_CHANGE_REQUIRED = NO
NEXT_TASK = TASK_C_CAUSAL_TARGET_SELECTION
```

The selected stop is the nearest directionally valid confirmed structural
invalidation plus the unchanged 0.25 x 5m ATR buffer. For 710 rows with a full
candidate inventory, the median nearest/selected efficiency is effectively
1.0; the minimum 0.9999185 difference is conservative price normalization, not
a material selector widening. Ordering, LONG/SHORT sign, ATR price units to bps,
5m timeframe provenance, and deterministic selection pass regression review.

Median observed MAE is 0.513 of selected stop distance, while the upper quartile
exceeds 1.0. This does not license a fixed or hindsight-tightened stop: 204
decisions exceed the 50 bps envelope because the nearest causal market
invalidation itself is too far away.
