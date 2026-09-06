# TRADERS_SCALPING_V2_FOUR_INDEPENDENT_BLOCKS_INTEGRATE_DEPLOY_02 — BLOCK 4

TASK_STATUS = BLOCK_4_COMPLETE
FINAL_VERDICT = PASS
RECONCILED_AT_UTC = 2026-09-06T21:15:26.742Z

## Result

BLOCK_4_IMPLEMENTED = YES
BLOCK_4_INTEGRATED = YES
BLOCK_4_SMOKE = PASS
BLOCK_4_PRODUCTION_MUTATIONS = 0
BLOCK_4_FULL_SWEEP_RUN = NO
BLOCK_4_MANUAL_COMMAND_READY = YES
BLOCK_4_PUSHED = YES

IMPLEMENTATION_COMMIT = fb0b660535f56af4842ca94a80a51872ce10b678
IMPLEMENTATION_PUSH = PASS
SCHEMA_VERSION = SCALPING_V2_PARAMETER_SWEEP/2

## Integration

PARAMETER_SCHEMA = app.config.trade_parameters.StalePositionPolicyParameters
TIME_STOP_EVALUATOR = app.engine_paper.stale_position_shadow.evaluate_stale_position_shadow
SECOND_TIME_STOP_MATH_IMPLEMENTATION = NO
CURRENT_COMMISSION_SUBSTITUTED_FOR_HISTORY = NO
FUTURE_LEAKAGE_ALLOWED = NO
MISSING_EXACT_EVIDENCE_STATE = UNREPLAYABLE_OR_INSUFFICIENT_DATA

Supported search dimensions include:

- `soft_timeout_seconds`;
- `hard_timeout_seconds`;
- `min_target_progress_at_soft_timeout`;
- `min_mfe_bps_at_soft_timeout`;
- `min_remaining_ev_r_at_soft_timeout`;
- `extension_seconds`;
- `max_extensions`;
- `break_even_activation_target_progress`;
- `net_break_even_protection_enabled`.

The shared Pydantic runtime schema rejects hard timeout not above soft timeout, negative extension/max-extension values, zero-duration enabled extensions with a positive extension count, invalid progress ranges, negative MFE, and negative remaining EV thresholds.

## Metrics and report

REPORT_SECTION = TIME-STOP / STALE-POSITION ANALYSIS
BASELINE_AND_EVERY_CONFIG = YES
CALIBRATION_VALIDATION_HOLDOUT = YES
HOLDOUT_RANKING = NO
SAMPLE_SUFFICIENCY = EXPLICIT
PARETO_FRONTIER = VALIDATION_ONLY

Implemented output includes stale/soft/hard/break-even counts; holding average/p50/p90; baseline and time-stop PnL, expectancy, profit factor and maximum drawdown; fee totals/per-trade/delta; stale/capacity seconds saved; and candidate blocking/unblocking only when exact causal candidate evidence exists.

## Verification

RESEARCH_SUITE = 11_PASSED
TIME_STOP_AND_RESEARCH_FINAL_SET = 16_PASSED
EARLIER_COMBINED_POLICY_SET = 19_PASSED
COMPILEALL = PASS
GIT_DIFF_CHECK = PASS
INSTALLED_PROJECT_MODE = EDITABLE_INSTALL_FROM_CURRENT_CHECKOUT
INSTALLED_PROJECT_CLI = PASS

BOUNDED_SMOKE_CONFIGS = 2
BOUNDED_SMOKE_EXACT_SOURCE_COMMIT = fb0b660535f56af4842ca94a80a51872ce10b678
BOUNDED_SMOKE_DATASET = postgres-paper-outcomes-readonly
BOUNDED_SMOKE_SAMPLE_SIZES = calibration=31,validation=10,holdout=11
BOUNDED_SMOKE_REPORT = artifacts/scalping_v2_parameter_sweep/codex-smoke-20260907-time-stop-v4-exact-source/REPORT.md
FULL_SWEEP_RUN_BY_CODEX = NO

PRODUCTION_COUNTS_BEFORE = commands=54,orders=106,positions=53
PRODUCTION_COUNTS_AFTER = commands=54,orders=106,positions=53
PRODUCTION_MUTATIONS = 0
PRODUCTION_CONFIG_WRITES = 0
APPROVALS_CREATED = 0
COMMANDS_CREATED = 0
POSITIONS_CREATED = 0
BINANCE_ORDER_CALLS = 0

## Project/deployment decision

MODULE_KIND = OFFLINE_RESEARCH_CLI
PRODUCTION_SERVICE_RESTART_FOR_BLOCK_4 = NO
DEPLOYMENT_DECISION = NO_RESTART_REQUIRED_FOR_OFFLINE_CLI

The module runs from the current installed project environment and reads production outcomes through a read-only database binding. It is not a production daemon or request path, so restarting the healthy runtime solely for this offline tool would add risk without activating any runtime capability.

The running state remained unchanged:

- `trade-5m-v2` worker: running, Block 3 source `337124ca6e45a239b3113a487877bdca21f44fa4`;
- Readonly: healthy, Block 3 source `337124ca6e45a239b3113a487877bdca21f44fa4`;
- Operator: healthy, wiring-fix source `4cf697515a99d4ba283cf7f3c1853c81bb468546`;
- legacy 15m: stopped;
- LIVE: disabled.

## Manual handoff

MANUAL_SWEEP_COMMAND = python -m app.research.scalping_v2_parameter_sweep --config config/research/scalping_v2_parameter_sweep.yaml --run-id <manual-run-id>
MANUAL_REPORT_PATH = artifacts/scalping_v2_parameter_sweep/<manual-run-id>/REPORT.md

No optimum was selected, no parameter was promoted, and the manual full command was not executed by Codex.
