# TRADERS_SCALPING_V2_DYNAMIC_RR_ACHIEVABILITY_TASK_B_FINAL

```text
TASK_STATUS = PASS
FINAL_VERDICT = DYNAMIC_RR_SYSTEMATICALLY_UNACHIEVABLE_FOR_CURRENT_SET2_CAUSAL_GEOMETRY

ANCHOR = 1788954600000 / 2026-09-09T11:50:24.518994Z / deployed 6e8e91547d9ed7005cc8132fe22bd30e87a21a04 / schema 0031
COHORT_COUNT = 49 over bounded 12h
RR_PASS_COUNT = 0
RR_FAIL_COUNT = 49

NET_RR_MEDIAN = 0.75015612
DYNAMIC_REQUIRED_RR_MEDIAN = 4.1101042744
FINAL_REQUIRED_RR_MEDIAN = 4.1101042744
DELTA_MEDIAN = -3.0430145950
ACHIEVABILITY_RATIO_MEDIAN = 0.1955433911

STRUCTURALLY_UNACHIEVABLE_COUNT = 49
MARGINALLY_ACHIEVABLE_COUNT = 0
ACHIEVABLE_COUNT = 0

DOMINANT_DRIVER = LOW_CONSERVATIVE_PWIN_RELATIVE_TO_CAUSAL_NET_RR_GEOMETRY
PWIN_REQUIRED_FOR_MEDIAN_GEOMETRY = 0.5881812783
ECONOMIC_FEASIBILITY_VERDICT = current Set #2 geometry is not compatible with positive-EV admission at measured win probability; the dynamic gate is correctly rejecting it

PRODUCTION_CHANGE_REQUIRED = NO; threshold weakening is not justified
NEXT_TASK = TASK_C_BOUNDED_OFFLINE_POLICY_CANDIDATES
```

## Distribution and causal envelope

```text
NET_RR = min0.60337 p250.68084 median0.75016 p750.88683 max1.76099
DYNAMIC_REQUIRED_RR = min3.42192 p253.59713 median4.11010 p754.18940 max6.60072
DELTA = min-5.75778 p25-3.38538 median-3.04301 p75-2.87396 max-1.83614
ACHIEVABILITY_RATIO_BINS = <0.25:39; 0.25-0.50:10; all other bins:0
BEST_CAUSAL_NET_RR = min0.60337 p250.68084 median0.75216 p750.94036 max1.95701
```

The causal envelope uses only targets persisted at decision time with
`causal=true`, `future_safe=true`, and `directionally_valid=true`. Net RR is
recomputed from target distance, the same causal stop, and the persisted full
cost. No future hindsight target is used. Even the best target available in
that envelope is below final required RR for every candidate.

## Formula and bounded sensitivity

Production uses
`max((1-p)/p + min_ev_reserve_r, (1-p+min_positive_ev_r)/p)` with Set #2
`min_ev_reserve_r=0.05` and `min_positive_ev_r=0`. The pure break-even term is
`(1-p)/p`.

```text
BASELINE_CONSERVATIVE_REQUIRED_MEDIAN = 4.11010
POSTERIOR_PWIN_REQUIRED_MEDIAN = 2.75000
RAW_PWIN_REQUIRED_MEDIAN = 2.83947
REMOVE_EV_RESERVE_ONLY_MEDIAN = 4.06010
```

The small reserve is not the bottleneck. Replacing conservative probability
with raw/posterior probability would still leave the median requirement about
3.7 times the median causal net RR and is forbidden as an authoritative
fallback.

Feasibility frontier (`required RR`, including the 0.05 reserve):

```text
p=.10 -> 9.05; .12 -> 7.3833; .15 -> 5.7167; .20 -> 4.05
p=.25 -> 3.05; .30 -> 2.3833; .35 -> 1.9071; .40 -> 1.55
```

## Evidence, validation, and safety

```text
EVIDENCE = artifacts/scalping_v2_dynamic_rr_calibration_01/task_b/RR_ACHIEVABILITY_COHORT.jsonl; artifacts/scalping_v2_dynamic_rr_calibration_01/task_b/TASK_B_REPORT.json
FOCUSED_TESTS = 13 passed
COMPILE = PASS
POSTGRES_ACCESS = SELECT_ONLY
PRODUCTION_MUTATION = 0
DEPLOY = NOT_REQUIRED
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
FULL_PARAMETER_SWEEP = NOT_RUN
```
