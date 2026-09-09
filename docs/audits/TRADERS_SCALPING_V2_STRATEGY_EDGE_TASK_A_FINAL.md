# Scalping v2 strategy edge — Task A

```text
TASK_STATUS = PASS
FINAL_VERDICT = EDGE_DECOMPOSED_CAUSAL_SAMPLE_LIMITED_NO_POSITIVE_SUBGROUP
ANCHOR = 1788961200000 / completed 2026-09-09T13:40:35.058840Z / trade-5m-v2 / scalping-v2-set-2 / config 1d0afbb4d1fb2cfb8afba03f718c28796a47e23b9d17c1f6e0109ace3d3717e7 / deployed 6e8e91547d9ed7005cc8132fe22bd30e87a21a04 / schema 0031_scalping_parameter_sets
COHORT_COUNT = 723 exact causally reconstructable decision snapshots; 396 scoreable causal outcomes
BEST_EDGE_GROUPS = SOLUSDT -0.504R PF0.012 n58; BNBUSDT -0.522R PF0.020 n47; DOGEUSDT -0.525R PF0.071 n39
WORST_EDGE_GROUPS = AVAXUSDT -0.647R PF0.002 n31; SUIUSDT -0.618R PF0.128 n25; LINKUSDT -0.616R PF0.034 n27
POSITIVE_EDGE_GROUP_COUNT = 0
NEGATIVE_EDGE_GROUP_COUNT = 19
INSUFFICIENT_SAMPLE_GROUP_COUNT = 4
EDGE_CONCENTRATION_FOUND = NO
DOMINANT_NEGATIVE_EDGE_SOURCE = AVAXUSDT, but loss is broad rather than concentrated
PRODUCTION_CHANGE_REQUIRED = NO
NEXT_TASK = TASK_B_CAUSAL_STOP_GEOMETRY
```

The cohort is frozen by exact candidate/opportunity/cycle/set/config identity in
`STRATEGY_EDGE_COHORT.jsonl`. It begins at the Set #2 activation cutoff because
24 hours of homogeneous history do not yet exist. No future candle participates
in setup, stop, target, or variant selection. Outcomes are joined only after the
decision through the persisted causal opportunity identity.

All meaningful scoreable subgroups are negative. SHORT is worse than LONG in
the Dynamic-RR subset (-0.53R vs -0.42R), but neither side is positive. Regime
is persisted as UNKNOWN throughout the available sample, so regime separation
is not yet identifiable. The only setup with meaningful outcomes is
`SCALP_MOMENTUM_CONTINUATION`; compression break is insufficient-sample.

