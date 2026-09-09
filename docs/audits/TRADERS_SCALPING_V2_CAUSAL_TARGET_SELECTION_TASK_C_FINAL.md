# Scalping v2 causal target selection — Task C

```text
TASK_STATUS = PASS
FINAL_VERDICT = TARGET_ORDERING_DEFECT
ANCHOR = 1788961200000
COHORT_COUNT = 723
TARGET_DISTANCE_MEDIAN_BPS = 25.3471
BEST_CAUSAL_TARGET_MEDIAN_BPS = 39.1046
TARGET_EFFICIENCY_MEDIAN = 0.99999435
FARTHER_CAUSAL_TARGET_AVAILABLE_COUNT = 376
TARGET_SELECTOR_MISSED_COUNT = 59
TARGET_SOFTWARE_DEFECT = YES
PRODUCTION_CHANGE_REQUIRED = YES_DEFECT_FIX_ONLY
NEXT_TASK = TASK_D_BOUNDED_VARIANTS
```

```text
TARGET_SELECTOR_FORMULA = source priority, distance, known_at, source_detail
TARGET_ORDERING = LOCAL_5M -> RECENT_5M_SWING -> LOCAL_RANGE_BOUNDARY -> STRUCTURAL -> 15M -> 1H; nearest within tier
FIRST_ACCEPTABLE_RULE = first target with positive cost-aware edge and Net RR >= minimum_planned_rr 0.6
DOES_SELECTOR_EVALUATE_FARTHER_TARGETS = only until the first static acceptable target; formerly no after late Dynamic RR rejection
```

This is the historical regression pattern in current Set #2: target construction
stopped at the first static-cost acceptable level, and only afterwards applied
Dynamic RR. Fifty-nine decisions already contained a farther causal target in
the same snapshot that met the unchanged final Dynamic RR.

The bounded, no-lookahead alternative is not profitable evidence: 78 would pass
RR, 67 have complete outcomes, only 3 hit target, 46 hit stop, 18 timed out;
expectancy is -0.7174R, PF 0.0628, DD 48.7056R. The defect fix therefore only
continues causal traversal through farther levels when the first target fails
Dynamic RR. It does not promote the alternative or weaken costs/probability/RR.

