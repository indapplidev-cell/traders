"""Authoritative server-owned bilingual contextual-help inventory.

The catalog is deliberately source-controlled and offline.  Stable page IDs are
the same IDs used by the client router; localized navigation text is never a key.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class LocalizedText:
    ru: str
    en: str

    def get(self, locale: str) -> str:
        return self.en if str(locale).lower().endswith("en") else self.ru


@dataclass(frozen=True, slots=True)
class HelpSection:
    section_id: str
    title: LocalizedText
    body: LocalizedText


@dataclass(frozen=True, slots=True)
class HelpTopic:
    page_id: str
    title: LocalizedText
    sections: tuple[HelpSection, ...]


def _s(section_id: str, ru_title: str, en_title: str, ru: str, en: str) -> HelpSection:
    return HelpSection(section_id, LocalizedText(ru_title, en_title), LocalizedText(ru, en))


COMMON_STATES = (
    "IDLE", "LOADING", "SUCCESS", "EMPTY", "ERROR", "UNKNOWN", "OK", "OFFLINE",
    "STALE", "DEGRADED", "NOT_AVAILABLE", "NOT_APPLICABLE", "AVAILABLE", "UNAVAILABLE",
    "READY", "NOT_READY", "HEALTHY", "UNHEALTHY", "WARNING", "CRITICAL", "INFO",
)
ANALYSIS_STATES = (
    "ANALYZED", "SKIPPED_NOT_ENOUGH_DATA", "SKIPPED_DEGRADED_MARKET_DATA",
    "SKIPPED_DUPLICATE_WINDOW", "SKIPPED_INVALID_SNAPSHOT",
)
SETUP_STATES = ("SETUP_CANDIDATE", "NO_SETUP", "WAIT_FOR_CONFIRMATION", "SETUP_INVALID")
INCIDENT_STATES = ("OPEN", "UPDATED", "RESOLVED")
PIPELINE_STATES = (
    "PENDING", "WAITING_FOR_REQUIRED_BOUNDARY", "READY_TO_RUN", "RUNNING", "COMPLETED",
    "SKIPPED", "MODULE_ERROR",
)
DIRECTION_STATES = ("BULLISH", "BEARISH", "NEUTRAL", "NONE")
PAPER_CANARY_STATES = (
    "NOT_CONFIGURED", "DISABLED", "RESERVED", "ARMED", "ARMED_WAITING",
    "NO_ELIGIBLE_APPROVAL", "WAITING_FOR_ELIGIBLE_APPROVAL", "RUNNING", "POSITION_OPEN",
    "POSITION_CLOSING", "POSITION_CLOSED", "RECONCILIATION_PENDING", "COMPLETED", "STOPPED",
    "FAILED_SAFE",
)
PAPER_POSITION_STATES = ("OPEN", "CLOSING", "CLOSED", "FAILED")
PAPER_SIDES = ("LONG", "SHORT")
PAPER_EXIT_CAUSES = ("STOP_LOSS", "TAKE_PROFIT", "SYSTEM_SAFETY_EXIT")
CONTROL_STATES = ("DISABLED", "ARMED", "EMERGENCY_STOP")
UNIVERSE_STATES = ("ACTIVE", "PREPARED_NOT_ACTIVE")
CRITERION_CLASSIFICATIONS = (
    "FIXED_THRESHOLD", "DYNAMIC_RULE", "DERIVED_VALUE", "BOOLEAN_GATE", "ENUM_ALLOWLIST",
    "NOT_CONFIGURED_AS_FIXED_THRESHOLD", "NOT_APPLICABLE",
)

DOCUMENTED_STATUS_TOKENS = frozenset(
    COMMON_STATES + ANALYSIS_STATES + SETUP_STATES + INCIDENT_STATES + PIPELINE_STATES
    + DIRECTION_STATES + PAPER_CANARY_STATES + PAPER_POSITION_STATES + PAPER_SIDES
    + PAPER_EXIT_CAUSES + CONTROL_STATES + UNIVERSE_STATES + CRITERION_CLASSIFICATIONS
    + ("READ_ONLY", "MOCK", "PRODUCTION_READONLY_HTTP", "NO_TRADE", "SAFE_FAILURE",
       "SCOPE_EXCEEDED", "NOT_DEPLOYED", "CURRENT", "WITHIN_GRACE", "PASS")
    + ("REJECTED", "DEFERRED", "NOT_REACHED")
)

PAGE_TABLE_COLUMNS = MappingProxyType({
    "Dashboard": ("symbol", "price", "data", "regime", "setup", "risk"),
    "Market": ("symbol", "price", "boundary", "data", "regime", "setup", "strategy", "risk"),
    "Trading Universe": ("symbol", "state", "market_data", "history", "analysis", "setup"),
    "Analysis": ("symbol", "regime", "direction", "confidence", "updated"),
    "Setups": ("symbol", "setup", "status", "quality", "direction", "updated"),
    "Trading Funnel": ("symbol", "stage", "status", "reason", "eligible", "rank", "updated"),
    "Incidents": ("id", "severity", "source", "title", "opened", "resolved"),
    "PAPER Trading": ("close", "symbol", "side", "capital", "net", "roi", "reason"),
    "Settings": (),
})

PAGE_CONTROLS = MappingProxyType({
    "Dashboard": ("refresh",),
    "Market": ("symbol_selector", "refresh"),
    "Trading Universe": ("refresh",),
    "Analysis": ("symbol_selector", "refresh"),
    "Setups": ("symbol_filter", "status_filter", "next", "refresh"),
    "Trading Funnel": ("refresh", "candidate_selection"),
    "Incidents": ("symbol_filter", "status_filter", "severity_filter", "next", "refresh"),
    "PAPER Trading": ("refresh", "arm_or_start", "disable", "emergency_stop", "clear_emergency_stop", "trade_selection", "next"),
    "Settings": ("language", "server_url", "provider_mode", "timeout", "paper_reporting_mode", "paper_control_mode", "paper_reporting_url", "paper_control_url", "help", "test_connection", "save_activate"),
})

PAPER_VISIBLE_INDICATORS = (
    "source", "live_disabled", "environment", "mode", "schema", "pitr", "wal", "market_data",
    "approval_source", "account_baseline", "accounting_reconciliation", "paper_reconciliation",
    "paper_runtime_enabled", "current_approval_availability", "current_mutation_ready", "live_allowed",
    "runtime_enabled", "daemon_enabled", "scheduler_enabled", "mutation_enabled", "control_state",
    "effective_state", "generation", "control_health", "audit_health", "workflow_state", "canary_state",
    "canary_id", "universe_version_id", "selection_policy_version", "command_id_count",
    "position_id_count", "last_action_error", "initial_balance", "current_balance", "gross_pnl",
    "total_fees", "net_pnl", "return_percent", "closed_trades", "wins", "losses", "breakeven",
    "win_rate", "profit_factor", "currency", "baseline_immutable", "position_symbol", "position_side",
    "position_state", "position_quantity", "entry_price", "entry_time", "stop_price", "target_price",
    "exit_cursor_status", "exit_decision", "position_count", "trade_report", "reconciliation_overall",
    "trading_criteria_summary", "trading_criteria_groups",
)

SHORTCUTS = MappingProxyType({
    "ru": ("Alt+О Dashboard", "Alt+Р Market", "Alt+П Trading Universe", "Alt+А Analysis",
           "Alt+С Setups", "Alt+В Trading Funnel", "Alt+И Incidents", "Alt+Т PAPER Trading", "Alt+Н Settings", "F5 active page"),
    "en": ("Alt+O Dashboard", "Alt+M Market", "Alt+P Trading Universe", "Alt+A Analysis",
           "Alt+C Setups", "Alt+F Trading Funnel", "Alt+I Incidents", "Alt+T PAPER Trading", "Alt+S Settings", "F5 active page"),
})

AUTO_REFRESH = MappingProxyType({
    "PAPER Trading": 10, "Dashboard": 30, "Market": 30, "Trading Universe": 30, "Trading Funnel": 10,
    "Analysis": 30, "Setups": 30, "Incidents": 60, "Settings": None, "Help": None,
})

_GLOBAL = HelpTopic("global", LocalizedText("Обзор приложения", "Application overview"), (
    _s("purpose", "Назначение", "Purpose",
       "Клиент показывает read-only API-состояние и отдельный PAPER Operator Control. Верхняя строка различает режим доступа провайдера и доменные статусы: «Только чтение» не является торговым состоянием.",
       "The client displays read-only API state and a separate PAPER Operator Control surface. The top line distinguishes provider access mode from domain status: Read-only is not a trading state."),
    _s("load", "Состояния загрузки", "Loading states",
       "IDLE — ещё не загружено; LOADING — запрос выполняется; SUCCESS — данные получены; EMPTY — корректный пустой результат; ERROR — запрос завершился ошибкой. UNKNOWN/NOT_AVAILABLE означают отсутствие подтверждённого значения, STALE — устаревшие данные, DEGRADED — частичное нарушение.",
       "IDLE means not loaded; LOADING is an in-flight request; SUCCESS is loaded data; EMPTY is a valid empty result; ERROR is a failed request. UNKNOWN/NOT_AVAILABLE mean no proven value, STALE means old data, and DEGRADED means partial impairment."),
    _s("refresh", "Обновление", "Refresh",
       "Опрос выполняется только для активной страницы и только существующим GET/read-only путём: PAPER 10 с; Обзор, Рынок, Торговые пары, Анализ и Сценарии 30 с; Инциденты 60 с; Настройки и Help — выкл. F5/кнопка сбрасывают отсчёт. Клиентский polling не управляет серверным торговым cadence.",
       "Only the active page polls, through its existing GET/read-only path: PAPER 10s; Overview, Market, Trading Pairs, Analysis and Scenarios 30s; Incidents 60s; Settings and Help Off. F5/the button reset the countdown. Client polling does not control server trading cadence."),
    _s("shortcuts", "Клавиатура", "Keyboard",
       "Alt+О — Обзор; Alt+Р — Рынок; Alt+П — Торговые пары; Alt+А — Анализ; Alt+С — Сценарии; Alt+И — Инциденты; Alt+Т — PAPER торговля; Alt+Н — Настройки. F5 обновляет активную страницу. Mutation hotkeys отсутствуют; при чувствительном modal/grab навигация и F5 подавляются.",
       "Alt+O — Overview; Alt+M — Market; Alt+P — Trading Pairs; Alt+A — Analysis; Alt+C — Scenarios; Alt+I — Incidents; Alt+T — PAPER Trading; Alt+S — Settings. F5 refreshes the active page. There are no mutation hotkeys; navigation and F5 are suppressed under a sensitive modal/grab."),
))

_TOPICS = (
    HelpTopic("Dashboard", LocalizedText("Обзор", "Overview"), (
        _s("purpose", "Назначение", "Purpose", "Сводка health, рынков, последних pipeline runs и числа нерешённых инцидентов.", "Summary of health, markets, recent pipeline runs, and unresolved incident count."),
        _s("source", "Источник", "Source", "GET /api/v1/health и GET /api/v1/dashboard через provider/controller state.", "GET /api/v1/health and GET /api/v1/dashboard through provider/controller state."),
        _s("blocks", "Блоки", "Blocks", "Connection API; Services: name/status/message; Markets — таблица Symbol/Price/Data/Regime/Setup/Risk; Latest activity: latest closed boundary, unresolved incident count, up to five run rows. Пустые списки дают пустую таблицу или явное сообщение.", "Connection API; Services: name/status/message; Markets is a Symbol/Price/Data/Regime/Setup/Risk table; Latest activity shows the latest closed boundary, unresolved incident count, and up to five run rows. Empty results use an empty table or an explicit message."),
        _s("controls", "Управление", "Controls", "Refresh/F5 — read-only refresh; auto-refresh 30 с.", "Refresh/F5 is read-only; auto-refresh is 30s."),
    )),
    HelpTopic("Market", LocalizedText("Рынок", "Market"), (
        _s("purpose", "Назначение", "Purpose", "Таблица GET /api/v1/markets и OHLC detail выбранного symbol из GET /api/v1/markets/{symbol}.", "GET /api/v1/markets table plus selected-symbol OHLC detail from GET /api/v1/markets/{symbol}."),
        _s("columns", "Колонки", "Columns", "Symbol; Price; Boundary; Data; Regime; Setup; Strategy из authoritative MarketSummary.strategy_status; Risk. Все доменные значения локализуются с сохранением raw-кода только для диагностики. Selector загружает detail; Refresh/F5 сохраняет выбор. Auto-refresh 30 с.", "Symbol; Price; Boundary; Data; Regime; Setup; Strategy from authoritative MarketSummary.strategy_status; Risk. Domain values are localized and raw codes are retained for diagnostics only. The selector loads detail; Refresh/F5 retains it. Auto-refresh is 30s."),
        _s("strategy", "Источник Strategy", "Strategy source", "Колонка Strategy больше не использует provider access mode READ_ONLY: она связана с per-symbol strategy_status server DTO.", "The Strategy column no longer uses the READ_ONLY provider access mode; it is bound to the per-symbol strategy_status server DTO."),
    )),
    HelpTopic("Trading Universe", LocalizedText("Торговые пары", "Trading Pairs"), (
        _s("purpose", "Назначение", "Purpose", "Read-only active/prepared universe из GET /api/v1/trading-universe; изменение или активация отсутствуют.", "Read-only active/prepared universe from GET /api/v1/trading-universe; there is no edit or activation action."),
        _s("columns", "Колонки", "Columns", "Symbol; State=ACTIVE или PREPARED_NOT_ACTIVE; Market data=ready_streams/6; History, Analysis, Setup=Готово/Не готово. Header показывает active_symbol_count/target_symbol_count и ready/target streams. При отсутствии snapshot — «не готово» и пустая таблица.", "Symbol; State=ACTIVE or PREPARED_NOT_ACTIVE; Market data=ready_streams/6; History, Analysis, Setup=Ready/Not ready. Header shows active/target symbols and ready/target streams. With no snapshot it shows Not ready and an empty table."),
        _s("controls", "Управление", "Controls", "Только Refresh/F5, auto-refresh 30 с.", "Refresh/F5 only; auto-refresh 30s."),
    )),
    HelpTopic("Trading Funnel", LocalizedText("Воронка поиска сделки", "Trading Funnel"), (
        _s("purpose", "Назначение", "Purpose",
           "Авторитетная read-only проекция GET /api/v1/trading/funnel для закрытого 15m cadence и активной вселенной. Панель не форсирует сделку, не меняет policy и не выполняет control actions.",
           "Authoritative read-only GET /api/v1/trading/funnel projection for the closed 15m cadence and active universe. The panel cannot force a trade, change policy, or invoke controls."),
        _s("cycles", "Циклы и окна", "Cycles and windows",
           "Текущий цикл может быть частичным и показывает processed/expected; последний завершённый цикл отдельный. Last 1h/4h включают boundary close в UTC-интервал [generated_at-window, generated_at].",
           "The current cycle may be partial and shows processed/expected; the last completed cycle is separate. Last 1h/4h include UTC boundary closes in [generated_at-window, generated_at]."),
        _s("stages", "Этапы", "Stages",
           "Analysis → Structural Setup → Strategy eligible → Risk approved → PaperTradePlan → Quantity approved → Validity approved → Final Approval → Eligible → Selector winner. Единица каждого счётчика — symbol. Final Approval означает существование immutable approval; Eligible отдельно означает текущий допуск и может стать false после expiry.",
           "Analysis → Structural Setup → Strategy eligible → Risk approved → PaperTradePlan → Quantity approved → Validity approved → Final Approval → Eligible → Selector winner. Every count unit is symbol. Final Approval is immutable approval existence; Eligible is separate current acceptance and may become false after expiry."),
        _s("statuses", "Статусы и причины", "Statuses and reasons",
           "Статусы и причины показываются операторскими формулировками. Исходный reason code сохраняется только в диагностических деталях.",
           "Statuses and reasons use operator-facing wording. The source reason code remains available only in diagnostic details."),
        _s("ranking", "Ранжирование", "Ranking",
           "Только текущие eligible approvals ранжируются неизменённым eligible-approval-ranking-v1; rank #1 — winner. Ноль eligible и winner=null — нормальное здоровое состояние.",
           "Only currently eligible approvals are ranked by unchanged eligible-approval-ranking-v1; rank #1 wins. Zero eligible and winner=null are normal healthy states."),
        _s("controls", "Управление", "Controls",
           "Refresh/F5 и auto-refresh 10 секунд выполняют только GET на активной странице. Ошибка production provider показывает unavailable/stale и никогда не подменяется Mock.",
           "Refresh/F5 and 10-second active-page auto-refresh perform GET only. A production-provider failure shows unavailable/stale and is never replaced with Mock."),
    )),
    HelpTopic("Analysis", LocalizedText("Анализ", "Analysis"), (
        _s("purpose", "Назначение", "Purpose", "Последний analysis snapshot выбранного symbol из GET /api/v1/analysis/{symbol}; список symbols приходит из markets.", "Latest analysis snapshot for a selected symbol from GET /api/v1/analysis/{symbol}; symbols come from markets."),
        _s("columns", "Колонки", "Columns", "Symbol; Regime (raw/UNKNOWN); Direction; Confidence как 0%..100% или —; Updated UTC. Возможные contract statuses анализа: ANALYZED, SKIPPED_NOT_ENOUGH_DATA, SKIPPED_DEGRADED_MARKET_DATA, SKIPPED_DUPLICATE_WINDOW, SKIPPED_INVALID_SNAPSHOT, ERROR, UNKNOWN; не все выводятся отдельной колонкой.", "Symbol; Regime (raw/UNKNOWN); Direction; Confidence as 0%..100% or —; Updated UTC. Contract analysis statuses are ANALYZED, SKIPPED_NOT_ENOUGH_DATA, SKIPPED_DEGRADED_MARKET_DATA, SKIPPED_DUPLICATE_WINDOW, SKIPPED_INVALID_SNAPSHOT, ERROR, UNKNOWN; not all have a dedicated visible column."),
        _s("controls", "Управление", "Controls", "Symbol selector и Refresh/F5; auto-refresh 30 с. В отсутствии market symbols UI предлагает BTCUSDT/ETHUSDT/SOLUSDT как client fallback (PARTIALLY_SUPPORTED, не server authority).", "Symbol selector and Refresh/F5; auto-refresh 30s. Without market symbols the UI offers BTCUSDT/ETHUSDT/SOLUSDT as a client fallback (PARTIALLY_SUPPORTED, not server authority)."),
    )),
    HelpTopic("Setups", LocalizedText("Сценарии", "Scenarios"), (
        _s("purpose", "Назначение", "Purpose", "Cursor-paged GET /api/v1/setups. Это аналитические setups, не ордера; API detail contract запрещает executable=true.", "Cursor-paged GET /api/v1/setups. These are analytical setups, not orders; the detail API contract rejects executable=true."),
        _s("columns", "Колонки", "Columns", "Symbol; Scenario; Status; Quality; Direction; Updated UTC. Scenario/status/direction показываются человекочитаемо из server catalog.", "Symbol; Scenario; Status; Quality; Direction; Updated UTC. Scenario, status, and direction are rendered from the server catalog."),
        _s("controls", "Управление", "Controls", "Symbol/status text filters; Refresh validates filters; Next активен только при next_cursor. Auto-refresh 30 с. Некорректные фильтры дают локальный ERROR.", "Symbol/status text filters; Refresh validates them; Next is enabled only with next_cursor. Auto-refresh 30s. Invalid filters produce a local ERROR."),
    )),
    HelpTopic("Incidents", LocalizedText("Инциденты", "Incidents"), (
        _s("purpose", "Назначение", "Purpose", "Cursor-paged GET /api/v1/incidents. Исторический OPEN/UPDATED incident не доказывает текущий outage: incident history/state != current service health.", "Cursor-paged GET /api/v1/incidents. A historical OPEN/UPDATED incident does not prove a current outage: incident history/state != current service health."),
        _s("columns", "Колонки", "Columns", "ID=incident_id; Severity=INFO/WARNING/ERROR/CRITICAL/UNKNOWN; Source; Title; Opened=opened_at UTC; Resolved=Да/Нет, вычисляется строго как status==RESOLVED. Contract status: OPEN, UPDATED, RESOLVED, UNKNOWN. resolved_at существует в contract, но отдельная timestamp-колонка UI отсутствует.", "ID=incident_id; Severity=INFO/WARNING/ERROR/CRITICAL/UNKNOWN; Source; Title; Opened=opened_at UTC; Resolved=Yes/No, strictly computed as status==RESOLVED. Contract status: OPEN, UPDATED, RESOLVED, UNKNOWN. resolved_at exists in the contract but has no timestamp column in this UI."),
        _s("controls", "Управление", "Controls", "Symbol/status/severity filters; Refresh; Next only with next_cursor; invalid filter=local ERROR; auto-refresh 60 с. Detail endpoint/model exists, but this table has no detail action (PARTIALLY_SUPPORTED UI reachability).", "Symbol/status/severity filters; Refresh; Next only with next_cursor; invalid filter=local ERROR; auto-refresh 60s. A detail endpoint/model exists, but this table has no detail action (PARTIALLY_SUPPORTED UI reachability)."),
    )),
    HelpTopic("PAPER Trading", LocalizedText("PAPER Торговля", "PAPER Trading"), (
        _s("purpose", "Назначение", "Purpose", "Reporting читает GET /api/v1/paper/*; Operator Control читает /control/v1/status и canary GET. LIVE всегда запрещён. Экран может выполнять только явно подтверждённые ARM/START/DISABLE/EMERGENCY/CLEAR действия; открытие Help ничего не вызывает.", "Reporting reads GET /api/v1/paper/*; Operator Control reads /control/v1/status and canary GETs. LIVE is always forbidden. The screen can perform only explicit ARM/START/DISABLE/EMERGENCY/CLEAR actions; opening Help invokes none."),
        _s("system", "System/readiness", "System/readiness", "Environment, mode, schema, PITR, WAL, adapters, reconciliation, runtime, Control, approval availability, next-ARM readiness и LIVE. Булевы значения контекстны: готово/не готово, включено/выключено, разрешено/запрещено. READY+NO_ELIGIBLE_APPROVAL — здоровое ожидание.", "Environment, mode, schema, PITR, WAL, adapters, reconciliation, runtime, Control, approval availability, next-ARM readiness, and LIVE. Booleans are contextual: ready/not ready, enabled/disabled, or allowed/forbidden. READY+NO_ELIGIBLE_APPROVAL is a healthy waiting state."),
        _s("control", "Runtime/control/canary", "Runtime/control/canary", "Основная панель показывает локализованные runtime/control/canary states, generation и точные canary/command/position links. Технические policy IDs не являются основным операторским статусом.", "The primary panel shows localized runtime, control, and canary states, generation, and exact canary/command/position links. Technical policy IDs are not a primary operator status."),
        _s("actions", "Mutation controls", "Mutation controls", "ARM доступен только при обоих соединениях, READY/current_mutation_ready, LIVE off, DISABLED и отсутствии активного canary; modal требует хотя бы один symbol и acknowledgement. START доступен только для exact healthy ARMED generation/canary links. Disable доступен при state!=DISABLED. Emergency Stop требует подтверждение и доступен при ARMED/active canary. Clear доступен только из EMERGENCY_STOP. Горячих клавиш нет; Help POST не выполняет.", "ARM requires both connections, READY/current_mutation_ready, LIVE off, DISABLED, and no active canary; its modal requires at least one symbol and acknowledgement. START requires exact healthy ARMED generation/canary links. Disable is enabled when state!=DISABLED. Emergency Stop requires confirmation and an ARMED/active canary. Clear is enabled only in EMERGENCY_STOP. There are no mutation hotkeys; Help performs no POST."),
        _s("account", "Account metrics", "Account metrics", "Initial/current balance; realized gross PnL; persisted fill fees; realized net PnL; return percent; closed/win/loss/breakeven counts; win rate; profit factor; currency; immutable baseline. Формулы принадлежат server accounting; UI не пересчитывает. Profit Factor nullable и тогда —. BASELINE_MISSING/PAPER_SCHEMA_NOT_DEPLOYED дают явное baseline message.", "Initial/current balance; realized gross PnL; persisted fill fees; realized net PnL; return percent; closed/win/loss/breakeven counts; win rate; profit factor; currency; immutable baseline. Formulas belong to server accounting; the UI does not recompute them. Profit Factor is nullable and then shows —. BASELINE_MISSING/PAPER_SCHEMA_NOT_DEPLOYED show an explicit baseline message."),
        _s("position", "Active position", "Active position", "Symbol, side LONG/SHORT, state OPEN/CLOSING/CLOSED/FAILED, quantity, entry price/time, stop, target, exit cursor status, exit decision, total position count. Без active detail — «нет активной позиции» и count. PnL/fees/timestamps сверх entry time существуют в contracts частично, но текущая active-position panel их не выводит (AUTHORITATIVE_DATA_UNAVAILABLE_IN_CURRENT_WIDGET для unrealized PnL/fees).", "Symbol, side LONG/SHORT, state OPEN/CLOSING/CLOSED/FAILED, quantity, entry price/time, stop, target, exit cursor status, exit decision, total position count. Without active detail it shows no active position and count. Additional PnL/fees/timestamps exist partly in contracts, but the current active-position panel does not render them (AUTHORITATIVE_DATA_UNAVAILABLE_IN_CURRENT_WIDGET for unrealized PnL/fees)."),
        _s("history", "Trade history", "Trade history", "7 колонок: Close time=exit_time UTC; Symbol; Side; Capital used; Net PnL; ROI; Exit reason. Double/single selection GETs authoritative final report; Next uses cursor. Empty history is an empty table. Exit reasons proven by domain: STOP_LOSS, TAKE_PROFIT, SYSTEM_SAFETY_EXIT.", "7 columns: Close time=exit_time UTC; Symbol; Side; Capital used; Net PnL; ROI; Exit reason. Single/double selection GETs the authoritative final report; Next uses the cursor. Empty history is an empty table. Domain-proven exit reasons: STOP_LOSS, TAKE_PROFIT, SYSTEM_SAFETY_EXIT."),
        _s("report", "Trade report", "Trade report", "trade_id/position_id, symbol, side, entry/exit timestamps, exit reason, quantity, entry/exit prices, capital used, entry/exit notionals, entry/exit/total fees, gross/net PnL, ROI, balance before/after, currency. No selection=No report; FINAL_REPORT_NOT_AVAILABLE=report pending.", "trade_id/position_id, symbol, side, entry/exit timestamps, exit reason, quantity, entry/exit prices, capital used, entry/exit notionals, entry/exit/total fees, gross/net PnL, ROI, balance before/after, currency. No selection=No report; FINAL_REPORT_NOT_AVAILABLE=report pending."),
        _s("reconciliation", "Reconciliation", "Reconciliation", "PAPER, Accounting и overall status. COMPLETED banner появляется только когда canary=COMPLETED и обе секции HEALTHY. Journal не имеет отдельного видимого поля в текущем widget: AUTHORITATIVE_DATA_UNAVAILABLE_IN_CURRENT_WIDGET.", "PAPER, Accounting, and overall status. The COMPLETED banner appears only when canary=COMPLETED and both sections are HEALTHY. Journal has no separate visible field in the current widget: AUTHORITATIVE_DATA_UNAVAILABLE_IN_CURRENT_WIDGET."),
        _s("criteria", "Trading criteria", "Trading criteria", "GET /api/v1/paper/trading-criteria: 17 source-owned groups rendered read-only. Каждая строка показывает key/value и classification: FIXED_THRESHOLD, DYNAMIC_RULE, DERIVED_VALUE, BOOLEAN_GATE, ENUM_ALLOWLIST, NOT_CONFIGURED_AS_FIXED_THRESHOLD или NOT_APPLICABLE. Это current server policy; canary-bound snapshot unavailable=false не следует трактовать как исторически замороженную policy.", "GET /api/v1/paper/trading-criteria: 17 source-owned groups rendered read-only. Each row shows key/value and classification: FIXED_THRESHOLD, DYNAMIC_RULE, DERIVED_VALUE, BOOLEAN_GATE, ENUM_ALLOWLIST, NOT_CONFIGURED_AS_FIXED_THRESHOLD, or NOT_APPLICABLE. This is current server policy; canary-bound snapshot unavailable=false must not be treated as a historically frozen policy."),
        _s("refresh", "Обновление/ошибки", "Refresh/errors", "Auto-refresh 10 с, active-page GET only. Reporting и Control имеют независимые AVAILABLE/UNAVAILABLE/IDLE connection states и независимые error codes. Production failure не переключается на Mock. Help выключает polling до закрытия.", "Auto-refresh 10s, active-page GET only. Reporting and Control have independent AVAILABLE/UNAVAILABLE/IDLE connection states and independent error codes. Production failure never falls back to Mock. Help turns polling off until closed."),
    )),
    HelpTopic("Settings", LocalizedText("Настройки", "Settings"), (
        _s("purpose", "Назначение", "Purpose", "Настройка locale, provider URL/mode/timeout и отдельных PAPER reporting/control modes/URLs. Auto-refresh выключен.", "Configures locale, provider URL/mode/timeout, and separate PAPER reporting/control modes/URLs. Auto-refresh is off."),
        _s("controls", "Управление", "Controls", "Language переключает RU/EN немедленно; Server URL; Provider mode MOCK/PRODUCTION_READONLY_HTTP; Timeout; PAPER modes MOCK/HTTP_DISABLED/PRODUCTION_HTTP; reporting/control URLs; Help; Test connection; Save & activate. Test connection выполняет только production read-only health request и не сохраняет/не активирует settings. Save validates and persists/activates. Ошибки validation показываются локально.", "Language switches RU/EN immediately; Server URL; Provider mode MOCK/PRODUCTION_READONLY_HTTP; Timeout; PAPER modes MOCK/HTTP_DISABLED/PRODUCTION_HTTP; reporting/control URLs; Help; Test connection; Save & activate. Test connection performs only a production read-only health request and does not save/activate settings. Save validates and persists/activates. Validation errors are local."),
        _s("security", "Безопасность", "Safety", "Control credential не вводится и не показывается в UI; production не делает fallback на Mock. F5 — no-op, mutation controls отсутствуют.", "The control credential is neither entered nor shown in the UI; production never falls back to Mock. F5 is a no-op and there are no mutation controls."),
    )),
    HelpTopic("Help", LocalizedText("Помощь", "Help"), (
        _s("navigation", "Навигация", "Navigation", "Выберите topic слева; справа — scrollable sections. Contextual ? открывает topic текущей main page. RU→EN→RU сохраняет stable topic ID. Escape/Close возвращает предыдущую polling page.", "Select a topic on the left; scroll its sections on the right. Contextual ? opens the current main-page topic. RU→EN→RU preserves the stable topic ID. Escape/Close restores the previous polling page."),
        _s("safety", "Read-only", "Read-only", "Help хранится offline, не polling-ит, не выполняет HTTP и не вызывает ARM/START/DISABLE/Emergency Stop/Clear.", "Help is offline, does not poll, performs no HTTP, and cannot invoke ARM/START/DISABLE/Emergency Stop/Clear."),
    )),
)

HELP_TOPICS = MappingProxyType({topic.page_id: topic for topic in (_GLOBAL,) + _TOPICS})
MAIN_PAGE_TOPIC_IDS = tuple(PAGE_TABLE_COLUMNS)


def get_topic(page_id: str) -> HelpTopic:
    return HELP_TOPICS[page_id]


def catalog_entries(locale: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for topic in HELP_TOPICS.values():
        prefix = f"help.topic.{topic.page_id}"
        entries[f"{prefix}.title"] = topic.title.get(locale)
        for section in topic.sections:
            section_prefix = f"{prefix}.section.{section.section_id}"
            entries[f"{section_prefix}.title"] = section.title.get(locale)
            entries[f"{section_prefix}.body"] = section.body.get(locale)
    return entries
