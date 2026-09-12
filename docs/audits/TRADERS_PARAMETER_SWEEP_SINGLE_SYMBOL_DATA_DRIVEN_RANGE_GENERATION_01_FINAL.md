# TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_DATA_DRIVEN_RANGE_GENERATION_01

FINAL_STATUS = PASS
FINAL_VERDICT = PASS_DETERMINISTIC_SCHEMA_AWARE_PROVISIONAL_RANGES_FROM_AUTHORIZED_CAUSAL_SEPARABILITY_EVIDENCE_NO_SEARCH_NO_PROMOTION

SYMBOL = DOGEUSDT
PROFILE = trade-5m-v2

SEPARABILITY_STATUS = PASS_LIMITED_SAMPLE
SAMPLE_ADEQUACY = DESCRIPTIVE_ONLY_3_WIN_7_LOSS

TUNABLE_PARAMETERS_TOTAL = 29
DIRECT_MAPPED = 8
DERIVED_MAPPED = 7
INDIRECT_MAPPED = 5
NO_AUTHORIZED_MAPPING = 9

RANGES_GENERATED = 4
PROVISIONAL_RANGES = 4
RANGES_NOT_GENERATED = 25

DATA_DRIVEN_SEARCH_RANGES_CREATED = YES
RANGE_GENERATION_TRACE_CREATED = YES
DATA_DRIVEN_RANGE_HANDOFF_CREATED = YES
LEGACY_COMPARISON_CREATED = YES

CURRENT_VALUES_PRESERVED_UNDER_LOW_SAMPLE = YES_4_OF_4
SCHEMA_VIOLATIONS = 0
CYCLIC_LINEARIZATION_VIOLATIONS = 0
HIDDEN_NUMERIC_FALLBACKS = 0
LEGACY_ARRAY_FALLBACKS = 0

BOUNDARY_PRESSURE_COUNT = 2
BOUNDARY_EXPANSION_EXECUTED = NO

PROMOTION_ELIGIBLE = NO
SEARCH_EXECUTED = NO
ADAPTIVE_REFINEMENT_EXECUTED = NO
HOLDOUT_OPENED = NO

TESTS = PASS_197_RESEARCH_TESTS
COMPILE = PASS_APP_CONFIG_AND_PARAMETER_SWEEP

FILES_CHANGED = app/config/yaml_authority.py; config/research/research_parameters.yaml; traders_ml/parameter_sweep/data_driven_ranges.py; tests/research/test_parameter_sweep_data_driven_ranges.py; docs/audits/TRADERS_PARAMETER_SWEEP_SINGLE_SYMBOL_DATA_DRIVEN_RANGE_GENERATION_01_FINAL.md; online_trader.md
COMMITS = PROJECT_STATE_87b1b5c19cd64f4327970e18eaa38096d0bada30; DOCUMENTATION_RECONCILIATION_SELF_RESOLVED_BY_GIT
PUSH = PROJECT_STATE_PUSHED_TO_ORIGIN_FEATURE_ENGINE_PLATFORM; DOCUMENTATION_RECONCILIATION_PENDING_AT_AUDIT_AUTHORING
AHEAD_BEHIND = PROJECT_STATE_POST_PUSH_AHEAD0_BEHIND0
WORKTREE = CLEAN_AFTER_PROJECT_STATE_COMMIT_BEFORE_DOCUMENTATION_RECONCILIATION

PRODUCTION_TRADING_LOGIC_CHANGED = NO
PRODUCTION_YAML_CHANGED = NO
ACTIVE_SET2_CHANGED = NO
VALIDATION_GATES_20_3_CHANGED = NO
DB_SCHEMA_CHANGED = NO
PRODUCTION_DEPLOY = NO

LIVE_STATE = DISABLED
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

OUT_OF_SCOPE_ISSUES = PROJECT_RUNTIME_WAL_AND_PITR_READINESS_AND_CLEAN72H_SOAK_REMAIN_SEPARATE_EXISTING_BLOCKERS
REMAINING_BLOCKERS = STATISTICAL_CERTIFICATION_BLOCKED_BY_ONLY_10_CLOSED_TRADES_3_WIN_7_LOSS; GENERATED_DOMAINS_ARE_PROVISIONAL_ONLY
NEXT_RECOMMENDED_ACTION = SEPARATE_EXPANDED_AUTOMATIC_RESEARCH_SEARCH_TASK_MAY_CONSUME_PROVISIONAL_HANDOFF_WITHOUT_ADAPTIVE_EXPANSION_HOLDOUT_OR_PRODUCTION_PROMOTION

## Real acceptance output

The authoritative registry contained 29 current dimensions. Every dimension
has an explicit mapping classification and consumer-path explanation in
`PARAMETER_EVIDENCE_MAP.json`. No feature created a new strategy parameter;
in particular, `utc_hour` remains `EVIDENCE_ONLY_NOT_TUNABLE` and is protected
from ordinary linear range generation.

| Parameter | Evidence class / feature | Range status | Generated domain | Confidence | Current included | Boundary |
|---|---|---|---|---|---|---|
| `min_net_edge_bps` | DIRECT / `net_edge_bps` | PROVISIONAL_LOW_SAMPLE | `[1.0, 21.005729, 45.035662, 57.029956, 73.004386, 82.589044]` | DESCRIPTIVE_ONLY | YES | HIGH |
| `minimum_planned_rr` | DIRECT / `planned_rr` | PROVISIONAL_LOW_SAMPLE | `[0.6, 1.520346, 1.953403, 2.675166, 2.783225, 4.361216, 6.196394]` | DESCRIPTIVE_ONLY | YES | NONE |
| `stop_max_bps` | DIRECT / `stop_distance_bps` | PROVISIONAL_LOW_SAMPLE | `[10.987851, 28.928998, 31.552087, 43.772972, 46.725232, 48.496589, 50.0]` | DESCRIPTIVE_ONLY | YES | NONE |
| `target_min_bps` | DIRECT / `target_distance_bps` | PROVISIONAL_LOW_SAMPLE | `[49.163216, 60.0, 73.180352, 85.175891, 101.137923, 110.715142]` | DESCRIPTIVE_ONLY | YES | HIGH |

Direct mappings with unusable real evidence were not generated:
`bucket_min_sample` (`probability_sample_size` missing), `entry_slippage_bps`
(`slippage_bps` constant), `min_positive_ev_r` (`expected_ev_r` missing), and
`strategy_minimum_score` (`strategy_score` constant). The other 21 parameters
were not eligible for generation because their evidence was only derived,
indirect, or had no authorized mapping. No legacy values were used as a
fallback.

## Artifacts and reproducibility

Run-local output:
`artifacts/scalping_v2_parameter_sweep/data_driven_ranges_dogeusdt_01/`

- `PARAMETER_EVIDENCE_MAP.json`
- `DATA_DRIVEN_SEARCH_RANGES.json`
- `RANGE_GENERATION_TRACE.json`
- `DATA_DRIVEN_RANGE_HANDOFF.json`
- `LEGACY_RANGE_COMPARISON.json`
- `REPORT.md`

Each range row records exact input SHA-256 values, mapping path, typed schema
domain, resolved YAML-policy paths, candidate calculation, schema clipping,
interaction annotations, and generator version. Two consecutive real runs
produced byte-identical files.

These ranges are provisional research ranges.
They are not statistically certified.
They must not be promoted automatically.
