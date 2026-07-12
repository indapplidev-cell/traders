from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TerminalCommandExample:
    title: str
    purpose: str
    command: str
    output: str


_CURRENT_TERMINAL_COMMAND = """python -m app.cli.commands book-l1-interactive-preview `
  --symbol BTCUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50"""

_CURRENT_JSON_COMMAND = """python -m app.cli.commands book-l1-preview `
  --symbol BTCUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50"""

_API_PREVIEW_COMMAND = """python -m app.cli.commands book-l1-api-preview `
  --symbol BTCUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50"""

_MULTI_PREVIEW_COMMAND = """python -m app.cli.commands book-l1-multi-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --non-interactive"""

_HISTORY_PREVIEW_COMMAND = """python -m app.cli.commands book-l1-history-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --non-interactive"""

_HISTORY_DETAILS_COMMAND = """python -m app.cli.commands book-l1-history-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --non-interactive `
  --show-details"""

_TIMELINE_PREVIEW_COMMAND = """python -m app.cli.commands book-l1-timeline-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --non-interactive"""

_TIMELINE_DETAILS_COMMAND = """python -m app.cli.commands book-l1-timeline-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --non-interactive `
  --show-details"""

_CURRENT_EXPORT_COMMAND = """python -m app.cli.commands book-l1-preview `
  --symbol BTCUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --export-json"""

_MULTI_EXPORT_COMMAND = """python -m app.cli.commands book-l1-multi-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --non-interactive `
  --export-json"""

_HISTORY_EXPORT_COMMAND = """python -m app.cli.commands book-l1-history-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --limit 300 `
  --min-candles 50 `
  --non-interactive `
  --export-json"""

_TIMELINE_EXPORT_COMMAND = """python -m app.cli.commands book-l1-timeline-preview `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --non-interactive `
  --export-json"""

_JSON_CONSUMER_SMOKE_COMMAND = "python -m app.cli.commands book-l1-json-consumer-smoke --strict"

_L2_CONTEXT_COMMAND = "python -m app.cli.commands book-l2-timeline-context --strict --show-details --export"

_L2_JSON_CONSUMER_SMOKE_COMMAND = "python -m app.cli.commands book-l2-json-consumer-smoke --strict"

_L2_API_READINESS_REVIEW_COMMAND = "python -m app.cli.commands book-l2-api-readiness-review --strict"

_L1_L2_INTERVAL_ANSWER_SMOKE_COMMAND = """python -m app.cli.commands book-l1-l2-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details"""

_L1_L2_MULTI_INTERVAL_ANSWER_SMOKE_COMMAND = """python -m app.cli.commands book-l1-l2-multi-interval-answer-smoke `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details"""

_DATA_AVAILABILITY_AUDIT_COMMAND = """python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --show-details"""

_DATA_AVAILABILITY_AUDIT_STRICT_COMMAND = """python -m app.cli.commands book-data-candle-availability-audit `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --intervals 15m,1h,4h `
  --window-size 300 `
  --window-count 4 `
  --strict `
  --show-details"""

_DATA_PREPARATION_DECISION_COMMAND = "python -m app.cli.commands book-data-interval-preparation-decision --show-details"

_DATA_PREPARATION_DECISION_STRICT_COMMAND = (
    "python -m app.cli.commands book-data-interval-preparation-decision --strict --show-details"
)

_DATA_15M_STABILIZATION_COMMAND = """python -m app.cli.commands book-data-15m-stabilization `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details"""

_L1_15M_QUALITY_REVIEW_COMMAND = """python -m app.cli.commands book-l1-15m-quality-review `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --window-size 300 `
  --window-count 4 `
  --min-candles 50 `
  --strict `
  --show-details"""

_L1_L2_REGIME_ALIGNMENT_REVIEW_COMMAND = """python -m app.cli.commands book-l1-l2-regime-alignment-review `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details"""

_L1_FLAT_CONTEXT_ALIGNMENT_DIAGNOSTIC_COMMAND = """python -m app.cli.commands book-l1-flat-context-alignment-diagnostic `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --strict `
  --show-details"""

_L2_FLAT_CONTEXT_HANDLING_PROPOSAL_COMMAND = """python -m app.cli.commands book-l2-flat-context-handling-proposal `
  --symbols BTCUSDT,ETHUSDT,SOLUSDT `
  --interval 15m `
  --high-confidence-threshold 0.80 `
  --strict `
  --show-details"""

_API_READINESS_REVIEW_COMMAND = "python -m app.cli.commands book-l1-api-readiness-review"

_GUIDE_COMMAND = "python -m app.cli.commands book-l1-guide"


def get_book_l1_terminal_command_examples() -> tuple[str, ...]:
    """Return canonical command examples used by guide and tests."""
    return (
        _GUIDE_COMMAND,
        _CURRENT_TERMINAL_COMMAND,
        _CURRENT_JSON_COMMAND,
        _API_PREVIEW_COMMAND,
        _MULTI_PREVIEW_COMMAND,
        _HISTORY_PREVIEW_COMMAND,
        _HISTORY_DETAILS_COMMAND,
        _TIMELINE_PREVIEW_COMMAND,
        _TIMELINE_DETAILS_COMMAND,
        _CURRENT_EXPORT_COMMAND,
        _MULTI_EXPORT_COMMAND,
        _HISTORY_EXPORT_COMMAND,
        _TIMELINE_EXPORT_COMMAND,
        _JSON_CONSUMER_SMOKE_COMMAND,
        _L2_CONTEXT_COMMAND,
        _L2_JSON_CONSUMER_SMOKE_COMMAND,
        _L2_API_READINESS_REVIEW_COMMAND,
        _L1_L2_INTERVAL_ANSWER_SMOKE_COMMAND,
        _L1_L2_MULTI_INTERVAL_ANSWER_SMOKE_COMMAND,
        _DATA_AVAILABILITY_AUDIT_COMMAND,
        _DATA_AVAILABILITY_AUDIT_STRICT_COMMAND,
        _DATA_PREPARATION_DECISION_COMMAND,
        _DATA_PREPARATION_DECISION_STRICT_COMMAND,
        _DATA_15M_STABILIZATION_COMMAND,
        _L1_15M_QUALITY_REVIEW_COMMAND,
        _L1_L2_REGIME_ALIGNMENT_REVIEW_COMMAND,
        _L1_FLAT_CONTEXT_ALIGNMENT_DIAGNOSTIC_COMMAND,
        _L2_FLAT_CONTEXT_HANDLING_PROPOSAL_COMMAND,
        _API_READINESS_REVIEW_COMMAND,
    )


def build_book_l1_terminal_guide() -> str:
    """Return human-readable BOOK-L1 terminal command guide."""
    examples = (
        TerminalCommandExample(
            title="1. Current single-symbol terminal preview",
            purpose="Quickly inspect the current regime for one symbol in the terminal.",
            command=_CURRENT_TERMINAL_COMMAND,
            output="symbol, interval, candle count, market_regime, directional_bias, confidence, trend_strength, reason_codes, safety",
        ),
        TerminalCommandExample(
            title="2. Current single-symbol JSON preview",
            purpose="Print machine-readable JSON for one symbol to stdout.",
            command=_CURRENT_JSON_COMMAND,
            output="Single-symbol JSON preview payload.",
        ),
        TerminalCommandExample(
            title="3. API/service response preview",
            purpose="Check the service/API response contract for one symbol.",
            command=_API_PREVIEW_COMMAND,
            output="Single-symbol API response JSON payload.",
        ),
        TerminalCommandExample(
            title="4. Multi-symbol current preview",
            purpose="Compare the current regime of several symbols.",
            command=_MULTI_PREVIEW_COMMAND,
            output="Symbol | Status | Regime | Bias | Confidence | Trend | Safety",
        ),
        TerminalCommandExample(
            title="5. Previous/current history snapshot",
            purpose="Compare previous window vs current window.",
            command=_HISTORY_PREVIEW_COMMAND,
            output="Symbol | Previous | Current | Transition | Prev Conf | Curr Conf | Safety",
        ),
        TerminalCommandExample(
            title="6. Multi-window timeline preview",
            purpose="Show the regime timeline W-3 -> W-2 -> W-1 -> Current.",
            command=_TIMELINE_PREVIEW_COMMAND,
            output="Symbol | W-3 | W-2 | W-1 | Current | Stability | Last Change | Curr Conf | Safety",
        ),
    )

    sections = [
        "BOOK-L1 Terminal Command Guide",
        "",
        "Open this guide:",
        _GUIDE_COMMAND,
        "",
        "Working model:",
        "- Terminal output is for humans.",
        "- JSON export is for API.",
        "- JSON consumer smoke validates stable JSON files before API consumption.",
        "- Runtime Markdown export is not used.",
        "",
        "Modes:",
        "1. Current single-symbol terminal preview",
        "2. Current single-symbol JSON preview",
        "3. API/service response preview",
        "4. Multi-symbol current preview",
        "5. Previous/current history snapshot",
        "6. Multi-window timeline preview",
        "7. JSON export files",
        "8. Runtime JSON consumer smoke",
        "9. API readiness / freeze review",
        "10. Safety contract",
        "",
    ]

    for example in examples:
        sections.extend(
            [
                example.title,
                f"Purpose: {example.purpose}",
                "Command:",
                example.command,
                f"Expected output: {example.output}",
                "",
            ]
        )

    sections.extend(
        [
            "History details:",
            _HISTORY_DETAILS_COMMAND,
            "",
            "History candle count:",
            "--limit 300 means 300 candles for the previous window and 300 candles for the current window.",
            "Total request size is limit * 2 = 600 candles per symbol.",
            "",
            "Timeline details:",
            _TIMELINE_DETAILS_COMMAND,
            "",
            "Timeline candle count:",
            "required candles = window_size * window_count",
            "300 * 4 = 1200 candles per symbol.",
            "",
            "7. JSON export files",
            "Use --export-json for API-oriented runtime JSON output.",
            "",
            "Current JSON export:",
            _CURRENT_EXPORT_COMMAND,
            "File: reports/book_l1/current_preview.json",
            "",
            "Multi JSON export:",
            _MULTI_EXPORT_COMMAND,
            "File: reports/book_l1/multi_preview.json",
            "",
            "History JSON export:",
            _HISTORY_EXPORT_COMMAND,
            "File: reports/book_l1/history_preview.json",
            "",
            "Timeline JSON export:",
            _TIMELINE_EXPORT_COMMAND,
            "File: reports/book_l1/timeline_preview.json",
            "",
            "JSON export rules:",
            "- JSON files are overwritten on each export run.",
            "- Filenames are stable.",
            "- No timestamp/version/symbol/interval/hash is added to filename.",
            "- Runtime Markdown export is not used.",
            "",
            "8. Runtime JSON consumer smoke",
            "Validate stable JSON export files before API consumption.",
            "",
            "Recommended API-readiness workflow:",
            _CURRENT_EXPORT_COMMAND,
            _MULTI_EXPORT_COMMAND,
            _HISTORY_EXPORT_COMMAND,
            _TIMELINE_EXPORT_COMMAND,
            _JSON_CONSUMER_SMOKE_COMMAND,
            "",
            "BOOK-L2 observation workflow:",
            "1. Export BOOK-L1 timeline JSON:",
            _TIMELINE_EXPORT_COMMAND,
            "2. Validate BOOK-L1 JSON:",
            _JSON_CONSUMER_SMOKE_COMMAND,
            "3. Read BOOK-L2 context:",
            _L2_CONTEXT_COMMAND,
            "4. Validate BOOK-L2 JSON for API consumers:",
            _L2_JSON_CONSUMER_SMOKE_COMMAND,
            "5. Write L1-L2 interval answer evidence:",
            _L1_L2_INTERVAL_ANSWER_SMOKE_COMMAND,
            "6. Write L1-L2 multi-interval answer evidence:",
            _L1_L2_MULTI_INTERVAL_ANSWER_SMOKE_COMMAND,
            "7. Audit local candle availability before multi-interval reports:",
            _DATA_AVAILABILITY_AUDIT_COMMAND,
            "8. Fix interval data preparation decision:",
            _DATA_PREPARATION_DECISION_COMMAND,
            "",
            "BOOK-L2 JSON consumer smoke:",
            "Validates reports/book_l2/timeline_context.json without reading candles, DB, or live services.",
            "",
            "Command:",
            _L2_JSON_CONSUMER_SMOKE_COMMAND,
            "",
            "Full BOOK-L2 JSON workflow:",
            _TIMELINE_EXPORT_COMMAND,
            _JSON_CONSUMER_SMOKE_COMMAND,
            _L2_CONTEXT_COMMAND,
            _L2_JSON_CONSUMER_SMOKE_COMMAND,
            "BOOK-L2 is observe-only and does not produce trading signals.",
            "BOOK-L2 market brief:",
            "- L2 summary is observe-only.",
            "- It gives observation candidates, not trade candidates.",
            "- JSON export remains reports/book_l2/timeline_context.json.",
            "",
            "L1-L2 interval answer smoke",
            "Runs the full L1 timeline to L2 context chain and writes a human evidence report.",
            "",
            "Command:",
            _L1_L2_INTERVAL_ANSWER_SMOKE_COMMAND,
            "",
            "Answer file:",
            "reports/book_l2/l1_l2_interval_answer.md",
            "",
            "L1-L2 multi-interval answer smoke",
            "Runs the full L1 timeline to L2 context chain for several intervals and writes a human evidence report.",
            "",
            "Command:",
            _L1_L2_MULTI_INTERVAL_ANSWER_SMOKE_COMMAND,
            "",
            "Answer file:",
            "reports/book_l2/l1_l2_multi_interval_answer.md",
            "",
            "Data availability audit",
            "Audits local candle counts for BOOK-L1/BOOK-L2 reports without downloading or modifying data.",
            "",
            "Command:",
            _DATA_AVAILABILITY_AUDIT_COMMAND,
            "",
            "Strict command:",
            _DATA_AVAILABILITY_AUDIT_STRICT_COMMAND,
            "",
            "Evidence files:",
            "reports/book_data/candle_availability_audit.json",
            "reports/book_data/candle_availability_audit.md",
            "",
            "Status meaning:",
            "- PASS means every requested symbol/interval is READY.",
            "- PASS_WITH_DATA_GAPS means the audit succeeded but some rows are MISSING or INSUFFICIENT_DATA.",
            "- FAIL in strict mode means one or more rows are not READY.",
            "",
            "Data preparation decision",
            "Reads the BOOK-DATA-01 audit artifact and fixes the active interval decision without downloading, writing DB rows, or aggregating candles.",
            "",
            "Recommended workflow:",
            _DATA_AVAILABILITY_AUDIT_COMMAND,
            _DATA_PREPARATION_DECISION_COMMAND,
            "",
            "Strict decision check:",
            _DATA_PREPARATION_DECISION_STRICT_COMMAND,
            "",
            "Decision files:",
            "reports/book_data/interval_data_preparation_decision.json",
            "reports/book_data/interval_data_preparation_decision.md",
            "",
            "Current expected decision:",
            "15m is the active working interval.",
            "1h and 4h are optional/missing and require a separate explicit BOOK-DATA stage.",
            "",
            "15m-only Market Reader stabilization",
            "Runs the current 15m-only workflow from DATA availability through L1 timeline, L2 context, strict consumers, readiness, and interval answer evidence.",
            "",
            "Command:",
            _DATA_15M_STABILIZATION_COMMAND,
            "",
            "Files:",
            "reports/book_data/market_reader_15m_stabilization.json",
            "reports/book_data/market_reader_15m_stabilization.md",
            "",
            "15m Market Reader quality review",
            "Reviews the current stabilized 15m L1/L2 evidence and explains weak or unclear market context without changing market logic.",
            "",
            "Recommended workflow:",
            _DATA_15M_STABILIZATION_COMMAND,
            _L1_15M_QUALITY_REVIEW_COMMAND,
            "",
            "Files:",
            "reports/book_l1/market_reader_15m_quality_review.json",
            "reports/book_l1/market_reader_15m_quality_review.md",
            "",
            "L1-L2 regime alignment review",
            "Reviews whether BOOK-L2 preserves and explains BOOK-L1 regimes correctly on the active 15m workflow.",
            "",
            "Recommended workflow:",
            _L1_15M_QUALITY_REVIEW_COMMAND,
            _L1_L2_REGIME_ALIGNMENT_REVIEW_COMMAND,
            "",
            "Files:",
            "reports/book_l1/l1_l2_regime_alignment_review.json",
            "reports/book_l1/l1_l2_regime_alignment_review.md",
            "",
            "FLAT context alignment diagnostic",
            "Diagnoses whether high-confidence L1 FLAT is preserved by BOOK-L2 as readable market context.",
            "",
            "Recommended workflow:",
            _L1_L2_REGIME_ALIGNMENT_REVIEW_COMMAND,
            _L1_FLAT_CONTEXT_ALIGNMENT_DIAGNOSTIC_COMMAND,
            "",
            "Files:",
            "reports/book_l1/flat_context_alignment_diagnostic.json",
            "reports/book_l1/flat_context_alignment_diagnostic.md",
            "",
            "FLAT context handling proposal",
            "Proposes safe BOOK-L2 handling for high-confidence L1 FLAT without changing runtime rules.",
            "",
            "Recommended workflow:",
            _L1_FLAT_CONTEXT_ALIGNMENT_DIAGNOSTIC_COMMAND,
            _L2_FLAT_CONTEXT_HANDLING_PROPOSAL_COMMAND,
            "",
            "Files:",
            "reports/book_l2/flat_context_handling_proposal.json",
            "reports/book_l2/flat_context_handling_proposal.md",
            "",
            "Boundary:",
            "- `15m` is the active interval for current BOOK-L1/BOOK-L2 development.",
            "- `1h` and `4h` remain optional/missing and are not blockers.",
            "- This command does not download data, write DB rows, aggregate intervals, train models, or connect runtime trading.",
            "",
            "Evidence rule:",
            "- This Markdown file is for human smoke review.",
            "- It is not runtime API output.",
            "- Runtime/API output remains JSON.",
            "",
            "BOOK-L2 freeze candidate review",
            "Run the fixed output, consumer smoke, and readiness review before treating BOOK-L2 as frozen.",
            "",
            "Commands:",
            "python -m app.cli.commands book-l2-timeline-context --export --strict",
            "python -m app.cli.commands book-l2-json-consumer-smoke --strict",
            "python -m app.cli.commands book-l2-api-readiness-review --strict",
            "",
            "9. API readiness / freeze review",
            "Checks that BOOK-L1 is ready as read-only Layer 1 for terminal use and API JSON consumers.",
            "",
            "Command:",
            _API_READINESS_REVIEW_COMMAND,
            "",
            "Expected output:",
            "PASS/WARN/FAIL readiness table and Layer 1 freeze candidate YES/NO.",
            "",
            "10. Safety contract",
            "trade_signal = NOT_EVALUATED",
            "safe_for_runtime_trading = false",
            "orders_enabled = false",
            "live_trading_connected = false",
            "traders_core_connected = false",
            "approved_for_live_trading = false",
            "approved_for_auto_activation = false",
            "model_training_executed = false",
            "binance_download_executed = false",
        ]
    )

    return "\n".join(sections)
