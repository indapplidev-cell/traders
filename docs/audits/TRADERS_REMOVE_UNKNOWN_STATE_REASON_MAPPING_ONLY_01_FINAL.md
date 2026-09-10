# Remove incorrect unknown-state reason mapping only 01

```text
TASK_STATUS = PASS
FINAL_VERDICT = PASS_KNOWN_MACHINE_REASON_RENDERED_AS_EXACT_READABLE_REASON

ROOT_CAUSE = READONLY_FUNNEL_ALREADY_PROJECTED_THE_EXACT_TERMINAL_MACHINE_REASON_BUT_THE_SERVER_OWNED_PUBLIC_I18N_CATALOG_DID_NOT_REGISTER_THREE_SCALPING_REASON_CODES; DESKTOP_REASON_LOOKUP_THEREFORE_USED_COMMON_UNKNOWN_STATE

SERVER_REASON_PRESENT_BEFORE = YES_TERMINAL_REASON_CODE_AND_EXACT_DOWNSTREAM_DETAIL_TERMINAL_REASON
CLIENT_MAPPING_PRESENT_BEFORE = NO_FOR_SCALPING_EMPIRICAL_EXPECTANCY_REJECTED_NET_BELOW_DYNAMIC_REQUIRED_INSUFFICIENT_PROBABILITY
UNKNOWN_FALLBACK_TRIGGER = MISSING_FUNNEL_REASON_I18N_KEY

FIX_SCOPE = SERVER_OWNED_PUBLIC_I18N_REASON_REGISTRY_PLUS_GENERATED_DESKTOP_BOOTSTRAP_AND_EXACT_REGRESSION_TESTS
TRADING_LOGIC_CHANGED = NO
YAML_CHANGED = NO
CONFIG_HASH_CHANGED = NO_49d89364e72d53aed0f59aa7ff9e7ce5335933049b3ff68f1221e1ba36496edf
STRATEGY_PARAMETERS_CHANGED = NO

KNOWN_REASON_CASES_TESTED = SCALPING_EMPIRICAL_EXPECTANCY_REJECTED; NET_BELOW_DYNAMIC_REQUIRED; INSUFFICIENT_PROBABILITY; SCALP_REJECT_CAUSAL_STOP_TOO_WIDE; NO_STRUCTURAL_SETUP
UNKNOWN_FOR_KNOWN_REASON_AFTER = 0

ROW_DETAIL_IDENTITY_PARITY = PASS_PROFILE_TIMEFRAME_CYCLE_BOUNDARY_SYMBOL_OPPORTUNITY_ID_AND_EXACT_TERMINAL_REASON

SERVER_TESTS = 43_PASSED
CLIENT_TESTS = FOCUSED_2_PASSED; FULL_1511_PASSED_2_SKIPPED_3029_SUBTESTS_WITH_2_TRANSIENT_TCL_INITIALIZATION_FAILURES_OUTSIDE_REASON_MAPPING_AND_TARGETED_RERUN_GREEN
COMPILE = SERVER_PASS_CLIENT_PASS

DEPLOYED_COMPONENTS = READONLY_API; DESKTOP_CLIENT_FROM_CLEAN_COMMITTED_WORKTREE
5M_ORCHESTRATOR_RESTARTED = NO
COLLECTOR_RESTARTED = NO
15M_RESTARTED = NO

LIVE_STATE = DISABLED
BINANCE_ORDER_CALLS = 0

SERVER_COMMIT = 4c6d23a7a17bf3d270e0c3b9e95ccf6391753106
CLIENT_COMMIT = 98928a6f6ce1d1dffb4b8af5e95acfc5dd591cf0
DOCUMENTATION_COMMIT = RESOLVE_WITH_GIT_LOG_1_FOR_THIS_FILE
PUSH = PASS
```

## Fresh production evidence

Before the fix, the current Readonly payload contained an exact rejected row
whose `terminal_reason_code` and exact detail `terminal_reason` were both
`SCALPING_EMPIRICAL_EXPECTANCY_REJECTED`, while the Desktop catalog had no
`funnel.reason.SCALPING_EMPIRICAL_EXPECTANCY_REJECTED` key. The existing
`TradingFunnelView._reason` implementation therefore selected
`common.unknown_state`; neither the API projection nor the row/detail binding
was defective.

After the Readonly-only deployment, catalog `i18n-2701aff5196dbe3d` exposes
the exact RU/EN labels. A fresh natural AVAXUSDT row at boundary
`1789065300000` preserved profile `trade-5m-v2`, timeframe `5m`, symbol,
source run, candidate, opportunity, cycle boundary and terminal reason parity;
its exact reason resolves to `Недостаточная ожидаемая доходность`. All known
reason rows in that production cycle resolved to non-unknown labels.

The Desktop was launched from clean committed client source at
`98928a6f6ce1d1dffb4b8af5e95acfc5dd591cf0`. Required PID/HWND preflight,
foreground activation and full-desktop cropped capture passed. The live Funnel
showed canonical real reasons such as `Структурный сценарий не найден` rather
than the generic fallback. Selected-row/detail capture used PID `16348`, HWND
`14551198` and SHA-256
`97F97A2B961C1AA42D9668827E360657DA170AC8240EDED973D2D07AB307FCEC`.
Exact expectancy rendering is additionally covered
by the production-shaped Tk row test and bilingual mapping test; a truly
unregistered future reason still uses `Неизвестное состояние`.

## Deployment isolation

Only `traders-readonly-api-readonly-api-1` was rebuilt and recreated, with
source identity `4c6d23a7a17bf3d270e0c3b9e95ccf6391753106` and image
`sha256:fa072aa5d78a238a499b4d94e8598d8a3dc63d33aa62d4b6e70fac22983613af`.
It is healthy with restart count zero. The 5m orchestrator, collector and
PostgreSQL container identities, start times and restart counts remained
unchanged; legacy 15m remained stopped. No strategy evaluator, configuration,
database reason, decision, readiness, PAPER execution semantics or order path
was changed.
