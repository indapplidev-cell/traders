# Scalping v2 impulse detector calibration and v3 setup research 01

TASK_STATUS = PASS_WITH_NO_CANDIDATE
FINAL_VERDICT = CURRENT_3PCT_FLOOR_IS_5M_SCALE_MISMATCH_TOO_RARE_AND_TOO_LATE_NO_MONOTONIC_EDGE_NO_SAFE_CANDIDATE
TASK_A_STATUS = PASS_CURRENT_THRESHOLD_TOO_RARE_FOR_5M
TASK_B_STATUS = PASS_TIMEFRAME_AND_POLICY_MISMATCH_NO_WIRING_DEFECT
TASK_C_STATUS = PASS_NO_CANDIDATE
TASK_D_STATUS = NOT_APPLICABLE_NO_CREDIBLE_CANDIDATE

V3_COHORT_COUNT = 2722
MOVE_PCT_MEDIAN = 0.651338
MOVE_PCT_P90 = 1.2430532
MOVE_PCT_P95 = 1.5295891
MOVE_PCT_P99 = 2.14232
ATR_PCT_MEDIAN = 0.22518
ATR_PCT_P90 = 0.4234898
CURRENT_THRESHOLD_REACH_COUNT = 5
CURRENT_THRESHOLD_REACH_RATE = 0.183688%
ABSOLUTE_3_PERCENT_DOMINANT_COUNT = 2722
ATR_COMPONENT_DOMINANT_COUNT = 0
CONFIRMED_IMPULSE_COUNT = 5
HIGHER_INTENSITY_IMPROVES_EDGE = NO_NOT_MONOTONIC
ENTRY_EXHAUSTION_FOUND = YES_MEDIAN_COMPLETED91.2794BPS_REMAINING_MFE18.1546BPS_N218

ABSOLUTE_THRESHOLD = 3.0_PERCENT
ATR_MULTIPLIER = 2.5
INTRODUCED_COMMIT = cca167e8c89feb8494c8d8c7af1f103ffd43e6f8
ORIGINAL_PROFILE = trade-15m-v1
ORIGINAL_TIMEFRAME = 15m
LEGACY_DRIFT_FOUND = YES
TIMEFRAME_MISMATCH_FOUND = YES
POLICY_MISMATCH_FOUND = YES
SOFTWARE_DEFECT_FOUND = NO

VARIANTS_EVALUATED = 6
BEST_VARIANT = NONE; BEST_DIAGNOSTIC_ONLY=FLOOR_0_50PCT_PLUS_1_0ATR
BASELINE_IMPULSE_RATE = 0.183688%
VARIANT_IMPULSE_RATE = 68.993387%
BASELINE_CANDIDATES_PER_HOUR = 0.0
VARIANT_CANDIDATES_PER_HOUR = 44.470588
BASELINE_EXPECTANCY = UNAVAILABLE_ZERO_SCOREABLE
VARIANT_EXPECTANCY = -0.392726R
BASELINE_PF = UNAVAILABLE_ZERO_SCOREABLE
VARIANT_PF = 0.157868
BASELINE_ACHIEVABILITY = UNAVAILABLE
VARIANT_ACHIEVABILITY = 0.340829
QUALITY_GAIN = NOT_PROVEN_NEGATIVE_FULL_SAMPLE
FREQUENCY_CHANGE = LARGE_INCREASE_WITHOUT_QUALITY
VALIDATION_RESULT = SMALL_POSITIVE_SLICE_DOES_NOT_REPLICATE_DEVELOPMENT
OVERFIT_RISK = HIGH
SHADOW_ALLOWED = NO

SHADOW_DEPLOYED = NO
SHADOW_ID = NONE
SHADOW_RESULT = NOT_APPLICABLE

AUTHORITATIVE_SET2_CHANGED = NO
PRODUCTION_FIX_DEPLOYED = NO
SHADOW_ONLY = NO_SHADOW_NOT_JUSTIFIED
SERVER_COMMITS = f1911ad12255f951fda4a7bdaaf0b26093625ec7; 6db4796d249b0c94e2441ed5943f11bee7e0cda5; 6fbb4c53405ddeef0473cf07150bdc37cc30885a; 87c1497c7621425a36fdf1008eb00e75c9ab1a4d
CLIENT_COMMITS = NONE
DOCUMENTATION_COMMITS = 2236ff02fc37388f9f62d9c7f8bb4c82687501bb; MASTER_AND_RECONCILIATION_RESOLVE_WITH_GIT
PUSH = ALL_TASK_COMMITS_PUSHED_AHEAD0_BEHIND0_BEFORE_MASTER
SERVER_TESTS = 36_FOCUSED_PASS_PLUS_BOUNDARY_TESTS
POSTGRES_E2E = PASS_ANCHOR10_ROWS10_SYMBOLS_EXACT_PROFILE_SET_HASH; POSITIONS53CLOSED0OPEN; V3_OUTCOME_APPEND_ONLY_229ENTERED0PREDECISION
DESKTOP_TESTS = 3_EXACT_SET2_PROVENANCE_RENDERING_PASS; FULL_SUITE_NOT_COMPLETED_WITHIN_BOUNDED_RUN
COMPILE = SERVER_AND_CLIENT_PASS
LIVE_STATE_AFTER = DISABLED_CONTINUOUS_PAPER_STATISTICS_ONLY
BINANCE_ORDER_CALLS = 0
REMAINING_BLOCKERS = NO_POSITIVE_EDGE_NO_CREDIBLE_CANDIDATE_SINGLE_DAY_SAMPLE_72H_SOAK_NOT_STARTED
NEXT_RECOMMENDED_ACTION = COLLECT_INDEPENDENT_MULTI_REGIME_FRESH_V3_OUTCOMES_THEN_REPEAT_BOUNDED_CHRONOLOGICAL_CALIBRATION_WITHOUT_POLICY_LOOSENING

## Decision

The current detector is not realistic as an actionable 5m impulse gate. Its
3% floor is reached in only five of 2,722 observations and dominates the ATR
term in every observation. Waiting for stronger moves does not yield monotonic
causal edge and consumes most of the move before entry. This proves a market-
scale and semantic mismatch, but does not prove a profitable replacement.

The provenance trace shows the threshold arrived in the recovered generic
analysis component while the only allowed primary orchestrator timeframe was
15m. It is now reused by 5m without a profile-specific config/resolver path.
The code is wired exactly as written, so no software/profile-routing defect was
deployed.

All six evidence-backed alternatives increase frequency dramatically, but
full-sample expectancy remains negative and the small positive validation slice
does not agree with development. No candidate is selected; consequently Task D
does not deploy a SHADOW service or alter API/Desktop projections.

## Verification and safety

- Frozen cohort identity SHA-256:
  `1d0fac07bcd3c3ae1ce6f203e5f5b09c5e96558424d744958fd0ee325d083258`.
- PostgreSQL read-only anchor query: 10 rows, 10 symbols, exact profile, Set #2
  and config hash; position state is 53 CLOSED / 0 OPEN.
- Collector health reports production trading mutations 0, parameter promotions
  0 and Binance order calls 0.
- Runtime remains the pre-task authoritative 5m image `sha256:222bf516...`,
  restart count 0; passive collector remains `sha256:a0f2b5ef...`.
- No Tk screenshot/acceptance was required because no client or readonly UI
  artifact changed. The separate client working tree's exact Set #2 rendering
  tests passed 3/3 and compile passed; its unrelated uncommitted work was not
  modified or committed.

Detailed evidence is in the four task audits and committed JSON/JSONL artifacts
under `artifacts/scalping_v2_impulse_calibration_01/`.
