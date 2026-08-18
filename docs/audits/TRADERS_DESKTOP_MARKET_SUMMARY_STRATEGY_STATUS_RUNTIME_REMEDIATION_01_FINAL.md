# TRADERS_DESKTOP_MARKET_SUMMARY_STRATEGY_STATUS_RUNTIME_REMEDIATION_01

## Final decision

```text
TASK_STATUS = COMPLETED
FINAL_VERDICT = PASS_TRADERS_DESKTOP_MARKET_SUMMARY_STRATEGY_STATUS_RUNTIME_REMEDIATION_01_COMPLETED
BLOCKER_CODE = NONE
SECONDARY_BLOCKER = NONE
STOP_CONDITION = NONE

DESKTOP_BRANCH_BEFORE = main
DESKTOP_HEAD_BEFORE = 0f69d575a8cb53b0cfc1a61799e622e710d5d291
DESKTOP_TREE_BEFORE = 142d51262265aed6678195d9eed5ec161d6cf3d3
DESKTOP_ROOT_CLEAN_BEFORE = YES
SERVER_BRANCH_BEFORE = feature/engine-platform
SERVER_HEAD_BEFORE = 77c023115c9ee5ee20f3895dd9e58b557c0f0ac5
SERVER_TREE_BEFORE = 8baeb650cfd33cd9f5fb8caff8e0a0549eca0314
SERVER_ROOT_CLEAN_BEFORE = YES
MOBILE_BRANCH_BEFORE = main
MOBILE_HEAD_BEFORE = 013ff7327a3a2d2bfd9e1aa7b216bf6ccaa497db
MOBILE_TREE_BEFORE = f791937049c431725718b4a26ce7e23b2a3ea4ec
MOBILE_ROOT_CLEAN_BEFORE = YES

DEFECT_REPRODUCED = YES
DEFECT_EXCEPTION_TYPE = AttributeError
DEFECT_EXCEPTION_MESSAGE = 'MarketSummary' object has no attribute 'strategy_status'
DEFECT_REPRODUCTION_PATH = real-shaped Markets item -> parse_market_summary -> MarketSummary.strategy_status

SERVER_MARKETS_SCHEMA_SOURCE = app/server_api/schemas/models.py:102
SERVER_STRATEGY_STATUS_FIELD_SOURCE = app/server_api/schemas/models.py:111; app/server_api/mapping/contract.py:96; app/engine_strategy/strategy_status.py
DESKTOP_MARKETS_TRANSPORT_SOURCE = src/traders_client/transport; src/traders_client/providers/server_provider.py:221
DESKTOP_MARKETS_PARSER_SOURCE = src/traders_client/api_contract/parsing.py:265
DESKTOP_MARKET_SUMMARY_MODEL_SOURCE = src/traders_client/api_contract/models.py:111
DESKTOP_MARKET_VIEW_SOURCE = src/traders_client/ui/market_view.py:12
DESKTOP_STRATEGY_PRESENTATION_SOURCE = src/traders_client/i18n/service.py:95; src/traders_client/ui/market_view.py:92
END_TO_END_STRATEGY_STATUS_TRACE_COMPLETE = YES

STRATEGY_STATUS_REQUIRED_BY_SERVER_CONTRACT = NO
STRATEGY_STATUS_NULLABLE_BY_SERVER_CONTRACT = YES
STRATEGY_STATUS_PUBLIC_VALUES = ALLOW_RESEARCH_TRADE_PLAN, REJECT, WAIT, NO_DECISION, ERROR

ROOT_CAUSE_PRIMARY = PARSER_MODEL_CONTRACT_PROPAGATION_OMISSION
ROOT_CAUSE_SECONDARY = MarketView consumed strategy_status ahead of DTO/parser; source-inspection tests and payload fixtures did not exercise the real row
ROOT_CAUSE_CONFIRMED = YES

MARKET_SUMMARY_HAS_STRATEGY_STATUS = YES
MARKET_SUMMARY_STRATEGY_STATUS_TYPE_MATCHES_SERVER = YES_STR_OR_NONE
STRATEGY_STATUS_RAW_VALUE_PRESERVED = YES
STRATEGY_STATUS_TRANSLATED_IN_PARSER = NO
MARKET_STRATEGY_COLUMN_USES_ACCESS_MODE = NO
MARKET_STRATEGY_PRESENTATION_USES_SERVER_I18N = YES
DESKTOP_NEW_LOCAL_STRATEGY_TRANSLATION_MAP_ADDED = NO
STRATEGY_STATUS_I18N_NAMESPACE_REUSED = YES
STRATEGY_STATUS_MISSING_FIELD_POLICY_MATCHES_SERVER_CONTRACT = YES_MISSING_OR_NULL_TO_NONE_UI_EXISTING_NOT_AVAILABLE_LABEL

UNKNOWN_STRATEGY_STATUS_CRASHES_UI = NO
UNKNOWN_STRATEGY_STATUS_RAW_CODE_DIAGNOSTIC_AVAILABLE = YES
KNOWN_STRATEGY_RAW_CODES_IN_PRIMARY_UI = 0

MARKET_SUMMARY_FIXTURES_UPDATED = YES
MARKETS_PARSER_STRATEGY_STATUS_TESTS = PASS
MARKETS_PROVIDER_STRATEGY_STATUS_CONTRACT_TEST = PASS
MARKETVIEW_RU_STRATEGY_STATUS_TEST = PASS
MARKETVIEW_EN_STRATEGY_STATUS_TEST = PASS
MARKET_STRATEGY_ACCESS_MODE_REGRESSION_TEST = PASS
MARKETVIEW_10_SYMBOL_STRATEGY_MATRIX = PASS
MARKET_ROW_PRESENTATION_REGRESSION = PASS
OVERVIEW_MARKETS_COMPATIBILITY = PASS

SERVER_I18N_AUTHORITY_PRESERVED = YES
DESKTOP_GENERATED_BOOTSTRAP_PRESERVED = YES
DESKTOP_LKG_CACHE_PRESERVED = YES
DESKTOP_INDEPENDENT_DOMAIN_TRANSLATION_DICTIONARY = NO

DEFECT_REPRODUCTION_PATH_AFTER = PASS
ATTRIBUTEERROR_AFTER_REMEDIATION = NO
DESKTOP_MARKET_FOCUSED_TESTS = PASS_86_PASSED_34_SUBTESTS
DESKTOP_FULL_REGRESSION = PASS
DESKTOP_FULL_TEST_COUNT = 1447_PASSED_2_SKIPPED_3029_SUBTESTS
DESKTOP_GUI_SMOKE_LOCAL = PASS_RU_EN_9_PAGES_MARKET_OVERVIEW_STRATEGY_HUMANIZED_CLEAN_CLOSE
DESKTOP_PRODUCTION_MARKET_GUI_SMOKE = NOT_PERFORMED_NOT_BLOCKING_SOURCE_TASK
PRODUCTION_GET_ONLY_API_CORROBORATION = PASS_HEALTH_OK_MARKETS_10_OF_10_HAVE_STRATEGY_STATUS_MANIFEST_IDENTITY_UNCHANGED

READONLY_CONTAINER_REPLACEMENTS_BY_TASK = 0
SERVER_SOURCE_CHANGED = NO
SERVER_RUNTIME_CHANGED = NO
MOBILE_SOURCE_CHANGED = NO
PRODUCTION_DATABASE_MUTATIONS_BY_TASK = 0
PRODUCTION_CONTROL_MUTATIONS_BY_TASK = 0
PRODUCTION_TRADING_MUTATIONS_BY_TASK = 0
EXISTING_CANARY_CONTROL_MUTATIONS_BY_TASK = 0
BINANCE_ORDER_API_CALLS_BY_TASK = 0
LIVE_MODE_CHANGED_BY_TASK = NO
PRODUCTION_SERVICE_RESTARTS_BY_TASK = 0
WAL_PITR_MUTATIONS_BY_TASK = 0

SECRET_OUTPUT_BY_TASK = 0
PROTECTED_SECRET_VALUE_OUTPUT = 0
SECRET_LOGGING_IMPLEMENTED = NO
PUSHED = NO
NEXT_ACTION = RETRY_TRADERS_SERVER_AUTHORITATIVE_I18N_READONLY_RUNTIME_DEPLOYMENT_ACCEPTANCE_01
```

## Implementation and validation

The authoritative server Pydantic schema defines `strategy_status` as an
optional nullable string and the mapping passes through the persisted value.
The declared public strategy vocabulary is the five-value `StrategyStatus`
enum. Desktop now adds that exact nullable raw value to the slotted immutable
DTO and maps the optional JSON field without translation or inference.

Known non-null values flow through `TranslationService.domain_label()` using
the existing `strategy.status` namespace. Missing/null uses the existing
server-catalog `market.data.NOT_AVAILABLE` neutral label; unknown non-null
future codes render the existing generic localized unknown-state label while
remaining on `MarketSummary` and available through `raw_diagnostic()`.

The focused suite covered representative values, missing/null/invalid input,
the provider boundary, RU/EN view rendering, explicit Production Readonly HTTP
access-mode separation, all ten trading-universe symbols, all eight Market row
columns, and Overview compatibility. The final full suite and both standard Tk
GUI smokes passed. The GUI harness was reconciled with the already-established
server-authoritative i18n startup: its single catalog refresh is locally
stubbed, while all network and socket calls remain forbidden.

No server or mobile source, database, runtime, container, Control, trading,
canary, LIVE, WAL/PITR, listener, or secret state was changed. Three bounded
GETs corroborated that the preserved runtime remained healthy, all ten Markets
rows exposed the field, and the deployed catalog identity remained
`i18n-8792dfefd2e4e0fa` /
`8792dfefd2e4e0fabd8251263c8d093282e372ba6d794d7b9a5df0cb7b101884`.

The next task is acceptance-only runtime reacceptance when the current runtime
identity still matches; no Readonly replacement is warranted in that case.
