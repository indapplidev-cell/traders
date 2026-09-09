# TRADERS_SCALPING_V2 setup/regime variants — Task C

```text
TASK_STATUS = PASS
FINAL_VERDICT = NO_CANDIDATE
VARIANTS_EVALUATED = 6_INCLUDING_BASELINE
BASELINE_CANDIDATES_PER_HOUR = 49.9100346021
BEST_VARIANT_CANDIDATES_PER_HOUR = N/A_NO_ELIGIBLE_VARIANT
BASELINE_RR_PASS = 0
BEST_VARIANT_RR_PASS = N/A
BASELINE_EXPECTANCY = -0.5457415081R_DIAGNOSTIC_ONLY_CONTAMINATED
BEST_VARIANT_EXPECTANCY = N/A
BASELINE_PF = 0.0267550287_DIAGNOSTIC_ONLY_CONTAMINATED
BEST_VARIANT_PF = N/A
BASELINE_ACHIEVABILITY = 0.3328315167
BEST_VARIANT_ACHIEVABILITY = N/A
QUALITY_GAIN = N/A_OUTCOME_TIMING_NOT_CAUSAL
FREQUENCY_LOSS = N/A_NO_SELECTED_VARIANT
BEST_VARIANT = NONE
OVERFIT_RISK = HIGH_INVALID_LEGACY_OUTCOME_TIMING
SHADOW_ALLOWED = NO
NEXT_TASK = COLLECT_FRESH_V3_DECISION_TIME_ANCHORED_OUTCOMES_THEN_REPEAT_BOUNDED_RESEARCH
```

The same frozen 24h exact-result cohort was split chronologically 70/30.  The
bounded policies were baseline, abstain UNKNOWN, require confirmed impulse,
trend plus confirmed impulse, exclude momentum+UNKNOWN, and known regime plus
confirmed impulse.  No parameter sweep was run.

Requiring confirmed impulse yields zero candidates because the entire cohort
is NO_IMPULSE.  The strongest retained-frequency diagnostic is abstaining on
UNKNOWN (140 candidates, 5.8131/hour, 88.35% frequency loss), but its apparent
expectancy change is not eligible evidence because legacy entry timing is
contaminated.  Its validation achievability (`0.2091`) is also below baseline
validation (`0.2443`).  It is therefore neither selected nor shadow-eligible.
All variants retain unchanged Dynamic RR, probability authority, costs, risk,
and safety limits.

Evidence: `artifacts/scalping_v2_postfix_setup_regime_01/TASK_C_REPORT.json`.
