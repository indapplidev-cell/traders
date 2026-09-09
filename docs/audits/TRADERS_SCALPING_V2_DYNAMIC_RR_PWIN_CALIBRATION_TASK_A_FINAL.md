# TRADERS_SCALPING_V2_DYNAMIC_RR_PWIN_CALIBRATION_TASK_A_FINAL

```text
TASK_STATUS = PASS_WITH_LIMITED_OUTCOME_SAMPLE
FINAL_VERDICT = CONSERVATIVE_PWIN_MEASURED; INSUFFICIENT_EVIDENCE_FOR_ROBUST_RECALIBRATION_OR_POLICY_CHANGE

ANCHOR = 1788954300000 / 2026-09-09T11:45:40.212775Z / trade-5m-v2 / scalping-v2-set-2 / config 1d0afbb4d1fb2cfb8afba03f718c28796a47e23b9d17c1f6e0109ace3d3717e7 / deployed 6e8e91547d9ed7005cc8132fe22bd30e87a21a04
COHORT_COUNT = 49 authority-available candidates over bounded 12h; 23 exact outcome matches; 18 causally scoreable outcomes

PWIN_RAW_MEAN = 0.2775731080
PWIN_CONSERVATIVE_MEAN = 0.2094268521
OBSERVED_WIN_RATE = 0.1666666667

BRIER_SCORE = 0.1404937696 conservative; 0.1509378568 raw
CALIBRATION_ERROR = 0.0526781416 conservative ECE; 0.1109064414 raw ECE
RELIABILITY_SUMMARY = conservative 0.0-0.2 bin n5 predicted0.18215 observed0.20; 0.2-0.4 bin n13 predicted0.21992 observed0.15385; sample is not robust

PARENT_LEVEL_USAGE_DISTRIBUTION = exact1; setup1; setup_direction_regime47; setup_direction0; global0
PARENT_LEVEL_CALIBRATION = setup_direction_regime scoreable17 predicted0.21396 observed0.17647 Brier0.14773; setup scoreable1 predicted0.13244 observed0; exact scoreable0

HETEROGENEITY_FOUND = YES_AS_SMALL_SAMPLE_SIGNAL; LINK scoreable6 observed0 versus SUI scoreable5 observed0.4; not sufficient for a hierarchy change
SELECTION_BIAS_FOUND = NO_EXECUTED_ONLY_BIAS; causal rejected opportunities included; exact source identity join used; completion-before-decision rows not scored
OUTCOME_SEMANTICS_DEFECT_FOUND = NO; TP_FIRST=WIN; SL_FIRST=LOSS; TIME_EXPIRED classified by net_return_bps sign; missing-net/entry-expired/no-geometry/ambiguous rows excluded

CONSERVATIVE_BOUND_TOO_AGGRESSIVE = NOT_PROVEN; on 18 outcomes the bound still overpredicts observed rate by 0.04276 rather than suppressing it, but uncertainty is high
EVIDENCE = artifacts/scalping_v2_dynamic_rr_calibration_01/task_a/PWIN_CALIBRATION_COHORT.jsonl; artifacts/scalping_v2_dynamic_rr_calibration_01/task_a/TASK_A_REPORT.json
ROOT_FINDING = current Wilson one-sided lower bound improves Brier/ECE versus raw p_win on the frozen sample; data do not support loosening confidence semantics. Parent/symbol heterogeneity needs more completed exact outcomes.

RUNTIME_CHANGE_REQUIRED = NO
NEXT_TASK = TASK_B_DYNAMIC_RR_ECONOMIC_ACHIEVABILITY
```

## Identity, causality, and coverage notes

The geometry candidate identity and the source causal opportunity identity are
both persisted. Calibration joins only
`paper_context.causal_primitives.opportunity_id` to the collector's frozen
opportunity id. No symbol-latest fallback is used. A matched outcome is scored
only when its completion timestamp is at or after the candidate boundary.

The configured value `0.95` is the one-sided Wilson confidence level. Empirical
coverage is not robustly measurable here: only one hierarchy group has at least
three causally scoreable outcomes, and its observed rate is below the mean
bound. This is evidence against declaring the bound excessively aggressive,
not evidence that 95% coverage has failed.

## Validation and safety

```text
FOCUSED_TESTS = 12 passed
COMPILE = PASS
POSTGRES_ACCESS = SELECT_ONLY; schema 0031_scalping_parameter_sets
PRODUCTION_MUTATION = 0
DEPLOY = NOT_REQUIRED
LIVE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
FULL_PARAMETER_SWEEP = NOT_RUN
```
