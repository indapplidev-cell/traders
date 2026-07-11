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
            "BOOK-L2 is observe-only and does not produce trading signals.",
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
