# TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_ADAPTIVE_REFINEMENT_01 — FINAL

```text
FINAL_STATUS = PASS
FINAL_VERDICT = PASS_DESCRIPTIVE_ONLY_ADAPTIVE_REFINEMENT_NOT_CERTIFIED

SYMBOL = DOGEUSDT
PROFILE = trade-5m-v2

SYMBOL_AUTHORITY_SOURCE = app.trading_universe.domain:trading-universe-v2 -> required CLI --symbol -> validator -> adaptive run config
RUNTIME_SYMBOL_HARDCODES = 0
RUNTIME_SYMBOL_DEFAULTS = 0
RUNTIME_SYMBOL_BRANCHES = 0

SOURCE_HISTORY_START = 2026-09-02T21:35:00+00:00
SOURCE_HISTORY_END = 2026-09-12T10:45:00+00:00
SOURCE_HISTORY_ACTUAL_DAYS = 9.54861111111111

INITIAL_NUMERIC_CONFIGS = 500
INITIAL_BEHAVIORAL_CLUSTERS = 21
INITIAL_POSITIVE_NUMERIC_CONFIGS = 108
INITIAL_POSITIVE_BEHAVIORAL_CLUSTERS = 2

BEHAVIORALLY_ACTIVE_PARAMETERS = min_net_edge_bps; stop_max_bps
BEHAVIORALLY_FLAT_PARAMETERS = NONE
INSUFFICIENT_EVIDENCE_PARAMETERS = minimum_planned_rr; target_min_bps

ADAPTIVE_ROUNDS = 2
NEW_NUMERIC_CONFIGS_EVALUATED = 50
NEW_BEHAVIORAL_CLUSTERS_DISCOVERED = 4
NEW_POSITIVE_BEHAVIORAL_CLUSTERS = 1
BEHAVIORAL_DUPLICATES = 46

INTERIOR_REFINEMENT_CANDIDATES = 90_DISTINCT_GENERATED; 49_EVALUATED
BOUNDARY_EXPANSION_CANDIDATES = 1_DISTINCT_GENERATED; 1_EVALUATED
BOUNDARY_BLOCKED_BY_SCHEMA = 0

FINAL_BEHAVIORAL_CLUSTERS = 25
FINAL_POSITIVE_NUMERIC_CONFIGS = 127
FINAL_POSITIVE_BEHAVIORAL_CLUSTERS = 3

BEST_CANONICAL_RANKED_CONFIG = f37a02163583157089fbc2d5f012e0f3355b48c67d78bea3a9281206895d2b0c {min_net_edge_bps=1.0, minimum_planned_rr=0.6, stop_max_bps=50.0, target_min_bps=60.0}
BEST_CANONICAL_RANKED_NET_PNL = -0.04961941999999997
BEST_CANONICAL_RANKED_PF = 0.9535167395746674

BEST_NET_PNL_CONFIG = fec017f393fe5daf2b7c5354ab275fc0e1f7190a8c01e7c6c5889b94862d40c5 {min_net_edge_bps=73.004386, minimum_planned_rr=1.953403, stop_max_bps=48.496589, target_min_bps=49.163216}
BEST_NET_PNL = 1.01784916

BEST_PF_CONFIG = f37a02163583157089fbc2d5f012e0f3355b48c67d78bea3a9281206895d2b0c {min_net_edge_bps=1.0, minimum_planned_rr=0.6, stop_max_bps=50.0, target_min_bps=60.0}
BEST_PF = 0.9535167395746674

VALIDATION_ELIGIBLE_CONFIGS = 0

CONVERGENCE_STATUS = CONVERGED
STOP_REASON = NO_NEW_BEHAVIORAL_CLUSTERS

HOLDOUT_READS = 0
HOLDOUT_OPENED = NO
FINALIST_FREEZE_EXECUTED = NO

ADAPTIVE_REFINEMENT_HANDOFF_CREATED = YES

SEARCH_RANKING_CHANGED = NO
VALIDATION_20_3_CHANGED = NO

SCHEMA_VIOLATIONS = 0
NEW_VALUE_WITHOUT_PROVENANCE = 0
DUPLICATE_CONSUMED_VALUES_EVALUATED = 0
RECONSTRUCTED_ROWS_USED = 0
CROSS_SYMBOL_ROWS = 0

BYTE_DETERMINISM = PASS_FRESH_IDENTICAL_RUNS_10_REQUIRED_ARTIFACTS_0_BYTE_DIFFERENCES; RESUME_0_BYTE_DIFFERENCES
RESUME_GUARDS = symbol; profile; dataset_fingerprint; calibration_split_fingerprint; validation_split_fingerprint; parameter_registry_version; range_handoff_fingerprint; expanded_search_fingerprint; adaptive_policy_fingerprint; seed

ADAPTIVE_RESULT_CERTIFIED = NO
PROMOTION_ELIGIBLE = NO

TESTS = PASS_231_RESEARCH; PASS_17_ADAPTIVE_FOCUSED; PASS_34_ADAPTIVE_PLUS_EXPANDED_AFTER_SYMBOL_AUDIT_UPDATE
COMPILE = PASS_COMPILEALL_PARAMETER_SWEEP_AND_RESEARCH_TESTS

FILES_CHANGED = traders_ml/parameter_sweep/adaptive_refinement.py; traders_ml/parameter_sweep/symbol_authority_audit.py; tests/research/test_parameter_sweep_adaptive_refinement.py; docs/audits/TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_ADAPTIVE_REFINEMENT_01_FINAL.md; online_trader.md; artifacts/scalping_v2_parameter_sweep/adaptive_refinement_dogeusdt_01/{ADAPTIVE_REFINEMENT_CONFIG.json,BEHAVIORAL_TRANSITION_GRAPH.json,ADAPTIVE_PARAMETER_SENSITIVITY.json,ADAPTIVE_CANDIDATE_TRACE.jsonl,ADAPTIVE_ROUNDS.jsonl,ADAPTIVE_RESULTS.jsonl,ADAPTIVE_BEHAVIORAL_CLUSTERS.json,ADAPTIVE_REFINEMENT_HANDOFF.json,STATUS.json,REPORT.md,CHECKPOINT.json}
COMMITS = PROJECT_STATE_beff25a129191dc02fe8c3429f6623fc9806871f; DOCUMENTATION_COMMIT_RESOLUTION_git_log_-1_--format=%H_--_online_trader.md
PUSH = PROJECT_STATE_PUSHED; DOCUMENTATION_RECONCILIATION_PUSHED
AHEAD_BEHIND = 0_0_AFTER_FINAL_PUSH
WORKTREE = CLEAN_AFTER_DOCUMENTATION_COMMIT

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = DISABLED_FALSE
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

OUT_OF_SCOPE_ISSUES = NONE_FOR_ADAPTIVE_REFINEMENT; PRODUCTION_AND_SOAK_STATE_UNCHANGED
REMAINING_BLOCKERS = VALIDATION_SAMPLE_REMAINS_BELOW_UNCHANGED_20_TRADES_AND_3_INDEPENDENT_UTC_DAYS; VALIDATION_ELIGIBLE_CONFIGS_0; EXPECTANCY_R_NOT_AVAILABLE
NEXT_RECOMMENDED_ACTION = SEPARATE_STEP_7_VALIDATION_RANKING_TASK_FROM_ADAPTIVE_REFINEMENT_HANDOFF_WITHOUT_HOLDOUT_FINALIST_FREEZE_OR_PROMOTION_UNLESS_SEPARATELY_AUTHORIZED
```

## Evidence summary

The adaptive engine consumes only explicit campaign paths and validates the
selected symbol, profile, canonical dataset hash, both deterministic split
hashes, typed parameter-registry fingerprint, exact range-handoff hash, the
aggregate expanded-search fingerprint, normalized domains, cluster membership,
adaptive-policy fingerprint and seed. A mismatch fails closed. No holdout path
is accepted by the API or CLI; the focused test places a holdout artifact beside
the inputs and instruments file reads, observing zero holdout reads.

Behavioral graph edges require an observed one-parameter adjacent pair with all
other parameters equal and different behavioral signatures. Sensitivity uses
only these comparable neighbor pairs. Interpolation uses the authoritative
range-policy transition weight and precision; boundary expansion uses current
adjacent spacing and requires pressure, a positive boundary cluster, behavioral
activity and schema validity. Candidate priority is separate from the unchanged
canonical result ranking.

The real run evaluated 49 transition-derived interior configs and one evidenced
high-boundary expansion. It discovered four new behavioral signatures in round
1. Round 2 added no new behavior, so convergence stopped immediately rather
than consuming the remaining 450-evaluation budget. The final handoff contains
all 25 behavioral clusters and remains descriptive-only: zero configurations
pass the unchanged 20-trade/three-independent-UTC-day validation gate.
