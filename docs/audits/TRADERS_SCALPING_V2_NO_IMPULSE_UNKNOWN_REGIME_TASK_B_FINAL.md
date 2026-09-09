# TRADERS_SCALPING_V2 NO_IMPULSE / UNKNOWN_REGIME — Task B

```text
TASK_STATUS = PASS_WITH_RESEARCH_COLLECTOR_DEFECT_FIXED
FINAL_VERDICT = SOFTWARE_DEFECT_AND_POLICY_MISMATCH_FOUND
COHORT_COUNT = 2342 exact unique production result_ids / rolling 24h / 1202 SETUP_CANDIDATE / 1140 NO_SETUP
NO_IMPULSE_COUNT = 2342
NO_IMPULSE_RATE = 1.0
NO_IMPULSE_SUBREASONS = MOVE_BELOW_ABSOLUTE_3PCT_FLOOR:2342
UNKNOWN_REGIME_COUNT = 2064
UNKNOWN_REGIME_RATE = 0.8812980359
UNKNOWN_REGIME_SUBREASONS = CONSERVATIVE_FALLBACK:2054; UNRESOLVED_CONFIRMED_HYPOTHESIS_CONFLICT:8; HIGH_CONFLICT:2
CONFIRMED_IMPULSE_EXPECTANCY = N/A_ZERO_SAMPLE
NO_IMPULSE_EXPECTANCY = -0.5457415081R_DIAGNOSTIC_ONLY_CONTAMINATED
KNOWN_REGIME_EXPECTANCY = -0.5710341324R_DIAGNOSTIC_ONLY_CONTAMINATED
UNKNOWN_REGIME_EXPECTANCY = -0.5424647309R_DIAGNOSTIC_ONLY_CONTAMINATED
SETUP_ALLOWED_WITH_NO_IMPULSE = YES_1202
SETUP_ALLOWED_WITH_UNKNOWN_REGIME = YES_1062
IMPULSE_ROOT_CAUSE = IMPULSE_DEFINITION_WEAK_PLUS_IMPULSE_GATE_TOO_PERMISSIVE
REGIME_ROOT_CAUSE = CLASSIFIER_VALID_ABSTENTION_BUT_SETUP_POLICY_DOES_NOT_ABSTAIN
ENTRY_TIMING_ROOT_CAUSE = CANDIDATE_FORMED_WITHOUT_IMPULSE_CONFIRMATION_AND_LEGACY_RESEARCH_OUTCOME_CLOCK_ANCHORED_BEFORE_DECISION
SOFTWARE_DEFECT_FOUND = YES_RESEARCH_COLLECTOR_OUTCOME_TIMESTAMP_GATE
POLICY_MISMATCH_FOUND = YES_INTENTIONAL_CODE_PATH_NOW_EVIDENCE_NEGATIVE
PRODUCTION_CHANGE_REQUIRED = YES_PASSIVE_COLLECTOR_ONLY; AUTHORITATIVE_SET2_NO
NEXT_TASK = TASK_C_BOUNDED_VARIANTS_AFTER_CAUSALITY_QUALIFICATION
```

The actual detector definition is
`impulse_move_pct >= max(3.0, atr_pct * 2.5)` over eight closed 5m bars.
Every frozen observation had sufficient data but remained below the binding
absolute 3% floor.  In contrast, the v2 micro-setup fallback treats
`impulse_move_pct >= 0.25` plus volatility ratio `>= 0.9` and an indicator
direction as momentum, and accepts `NOT_EVALUATED` entry evidence.  This is the
exact path by which all 1,202 candidates were labelled WEAK while impulse was
NO_IMPULSE.  The behavior is intentional in code, but the negative evidence
makes the contract a policy mismatch rather than a software control-flow bug.

The composer UNKNOWN state is a valid conservative abstention: 2,054 cases are
score-margin/no-confirmed-hypothesis fallback, eight unresolved confirmed
hypothesis conflicts, and two high conflicts; there are zero low-coverage,
partial-analysis, or OHLC-failure causes.  Setup nonetheless admits 1,062
UNKNOWN-regime candidates.

The legacy outcome evidence is not causally acceptable.  Of 1,202 candidate
outcomes, 1,048 were labelled ENTERED and all 1,048 used a candle whose open
preceded `entry_decision_time_ms`; 572 decisions were already later than the
old boundary-anchored 30-second TTL.  Median decision lag is 29.652s, maximum
925.084s.  Therefore MFE/MAE and the displayed expectancy/PF are retained only
as contaminated diagnostics.  Pre-entry MFE and distance moved before entry
are not persisted and were not invented.

The passive collector fix anchors TTL/time-stop at decision time, rejects
pre-decision candle opens, and starts outcome semantics v3 so invalid v2 rows
cannot mix with corrected evidence.  Dynamic RR, probability formula/sample
floor, costs, risk, command limits, positions, and authoritative Set #2 are
unchanged.

Evidence: `artifacts/scalping_v2_postfix_setup_regime_01/TASK_B_REPORT.json`
and `TASK_B_SETUP_REGIME_COHORT.jsonl`.
