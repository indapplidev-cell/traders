# Scalping v2 bounded strategy/geometry variants — Task D

```text
TASK_STATUS = PASS
FINAL_VERDICT = NO_CANDIDATE
ANCHOR = 1788961200000
VARIANTS_EVALUATED = 4
BEST_VARIANT = NONE
OVERFIT_RISK = MEDIUM
PROMOTION_ALLOWED = NO
SHADOW_ELIGIBLE = NO
NEXT_TASK = COLLECT_LARGER_INDEPENDENT_CAUSAL_COHORT
```

The same frozen cohort was evaluated chronologically (70% fit / 30%
validation) with four pre-declared policies: baseline, first farther target
meeting unchanged Dynamic RR, trend-aligned only, and impulse-present only.
No grid or parameter sweep was run. Costs, conservative probability, Dynamic
RR, risk, and position limits were unchanged.

The farther-target rule had 78 fit candidates but zero validation candidates;
its scoreable fit expectancy was -0.7174R. Trend and impulse filters had no
eligible rows because the current persisted regime/entry context is UNKNOWN or
NO_IMPULSE. No alternative satisfies geometry improvement plus non-degraded
validation expectancy, so Task E is not applicable.

