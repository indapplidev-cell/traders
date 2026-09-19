# Scalping PAPER bootstrap deadlock remediation 01

## Verdict

```text
FINAL_STATUS = FAIL_CLOSED
FINAL_VERDICT = ARCHITECTURE_AND_NATURAL_OPEN_PATH_PASS; CLOSED_INGESTION_RUNTIME_PROOF_NOT_OBSERVED_BY_USER_DIRECTION
PROJECT_STATE_COMMIT = 55d2614c2f79c5c9f770585163cb4ecb65505714
PROFILE = trade-5m-v2
PARAMETER_SET = scalping-v2-set-2
CONFIG_HASH = 9d3f604ee4a3b0793bb40ba3cef9826a36e00d945c44e60811cdeede6b1ee7ce
CONFIG_EPOCH = 49a943204a0be29b3ba7d6fa05d2417f6f53653600c2e286b32cf24090f427cc
YAML_CHANGED = false
LIVE_STATE = DISABLED
REAL_BINANCE_ORDER_CALLS = 0
FIFTEEN_MINUTE_BEHAVIOR_CHANGED = false
```

The implementation, integration, build, deployment and natural production
candidate-to-open path passed. The original acceptance also required waiting
for that position to close and proving a production sample increment. At the
user's explicit direction, waiting stopped while the position was still OPEN.
Therefore CLOSED, ingestion and production `0 -> 1` are not reported as PASS.

## Reproduced root cause

Before the change, `evaluate_expectancy()` returned
`INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE` whenever no compatible hierarchy
bucket reached 20 samples. `evaluate_scalping_shadow()` converted that result
to an expectancy rejection, so a cost-valid natural candidate could not
produce a plan, command, position, close or the first compatible observation.

```text
BOOTSTRAP_DEADLOCK_REPRODUCED = PASS
EXACT_BLOCKING_FUNCTION = app.engine_paper.scalping_policy_v2.evaluate_expectancy
EXACT_BLOCKING_CONDITION = no compatible exact/parent bucket has samples >= bucket_min_sample
CURRENT_SAMPLE_BEFORE = 0
REQUIRED_SAMPLE = 20
```

## Admission state machine

```text
all pre-empirical Scalping gates pass
  -> any compatible hierarchy bucket has sample >= 20?
       YES -> observed payoff distribution + conservative P(win)
              -> EVnet positive and all existing gates pass: EMPIRICAL
              -> otherwise: REJECT (never bootstrap)
       NO  -> PAPER_BOOTSTRAP, empirical EV/probability/AvgWin/AvgLoss remain null
              -> PAPER execution only; LIVE forbidden
```

Bootstrap is reached only after causal stop/target, normalized geometry,
authoritative account commission, spread/depth/slippage/adverse-fill costs,
positive net edge and the unchanged configured RR floor pass. It is not an
empirical RR pass: `rr_empirical_status=NOT_ESTABLISHED` and
`empirical_authority_status=NOT_ESTABLISHED`.

At sufficient sample, the existing conservative empirical formula is the
authority:

```text
EVnet = Pconservative(win) * observed AvgWin_net
        - (1 - Pconservative(win)) * observed AvgLoss_net
```

Tests prove that a compatible parent bucket prevents bootstrap, negative EV at
sample 20 cannot fall back to bootstrap, and a bootstrap admission cannot be
used with execution mode LIVE.

## Authoritative observation boundary

The production statistics adapter reads only unique CLOSED positions joined to
natural `trade-5m-v2` pipeline commands/results. It partitions by the active
parameter set and resolved config hash, correlates the result symbol, and
deduplicates by `position_id`. Prospective, counterfactual, replay, research,
parameter-sweep, v1, non-closed and incompatible-config records are excluded.
Net return is derived from realized position PnL and filled entry notional.

Persisted attribution now includes position, candidate/setup, plan and command
identity, parameter set, resolved config hash, config epoch, source/runtime
revision when available, and `admission_mode_at_entry`.

## Natural production proof captured before the stop instruction

```text
BOUNDARY = 1789834800000
SYMBOL = SOLUSDT
SETUP = SCALP_MOMENTUM_CONTINUATION
DIRECTION = BEARISH
ADMISSION_MODE = PAPER_BOOTSTRAP
EMPIRICAL_SAMPLE_BEFORE = 0
EMPIRICAL_REQUIRED_SAMPLE = 20
EMPIRICAL_EV = null
FEE_SOURCE = BINANCE_ACCOUNT_COMMISSION_SNAPSHOT
MODELED_TOTAL_COST_BPS = 22.89521508
PLAN_ID = paper:SOLUSDT:5m:1789834800000:risk:SOLUSDT:5m:1789834800000:strategy:v2:e867fba9760d12268c142fd3834a3d1e06bba9b9461dcb746e7e7d15b863a974:0b23e2c7d73e7f4c:82167e4cca88591e
COMMAND_ID = paper:ingestion-command:v1:67bc4edbfc598596e6881054f5ae68a2e2e27c6620cccba4baf7ad2ba07c4747
POSITION_ID = paper:continuous:position:48968843e65aa640cd0523a5f3562904019eacae86eec7a199afc0c6484d8ba6
POSITION_STATUS_AT_HANDOFF = OPEN
NATURAL_CLOSE = NOT_OBSERVED_BY_USER_DIRECTION
EMPIRICAL_SAMPLE_AFTER = 0_AT_HANDOFF_CLOSED_ONLY_SOURCE
EMPIRICAL_OBSERVATION_INGESTED = NOT_YET_POSITION_OPEN
DUPLICATE_INGESTION = 0
```

No symbol, candle, candidate, command or fill was injected. The normal
orchestrator, deterministic selector and controlled PAPER lifecycle produced
the plan, single command and single open position.

## Validation and deployment

```text
PY_COMPILE = PASS
FOCUSED_POLICY_STATISTICS_EXPORT = 43 passed; 1 skipped
ISOLATED_POSTGRESQL16_NATURAL_E2E = 18 passed
V2_EXPORT_AND_15M_V1_REGRESSION = 23 passed
EXPLICIT_15M_PARALLEL_AND_V1_REMOVAL = 11 passed
ALEMBIC_LOCAL_HEAD = 0031_scalping_parameter_sets
ALEMBIC_PRODUCTION_CURRENT = 0031_scalping_parameter_sets
BUILD = PASS; online-orchestrator-5m and readonly-api
DEPLOY = PASS; only online-orchestrator-5m and readonly-api recreated with --no-deps
RUNTIME_REVISION = 55d2614c2f79c5c9f770585163cb4ecb65505714
READONLY_HEALTH = OK; operational=true; ready=true
PAPER_READINESS = READY; CONTINUOUS_ARMED; current_mutation_ready=true
LIVE_PROHIBITION = live_allowed=false; LIVE domain BLOCKED; command schema PAPER-only
```

The broad server suite produced `177 passed, 7 skipped` and five failures from
pre-existing uncommitted `/api/v1/trading/config` route-inventory changes that
were outside this task and were not staged. Legacy test modules that attempt to
execute removed `trade-5m-v1` behavior fail at the explicit v2-only invariant;
they do not contribute runtime authority.

## Changed files

- `app/engine_paper/final_approval_materializer.py`
- `app/engine_paper/scalping_paper_runner.py`
- `app/engine_paper/scalping_policy_v2.py`
- `app/engine_paper/scalping_shadow.py`
- `app/engine_paper/scalping_statistics.py`
- `app/server_api/funnel_export.py`
- `app/server_api/trading_funnel.py`
- `tests/engine_paper/test_scalping_statistics.py`
- `tests/integration/paper_natural_execution_e2e/test_natural_approval_opens_position.py`
- `tests/integration/paper_natural_execution_e2e/test_probability_authority_accumulation_postgres.py`
- `tests/integration/paper_natural_execution_e2e/test_scalping_profitability_integration.py`
- `tests/server_api/test_funnel_export.py`
- `tests/test_15m_first_class_domain_remediation.py`
- `tests/test_probability_authority_accumulation.py`
- `tests/test_scalping_dynamic_ev_gate.py`
- `tests/test_scalping_independent_profile_v2.py`
- `tests/test_scalping_probability_fallback_hierarchy.py`
- `docs/audits/TRADERS_SCALPING_PAPER_BOOTSTRAP_DEADLOCK_REMEDIATION_01_FINAL.md`
- `online_trader.md`

