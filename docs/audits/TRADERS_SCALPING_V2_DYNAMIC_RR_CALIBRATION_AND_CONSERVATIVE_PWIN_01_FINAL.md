# TRADERS_SCALPING_V2_DYNAMIC_RR_CALIBRATION_AND_CONSERVATIVE_PWIN_01_FINAL

```text
TASK_STATUS = PASS_WITH_LIMITED_CALIBRATION_SAMPLE
FINAL_VERDICT = PASS_DYNAMIC_RR_IS_SYSTEMATICALLY_UNACHIEVABLE_FOR_CURRENT_SET2_EDGE_AND_CAUSAL_GEOMETRY; NO_RUNTIME_BUG_OR_CONFIDENCE_LOOSENING_JUSTIFIED

TASK_A_STATUS = PASS_WITH_LIMITED_OUTCOME_SAMPLE
TASK_B_STATUS = PASS_DYNAMIC_RR_SYSTEMATICALLY_UNACHIEVABLE
TASK_C_STATUS = PASS_NO_CHANGE
TASK_D_STATUS = NOT_APPLICABLE_NO_DEFECT_AND_NO_PROMOTABLE_POLICY_CANDIDATE

# PWIN CALIBRATION

COHORT_COUNT = 49; exact outcome matches23; causally scoreable18
OBSERVED_WIN_RATE = 0.1666666667
RAW_PWIN_MEAN = 0.2775731080
CONSERVATIVE_PWIN_MEAN = 0.2094268521
BRIER_SCORE = 0.1404937696 conservative versus 0.1509378568 raw
CALIBRATION_ERROR = 0.0526781416 conservative versus 0.1109064414 raw

CONSERVATIVE_BOUND_TOO_AGGRESSIVE = NOT_PROVEN; frozen sample shows overprediction, not excessive pessimism
PARENT_BUCKET_OVERGENERALIZATION = SMALL_SAMPLE_HETEROGENEITY_SIGNAL_ONLY_NOT_PROVEN
OUTCOME_SEMANTICS_DEFECT = NO
SELECTION_BIAS = NO_EXECUTED_ONLY_BIAS_AND_NO_LOOKAHEAD_IN_SCORED_ROWS

# RR ACHIEVABILITY

RR_COHORT_COUNT = 49
RR_PASS = 0
RR_FAIL = 49

NET_RR_MEDIAN = 0.75015612
DYNAMIC_REQUIRED_RR_MEDIAN = 4.1101042744
FINAL_REQUIRED_RR_MEDIAN = 4.1101042744
ACHIEVABILITY_RATIO_MEDIAN = 0.1955433911

ACHIEVABLE_COUNT = 0
MARGINAL_COUNT = 0
STRUCTURALLY_UNACHIEVABLE_COUNT = 49

DYNAMIC_RR_ECONOMIC_VERDICT = SYSTEMATICALLY_UNACHIEVABLE_FOR_CURRENT_SET2_CAUSAL_GEOMETRY; gate rejection is economically coherent

# POLICY

CALIBRATION_POLICY_CHANGE_NEEDED = NO
SOFTWARE_FIX_NEEDED = NO
SHADOW_CANDIDATE_NEEDED = NO

# PRODUCTION

AUTHORITATIVE_POLICY_CHANGED = NO
SHADOW_DEPLOYED = NO
PRODUCTION_DEPLOY = NOT_REQUIRED_DIAGNOSTIC_ONLY

SERVER_COMMITS = 86a0b36cab371992e54a63f16f7cd65b90a08e7c; 745c5c7ef72b763e6c43031e86c479d3ab572e1b; bf6b51bc05d1f8258bcf967749deb7921622ee43
CLIENT_COMMITS = NONE
DOCUMENTATION_COMMITS = RESOLVE_FROM_GIT_AFTER_COMMIT
PUSH = A_B_C_PUSHED_AHEAD0_BEHIND0_BEFORE_MASTER_AUDIT

SERVER_TESTS = 64_PASS
POSTGRES_E2E = 6_PASS_ISOLATED_POSTGRES16_TEST_PRINCIPAL
DESKTOP_TESTS = 1509_PASS_2_SKIP_3029_SUBTESTS
COMPILE = PASS

LIVE_STATE_AFTER = DISABLED_live_allowed_false_MODE_PAPER
BINANCE_ORDER_CALLS = 0_REAL; paper ledger only

REMAINING_BLOCKERS = only18 causally scoreable calibration outcomes; no profitable Set2 evidence; 72h soak not started; exact/parent heterogeneity not robustly resolved
NEXT_RECOMMENDED_ACTION = continue bounded Set2 PAPER outcome collection; investigate strategy edge/causal target-stop geometry rather than weakening RR or confidence; repeat calibration on an independent larger cohort before any shadow candidate
```

## Root finding

The production formula is internally consistent. At the observed median causal
net RR of `0.7502`, a conservative win probability near `0.5882` would be
required merely to satisfy break-even plus the `0.05R` reserve. The measured
observed win rate is `0.1667`, and even raw/posterior alternatives leave median
required RR at `2.84/2.75`. Therefore the present rejection is dominated by
insufficient trading edge relative to costs and causal geometry, not by a
software defect or the small EV reserve.

Task C confirmed this with bounded same-cohort alternatives: Wilson 90%, 95%,
and 97.5% all produced `0/49` RR passes. The 90% alternative worsened
calibration; the 97.5% alternative improved in-sample Brier by only `0.000886`
while worsening achievability. No alternative merits shadow deployment.

## Evidence and constraints

```text
TASK_A = docs/audits/TRADERS_SCALPING_V2_DYNAMIC_RR_PWIN_CALIBRATION_TASK_A_FINAL.md
TASK_B = docs/audits/TRADERS_SCALPING_V2_DYNAMIC_RR_ACHIEVABILITY_TASK_B_FINAL.md
TASK_C = docs/audits/TRADERS_SCALPING_V2_DYNAMIC_RR_CALIBRATION_POLICY_TASK_C_FINAL.md
ARTIFACT_ROOT = artifacts/scalping_v2_dynamic_rr_calibration_01
DB_SCHEMA = 0031_scalping_parameter_sets
RUNTIME_SOURCE = 6e8e91547d9ed7005cc8132fe22bd30e87a21a04
READONLY_API = HEALTH_OK_READY_TRUE; PAPER_READY_MODE_PAPER_live_allowed_false
LATEST_5M_CORROBORATION = 1788955200000 at fresh verification
PRODUCTION_DB_ACCESS = SELECT_ONLY
TEST_DATABASE = task-owned paper_test_dynamic_rr_calibration removed after PASS
UNRELATED_WORKTREE_CHANGES = PRESERVED_EXCLUDED_FROM_ALL_TASK_COMMITS
```
