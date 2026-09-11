# Parameter Sweep v2 reporting/accounting bugs fix 01

```text
FINAL_STATUS = BLOCKED
FINAL_VERDICT = IMPLEMENTATION_AND_FOCUSED_PARITY_PASS; REQUIRED_EXISTING_126_CONFIG_RUN_REGENERATION_BLOCKED_BECAUSE_ITS_ARTIFACTS_ARE_ABSENT

# Scope

FILES_CHANGED = app/config/yaml_authority.py; config/research/research_parameters.yaml; traders_ml/parameter_sweep/artifact_v2.py; traders_ml/parameter_sweep/checkpoint.py; traders_ml/parameter_sweep/controller.py; traders_ml/parameter_sweep/engine.py; traders_ml/parameter_sweep/integrity.py; traders_ml/parameter_sweep/state.py; tests/research/test_parameter_sweep_report_semantics.py; tests/research/test_scalping_v2_parameter_sweep.py; docs/audits/TRADERS_PARAMETER_SWEEP_REPORTING_ACCOUNTING_BUGS_FIX_01_FINAL.md; online_trader.md
PRODUCTION_YAML_CHANGED = NO
RESEARCH_RANGES_CHANGED = NO
SEARCH_SPACE_CHANGED = NO; exact search_space SHA256 before/after a2797853fb70650b143c93184ef010a2ee0cf3d1202e8ad883f88898448fa6e8
TRADING_LOGIC_CHANGED = NO

# Forensic mismatch table before fix

FIELD | CANONICAL_OR_SOURCE | STATUS | REPORT | GUI | OTHER_ARTIFACT | EXPECTED | ROOT_CAUSE
accepted_count | RESULTS ACCEPTED=50 | 50 | checkpoint projection=50 | 50 projection | ACCEPTED_CONFIGS=50 reported | 50 | evaluation axis was only partly canonical
rejected_count | RESULTS REJECTED=76 | 0 | checkpoint projection=76 | 0 projection | REJECTED_CONFIGS=76 reported | 76 | insufficient performance count was subtracted from rejected evaluation count
insufficient_count | RESULTS performance_class INSUFFICIENT_SAMPLE=126 | 126 | 126 | 126 projection | checkpoint=126 | 126 | independent performance axis was mixed with evaluation axis
symbol_coverage | FINALIST validation trades contain 5 distinct named symbols | readiness current=0 | readiness current=0 | status projection=0 | compact RESULTS=0 reported | 5 | compact result trusted summary zero instead of exact validation trades
setup_coverage | FINALIST validation trades contain at least SCALP_MOMENTUM_CONTINUATION | readiness/result current=0 | current=0 | status projection=0 | compact RESULTS=0 reported | at least 1 | compact result trusted summary zero instead of exact validation trades
independent_period_count | validation trades have timestamps but no authoritative bucket implementation existed | 0 | 0 | status projection=0 | compact RESULTS=0 reported | derived from configured bucket or DATA_INCOMPLETE | absent definition and silent `or 0`
seed | top-level RUN_CONFIG input=20260906; planner/sampler=20260907 | not serialized | 20260907 | not shown | SEARCH_PLAN=20260907 | one resolved value | two config fields had different meanings without names

FORENSIC_SOURCE = user-confirmed successful ALL run facts plus pre-fix source trace; run files are not present in the workspace
EXISTING_RUN_ARTIFACT_DISCOVERY = BLOCKED; artifacts/scalping_v2_parameter_sweep is empty and repository-wide no-ignore search found no RESULTS.jsonl, STATUS.json, FINALIST_TRADES.jsonl, or RUN_CONFIG.yaml

# Evaluation status

EVALUATION_ACCEPTED = 50 known-run canonical input; focused 126-row regression recomputes 50
EVALUATION_REJECTED = 76 known-run canonical input; focused 126-row regression recomputes 76
EVALUATION_ERRORS = 0

PERFORMANCE_CLASS_COUNTS = {INSUFFICIENT_SAMPLE: 126} known-run canonical input; focused 126-row regression matches

STATUS_RESULTS_PARITY = PASS_FOCUSED_SMOKE; BLOCKED_EXISTING_RUN_REGENERATION
REPORT_RESULTS_PARITY = PASS_FOCUSED_SMOKE; BLOCKED_EXISTING_RUN_REGENERATION
GUI_RESULTS_PARITY = PASS_FOCUSED_EVENT_PROJECTION; BLOCKED_EXISTING_RUN_REGENERATION

# Coverage

SAMPLE_CONFIG_ID = focused-regression-config-7; existing-run config id unavailable with missing artifacts
VALIDATION_TRADES = 21
DISTINCT_SYMBOLS = 5; ADAUSDT,DOGEUSDT,LINKUSDT,SUIUSDT,XRPUSDT
REPORTED_SYMBOL_COVERAGE = before 0; after 5 in focused regression
DISTINCT_SETUPS = 2 in focused missing-setup regression; UNKNOWN plus SCALP_MOMENTUM_CONTINUATION
REPORTED_SETUP_COVERAGE = before 0; after 2 in focused regression

SYMBOL_COVERAGE_PARITY = PASS_FOCUSED_REGRESSION; BLOCKED_EXISTING_RUN_REGENERATION
SETUP_COVERAGE_PARITY = PASS_FOCUSED_REGRESSION; BLOCKED_EXISTING_RUN_REGENERATION

# Independent periods

INDEPENDENT_PERIOD_DEFINITION = distinct UTC calendar dates of canonical validation trade opened_at_ms, falling back to canonical boundary_ms
INDEPENDENT_PERIOD_SOURCE = config/research/research_parameters.yaml ranking.independent_period_unit=UTC_CALENDAR_DAY; existing dataset manifest already uses the same UTC-date boundary under composition.time_period_utc_date
SAMPLE_TRADE_TIMESTAMPS = 2026-09-01T00:00:00Z; 2026-09-02T00:00:00Z; 2026-09-03T00:00:00Z repeated across 21 validation trades
SAMPLE_PERIOD_BUCKETS = 2026-09-01; 2026-09-02; 2026-09-03
REPORTED_INDEPENDENT_PERIOD_COUNT = before 0; after 3 in focused regression
INDEPENDENT_PERIOD_PARITY = PASS_FOCUSED_REGRESSION; missing timestamp produces DATA_INCOMPLETE and null, never silent zero; BLOCKED_EXISTING_RUN_REGENERATION

# Readiness

INSUFFICIENT_SAMPLE_GATES_BEFORE = known sample validation_trade_count current=21 required=20 PASS; symbol_coverage current=0 required=3 FAIL; independent_period_count current=0 required=3 FAIL
INSUFFICIENT_SAMPLE_GATES_AFTER = focused sample validation_trade_count current=21 required=20 PASS; symbol_coverage current=5 required=3 PASS and omitted from failures; independent_period_count current=3 required=3 PASS and omitted from failures
READINESS_GATE_VALUES_CORRECT = PASS_FOCUSED_REGRESSION; BLOCKED_EXISTING_RUN_REGENERATION

# Seed

REQUESTED_SEED = before ambiguous 20260906 top-level and 20260907 search; after 20260907
RESOLVED_SEED = 20260907
SAMPLER_SEED = 20260907
MANIFEST_SEED = 20260907
REPORT_SEED = 20260907
STATUS_SEED = 20260907
RESUME_SEED = 20260907

SEED_PROVENANCE_PARITY = PASS_FOCUSED_SMOKE; integrity covers RUN_CONFIG, RUN_MANIFEST, SEARCH_PLAN, CHECKPOINT, STATUS, REPORT, RESULTS, accepted/rejected, finalist trades, and OPPORTUNITY_FUNNEL; BLOCKED_EXISTING_RUN_REGENERATION
SEED_RESUME_PARITY = PASS; same seed compatible and different resolved seed rejected

# Cross artifact

FINALIST_TRADES_COVERAGE_PARITY = PASS_FOCUSED_SMOKE; BLOCKED_EXISTING_RUN_REGENERATION
COUNTERFACTUAL_PARITY = PASS_FOCUSED_REGRESSION
NULL_CONFIG_METADATA = PASS_FOCUSED_REGRESSION

# Safety

ACTIVE_SET2_CHANGED = NO; fresh readonly runtime active_parameter_set=scalping-v2-set-2 and resolved_config_hash=49d89364e72d53aed0f59aa7ff9e7ce5335933049b3ff68f1221e1ba36496edf
PRODUCTION_DEPLOY = NO
LIVE_STATE = FALSE; fresh readonly runtime mode=PAPER and live_allowed=false
BINANCE_ORDER_CALLS = 0
PRODUCTION_MUTATIONS = 0

# Delivery

FOCUSED_TESTS = PASS; final rerun 106 passed in 80.91s
COMPILE = PASS; python -m compileall -q traders_ml/parameter_sweep app/research/scalping_v2_parameter_sweep.py app/config/yaml_authority.py
COMMITS = project-state 01645845350947b902ce4d5ed2baa40f4a57ad31; documentation reconciliation resolve from Git history
PUSH = PASS after documentation reconciliation commit
AHEAD_BEHIND = 0/0 after final push
WORKTREE = CLEAN after final push

REMAINING_BLOCKERS = latest successful ALL run artifacts are absent, so its exact post-fix coverage, independent-period buckets, regenerated STATUS/REPORT/GUI projection, and all real-run parity gates cannot be verified without restoring that run directory
NEXT_RECOMMENDED_ACTION = restore the exact successful 126-config run directory and run report-only regeneration/integrity; do not launch a new large sweep, tune parameters, create Set #3, deploy production, or enable LIVE
```

The implementation has one reporting flow: compact canonical config results feed
`aggregate_result_semantics`, and STATUS, REPORT, GUI events, checkpoint,
opportunity funnel, and integrity assertions consume that result. Evaluation
status and performance class are independent axes. Coverage, wins/losses, and
period buckets come from the same validation trade list whenever that list is
present; a missing setup is serialized as `UNKNOWN`, and a missing period
timestamp is explicit `DATA_INCOMPLETE`.

No large sweep or production deployment was performed.
