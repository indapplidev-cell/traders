# Parameter Sweep v2 — Block C targeted search space

TASK_STATUS = PASS
BASELINE_SET = scalping-v2-set-2
BASELINE_HASH = 0b109fd317af9c9d2b96f6933a4964f3ae3ff5685804a4a160aacb7ef27cb429
PARAMETER_FAMILIES = SIGNAL,REGIME,ENTRY,GEOMETRY,ECONOMICS,LIFECYCLE_SHADOW,RISK_SAFETY,COSTS
TARGETED_PARAMETERS = stop_max_bps,target_min_bps,causal_reset_min_conditions,entry_refinement_1m_confirmation_count
FROZEN_PARAMETERS = minimum_planned_rr,probability_confidence_policy,commission_source,risk_per_trade_bps,max_open_positions,max_new_commands_per_cycle,total_open_risk_limit_bps,and_all_non_targeted_YAML_keys
STAGE_BUDGETS = SET2_BASELINE:1,ONE_FACTOR_SENSITIVITY:10,SMALL_FAMILY_SEARCH:60,TOP_REGION_REFINEMENT:40,LOCAL_FINALIST_VALIDATION:33
RAW_CARTESIAN_SPACE = 36691771392_LEGACY_DECLARED_SPACE;144_ACTIVE_TARGETED_SPACE
PLANNED_EVALUATIONS = 144_MAX_FOR_CURRENT_TARGETED_PHASE
ACTUAL_EVALUATIONS = DEFERRED_TO_BLOCK_G_BOUNDED_ACCEPTANCE

The declared YAML registry retains all historical dimensions for provenance and
legacy-reader compatibility, but `active_search_space` admits only members of
the four targeted families. Economics, costs, risk/safety and lifecycle-shadow
families are frozen. The generator yields the exact Set #2 baseline first,
one-factor sensitivity second, then bounded family/refinement/finalist stages.
It never materializes the Cartesian product and every evaluated row stores only
baseline identity plus overrides and research-config hash.

Set #2 file immutability anchor before/after this block:
`config/trading/trade_parameters.yaml` Git blob
`1a2260d5bf7139efb386e67a260e6ef2893aec54` (unchanged).
