from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l2/l1_l2_interval_answer.md")
EXPECTED_L1_SOURCE_PATH = "reports/book_l1/timeline_preview.json"
PASS = "PASS"
FAIL = "FAIL"

FORBIDDEN_ANSWER_TERMS = (
    "LONG",
    "SHORT",
    "BUY",
    "SELL",
    "ENTRY",
    "EXIT",
    "TAKE PROFIT",
    "STOP LOSS",
    "TP",
    "SL",
    "POSITION SIZE",
    "LEVERAGE",
    "ORDER",
    "TRADE CANDIDATE",
    "ENTRY CANDIDATE",
    "сигнал на покупку",
    "сигнал на продажу",
    "вход",
    "шорт",
    "лонг",
)

EXPECTED_SAFETY_FIELDS: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
}


@dataclass(frozen=True)
class L1L2IntervalAnswerSmokeConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = "15m"
    window_size: int = 300
    window_count: int = 4
    min_candles: int = 50
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False
    l1_json_path: Path = DEFAULT_L1_TIMELINE_JSON
    l2_json_path: Path = DEFAULT_L2_CONTEXT_JSON
    project_root: Path = Path(".")
    run_api_readiness: bool = True

    def __post_init__(self) -> None:
        symbols = tuple(_normalize_symbol(symbol) for symbol in self.symbols if str(symbol).strip())
        object.__setattr__(self, "symbols", symbols or DEFAULT_SYMBOLS)
        object.__setattr__(self, "interval", self.interval.strip() or "15m")
        object.__setattr__(self, "output_md", Path(self.output_md))
        object.__setattr__(self, "l1_json_path", Path(self.l1_json_path))
        object.__setattr__(self, "l2_json_path", Path(self.l2_json_path))
        object.__setattr__(self, "project_root", Path(self.project_root))


@dataclass(frozen=True)
class L1L2IntervalAnswerSmokeStep:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class L1L2IntervalAnswerSmokeResult:
    status: str
    output_md: str
    steps: tuple[L1L2IntervalAnswerSmokeStep, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    l2_payload: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def passed(self) -> bool:
        return self.status == PASS


class L1L2IntervalAnswerSmokeRunner:
    def run(
        self,
        config: L1L2IntervalAnswerSmokeConfig | None = None,
        *,
        execute_pipeline: bool = True,
    ) -> L1L2IntervalAnswerSmokeResult:
        active_config = config or L1L2IntervalAnswerSmokeConfig()
        steps: list[L1L2IntervalAnswerSmokeStep] = []
        warnings: list[str] = []
        errors: list[str] = []

        if execute_pipeline:
            steps.extend(_run_pipeline(active_config))

        l1_payload = _read_json(active_config.l1_json_path)
        l2_payload = _read_json(active_config.l2_json_path)
        _upsert_step(steps, _file_step("L1 timeline export", active_config.l1_json_path, l1_payload))
        _upsert_step(steps, _l1_json_consumer_step(active_config))
        _upsert_step(steps, _file_step("L2 context export", active_config.l2_json_path, l2_payload))
        _upsert_step(steps, _l2_json_consumer_step(active_config))
        if active_config.run_api_readiness:
            _upsert_step(steps, _l2_api_readiness_step(active_config))
        else:
            _upsert_step(steps, L1L2IntervalAnswerSmokeStep("L2 API readiness strict", PASS, "Skipped by test config."))
        _upsert_step(steps, _symbol_propagation_step(l1_payload.value, l2_payload.value))
        _upsert_step(steps, _source_lineage_step(l2_payload.value))
        _upsert_step(steps, _safety_step(l2_payload.value))
        _upsert_step(steps, _forbidden_terms_step(l2_payload.value))

        errors.extend(step.message for step in steps if step.status == FAIL)
        status = PASS if not errors else FAIL
        markdown = build_evidence_markdown(
            config=active_config,
            status=status,
            steps=tuple(steps),
            l1_payload=l1_payload.value,
            l2_payload=l2_payload.value,
            errors=tuple(errors),
        )
        try:
            active_config.output_md.parent.mkdir(parents=True, exist_ok=True)
            active_config.output_md.write_text(markdown, encoding="utf-8")
            _upsert_step(steps, L1L2IntervalAnswerSmokeStep("Evidence markdown written", PASS, "Evidence Markdown written."))
            markdown = build_evidence_markdown(
                config=active_config,
                status=status,
                steps=tuple(steps),
                l1_payload=l1_payload.value,
                l2_payload=l2_payload.value,
                errors=tuple(errors),
            )
            active_config.output_md.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            message = f"Could not write evidence Markdown: {exc}"
            _upsert_step(steps, L1L2IntervalAnswerSmokeStep("Evidence markdown written", FAIL, message))
            errors.append(message)
            status = FAIL

        return L1L2IntervalAnswerSmokeResult(
            status=status,
            output_md=active_config.output_md.as_posix(),
            steps=tuple(steps),
            warnings=tuple(warnings),
            errors=tuple(dict.fromkeys(errors)),
            l2_payload=l2_payload.value if isinstance(l2_payload.value, dict) else None,
        )


class L1L2IntervalAnswerSmokeFormatter:
    def format(self, result: L1L2IntervalAnswerSmokeResult, *, config: L1L2IntervalAnswerSmokeConfig) -> str:
        lines = [
            "BOOK-L1 -> BOOK-L2 Interval Answer Smoke",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"Window size: {config.window_size}",
            f"Window count: {config.window_count}",
            f"Min candles: {config.min_candles}",
            "",
            "Pipeline:",
            _format_steps_table(result.steps),
            "",
            "Answer file:",
            result.output_md,
        ]
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        if config.show_details:
            lines.extend(["", _format_details(result.l2_payload)])
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_smoke_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return tuple(_normalize_symbol(item) for item in values) or DEFAULT_SYMBOLS


def build_evidence_markdown(
    *,
    config: L1L2IntervalAnswerSmokeConfig,
    status: str,
    steps: tuple[L1L2IntervalAnswerSmokeStep, ...],
    l1_payload: Any,
    l2_payload: Any,
    errors: tuple[str, ...],
) -> str:
    if status != PASS:
        failure_lines = [f"- {_md(error)}" for error in errors] or ["- Unknown failure."]
    else:
        failure_lines = []

    result = _dict(l2_payload.get("result") if isinstance(l2_payload, dict) else None)
    brief = _dict(result.get("market_brief"))
    symbols = _list_of_dicts(result.get("symbols"))
    safety = _dict(l2_payload.get("safety") if isinstance(l2_payload, dict) else None)
    overall_state = _text(result.get("overall_state"), "N/A")
    brief_text = _text(brief.get("brief") or brief.get("brief_state"), "N/A")

    lines = [
        "# L1-L2 Interval Answer Smoke",
        "",
        "## Status",
        "",
        f"`{status}`",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Interval | `{_md(config.interval)}` |",
        f"| Window size | `{config.window_size}` |",
        f"| Window count | `{config.window_count}` |",
        f"| Min candles | `{config.min_candles}` |",
        "",
        "## Pipeline Result",
        "",
        "| Step | Status |",
        "|---|---|",
        *[f"| {_md(step.name)} | {step.status} |" for step in steps],
    ]
    if failure_lines:
        lines.extend(["", "## Failure", "", *failure_lines])

    lines.extend(
        [
            "",
            "## Actual BOOK-L2 Answer",
            "",
            "### Overall",
            "",
            f"- Overall state: `{_md(overall_state)}`",
            f"- Brief: {_md(brief_text)}",
            "",
            "### Observation candidates",
            "",
            *_candidate_lines(brief.get("observation_candidates")),
            "",
            "### Skip candidates",
            "",
            *_candidate_lines(brief.get("skip_candidates")),
            "",
            "### Key points",
            "",
            *_text_list_lines(brief.get("key_points")),
            "",
            "## Per-symbol Context",
            "",
            "| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |",
            "|---:|---|---|---|---:|---|---|---|---|---|",
            *_symbol_table_rows(symbols, brief),
            "",
            "## Source Lineage",
            "",
            f"- L1 input JSON: `{_md(config.l1_json_path.as_posix())}`",
            f"- L2 output JSON: `{_md(config.l2_json_path.as_posix())}`",
            f"- L2 source confirms L1 timeline: `{_step_status(steps, 'Source lineage')}`",
            "",
            "## Safety",
            "",
            f"- trade_signal: `{_md(_text(safety.get('trade_signal'), 'N/A'))}`",
            f"- safe_for_runtime_trading: `{_format_value(safety.get('safe_for_runtime_trading'))}`",
            f"- orders_enabled: `{_format_value(safety.get('orders_enabled'))}`",
            f"- live_trading_connected: `{_format_value(safety.get('live_trading_connected'))}`",
            f"- traders_core_connected: `{_format_value(safety.get('traders_core_connected'))}`",
            f"- approved_for_live_trading: `{_format_value(safety.get('approved_for_live_trading'))}`",
            f"- approved_for_auto_activation: `{_format_value(safety.get('approved_for_auto_activation'))}`",
            f"- observe_only: `{_format_value(safety.get('observe_only', 'N/A'))}`",
            "",
            "## Conclusion",
            "",
            _conclusion(status, l1_payload=l1_payload, l2_payload=l2_payload),
            "",
            "This is observe-only context. It is not a trading instruction.",
            "",
        ]
    )
    return "\n".join(lines)


def _run_pipeline(config: L1L2IntervalAnswerSmokeConfig) -> tuple[L1L2IntervalAnswerSmokeStep, ...]:
    steps: list[L1L2IntervalAnswerSmokeStep] = []
    try:
        from app.db.repositories.candle_repository import CandleRepository
        from app.db.session import get_session
        from app.market_reader.json_export import build_timeline_preview_export_payload, write_book_l1_json_export
        from app.market_reader.timeline_preview import TimelinePreviewConfig, TimelinePreviewRunner

        preview_config = TimelinePreviewConfig(
            symbols=config.symbols,
            interval=config.interval,
            window_size=config.window_size,
            window_count=config.window_count,
            min_candles=config.min_candles,
        )
        with get_session() as session:
            timeline_result = TimelinePreviewRunner(candle_repository=CandleRepository(session)).run(preview_config)
        envelope = build_timeline_preview_export_payload(
            request={
                "symbols": list(config.symbols),
                "interval": config.interval,
                "window_size": config.window_size,
                "window_count": config.window_count,
                "min_candles": config.min_candles,
                "non_interactive": True,
                "show_details": config.show_details,
            },
            result=timeline_result,
        )
        path = write_book_l1_json_export(envelope, output_dir=config.l1_json_path.parent)
        steps.append(_pass("L1 timeline export", f"Written: {path.as_posix()}"))
    except Exception as exc:
        steps.append(_fail("L1 timeline export", f"L1 timeline export failed: {exc}"))
        return tuple(steps)

    steps.append(_l1_json_consumer_step(config))
    if steps[-1].status == FAIL:
        return tuple(steps)

    try:
        from app.market_interpreter import L1TimelineConsumer, L1TimelineConsumerConfig

        result = L1TimelineConsumer().run(
            L1TimelineConsumerConfig(
                input_path=config.l1_json_path,
                strict=True,
                export_json=True,
                output_dir=config.l2_json_path.parent,
            )
        )
        if result.status == "OK":
            steps.append(_pass("L2 context export", f"Written: {config.l2_json_path.as_posix()}"))
        else:
            message = "; ".join(result.errors or ("BOOK-L2 context export failed.",))
            steps.append(_fail("L2 context export", message))
    except Exception as exc:
        steps.append(_fail("L2 context export", f"L2 context export failed: {exc}"))
        return tuple(steps)

    steps.append(_l2_json_consumer_step(config))
    if config.run_api_readiness:
        steps.append(_l2_api_readiness_step(config))
    return tuple(steps)


@dataclass(frozen=True)
class _JsonRead:
    value: Any = None
    error: str | None = None


def _read_json(path: Path) -> _JsonRead:
    if not path.is_file():
        return _JsonRead(error=f"missing file: {path.as_posix()}")
    try:
        return _JsonRead(value=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return _JsonRead(error=f"invalid JSON in {path.as_posix()}: {exc.msg}")
    except OSError as exc:
        return _JsonRead(error=f"could not read {path.as_posix()}: {exc}")


def _file_step(name: str, path: Path, payload: _JsonRead) -> L1L2IntervalAnswerSmokeStep:
    if payload.error:
        return _fail(name, payload.error)
    return _pass(name, f"Found readable JSON: {path.as_posix()}")


def _l1_json_consumer_step(config: L1L2IntervalAnswerSmokeConfig) -> L1L2IntervalAnswerSmokeStep:
    try:
        from app.market_reader.json_consumer import RuntimeJsonConsumer, RuntimeJsonConsumerConfig

        result = RuntimeJsonConsumer().run(
            RuntimeJsonConsumerConfig(input_dir=config.l1_json_path.parent, report_types=("timeline",), strict=True)
        )
    except Exception as exc:
        return _fail("L1 JSON consumer strict", f"L1 JSON consumer failed: {exc}")
    if result.result_status == PASS:
        return _pass("L1 JSON consumer strict", "BOOK-L1 timeline JSON is API-readable.")
    message = "; ".join(result.validation_errors or ("BOOK-L1 timeline JSON consumer did not pass.",))
    return _fail("L1 JSON consumer strict", message)


def _l2_json_consumer_step(config: L1L2IntervalAnswerSmokeConfig) -> L1L2IntervalAnswerSmokeStep:
    try:
        from app.market_interpreter import L2ContextConsumerConfig, L2ContextJsonConsumer

        result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=config.l2_json_path, strict=True))
    except Exception as exc:
        return _fail("L2 JSON consumer strict", f"L2 JSON consumer failed: {exc}")
    if result.status == PASS:
        return _pass("L2 JSON consumer strict", "BOOK-L2 context JSON strict validation passed.")
    message = "; ".join(result.errors or result.warnings or ("BOOK-L2 JSON consumer did not pass.",))
    return _fail("L2 JSON consumer strict", message)


def _l2_api_readiness_step(config: L1L2IntervalAnswerSmokeConfig) -> L1L2IntervalAnswerSmokeStep:
    try:
        from app.market_interpreter import L2ApiReadinessConfig, L2ApiReadinessReviewer

        result = L2ApiReadinessReviewer().run(
            L2ApiReadinessConfig(
                project_root=config.project_root,
                l1_timeline_path=config.l1_json_path,
                l2_context_path=config.l2_json_path,
                strict=True,
            )
        )
    except Exception as exc:
        return _fail("L2 API readiness strict", f"L2 API readiness review failed: {exc}")
    if result.status == PASS:
        return _pass("L2 API readiness strict", "BOOK-L2 API readiness strict review passed.")
    message = "; ".join(result.errors or result.warnings or ("BOOK-L2 API readiness strict review did not pass.",))
    return _fail("L2 API readiness strict", message)


def _symbol_propagation_step(l1_payload: Any, l2_payload: Any) -> L1L2IntervalAnswerSmokeStep:
    l1_symbols = _extract_l1_symbols(l1_payload)
    l2_symbols = _extract_l2_symbols(l2_payload)
    if not l1_symbols:
        return _fail("Symbol propagation", "L1 timeline JSON contains no symbols.")
    missing = tuple(symbol for symbol in l1_symbols if symbol not in l2_symbols)
    if missing:
        return _fail("Symbol propagation", f"Missing L2 symbol(s): {', '.join(missing)}")
    return _pass("Symbol propagation", "Every L1 symbol is present in L2 output.")


def _source_lineage_step(l2_payload: Any) -> L1L2IntervalAnswerSmokeStep:
    if not isinstance(l2_payload, dict):
        return _fail("Source lineage", "L2 payload is not an object.")
    source = _dict(l2_payload.get("source"))
    values = {
        _path_text(l2_payload.get("source_report")),
        _path_text(source.get("input_path")),
        _text(source.get("report_type"), ""),
    }
    if EXPECTED_L1_SOURCE_PATH in values or "timeline_preview" in values:
        return _pass("Source lineage", "L2 output points back to BOOK-L1 timeline JSON.")
    return _fail("Source lineage", "L2 output does not contain BOOK-L1 timeline source lineage.")


def _safety_step(l2_payload: Any) -> L1L2IntervalAnswerSmokeStep:
    safety = _dict(l2_payload.get("safety") if isinstance(l2_payload, dict) else None)
    errors: list[str] = []
    for field_name, expected in EXPECTED_SAFETY_FIELDS.items():
        if field_name not in safety:
            errors.append(f"missing safety field: {field_name}")
        elif safety[field_name] != expected:
            errors.append(f"safety.{field_name} must be {_format_value(expected)}")
    if "observe_only" in safety and safety.get("observe_only") is not True:
        errors.append("safety.observe_only must be true")
    if errors:
        return _fail("Fail-closed safety", "; ".join(errors))
    return _pass("Fail-closed safety", "Safety is fail-closed.")


def _forbidden_terms_step(l2_payload: Any) -> L1L2IntervalAnswerSmokeStep:
    matches: list[str] = []
    for text in _human_answer_text_parts(l2_payload):
        matches.extend(_forbidden_terms_in_text(text))
    if matches:
        return _fail("Forbidden terms", f"Human answer contains forbidden term(s): {', '.join(dict.fromkeys(matches))}")
    return _pass("Forbidden terms", "Human answer sections contain no forbidden trading terms.")


def _extract_l1_symbols(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    request = _dict(payload.get("request"))
    requested_symbols = request.get("symbols")
    if isinstance(requested_symbols, list) and requested_symbols:
        return tuple(_normalize_symbol(symbol) for symbol in requested_symbols)
    result = _dict(payload.get("result"))
    rows = _list_of_dicts(result.get("rows") or result.get("symbols") or payload.get("rows"))
    return tuple(_normalize_symbol(row.get("symbol")) for row in rows if row.get("symbol"))


def _extract_l2_symbols(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    result = _dict(payload.get("result"))
    return tuple(_normalize_symbol(row.get("symbol")) for row in _list_of_dicts(result.get("symbols")) if row.get("symbol"))


def _human_answer_text_parts(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    result = _dict(payload.get("result"))
    brief = _dict(result.get("market_brief"))
    parts: list[str] = []
    for key in ("brief", "brief_state", "safety_note"):
        value = brief.get(key)
        if isinstance(value, str):
            parts.append(value)
    key_points = brief.get("key_points")
    if isinstance(key_points, list):
        parts.extend(str(point) for point in key_points)
    for key in ("observation_candidates", "skip_candidates"):
        for candidate in _list_of_dicts(brief.get(key)):
            reason = candidate.get("main_reason")
            if isinstance(reason, str):
                parts.append(reason)
    return tuple(parts)


def _forbidden_terms_in_text(text: str) -> tuple[str, ...]:
    upper_text = text.replace("_", " ").upper()
    matches: list[str] = []
    for term in FORBIDDEN_ANSWER_TERMS:
        upper_term = term.upper()
        if any(ord(char) > 127 for char in upper_term):
            if upper_term in upper_text:
                matches.append(term)
            continue
        pattern = r"(?<![A-Z0-9])" + re.escape(upper_term).replace(r"\ ", r"[\s_]+") + r"(?![A-Z0-9])"
        if re.search(pattern, upper_text):
            matches.append(term)
    return tuple(matches)


def _format_steps_table(steps: tuple[L1L2IntervalAnswerSmokeStep, ...]) -> str:
    headers = ("Step", "Status")
    rows = tuple((step.name, step.status) for step in steps)
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _format_table_row(headers, widths), border]
    lines.extend(_format_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _format_table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _format_details(payload: dict[str, Any] | None) -> str:
    result = _dict(payload.get("result") if isinstance(payload, dict) else None)
    brief = _dict(result.get("market_brief"))
    return "\n".join(
        [
            f"Overall State: {_text(result.get('overall_state'), 'N/A')}",
            f"Brief: {_text(brief.get('brief') or brief.get('brief_state'), 'N/A')}",
            f"Observation candidates: {_join_candidate_symbols(brief.get('observation_candidates'))}",
            f"Skip candidates: {_join_candidate_symbols(brief.get('skip_candidates'))}",
        ]
    )


def _candidate_lines(value: Any) -> list[str]:
    candidates = _list_of_dicts(value)
    if not candidates:
        return ["- none"]
    return [f"- {_md(_text(candidate.get('symbol'), 'N/A'))}" for candidate in candidates]


def _text_list_lines(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["- none"]
    return [f"- {_md(str(item))}" for item in value]


def _symbol_table_rows(symbols: tuple[dict[str, Any], ...], brief: dict[str, Any]) -> list[str]:
    if not symbols:
        return ["|  | N/A | N/A | N/A |  | N/A | N/A | N/A | N/A | N/A |"]
    reasons = _candidate_reasons(brief)
    sorted_symbols = sorted(symbols, key=lambda row: (row.get("context_rank") is None, row.get("context_rank") or 10**9, str(row.get("symbol"))))
    rows: list[str] = []
    for symbol in sorted_symbols:
        symbol_name = _text(symbol.get("symbol"), "N/A")
        score = symbol.get("context_quality_score")
        rows.append(
            "| "
            + " | ".join(
                (
                    _md(_rank_text(symbol.get("context_rank"))),
                    _md(symbol_name),
                    _md(_text(symbol.get("bucket"), "N/A")),
                    _md(_text(symbol.get("context_quality_grade") or symbol.get("quality_grade"), "N/A")),
                    _md(_score_text(score)),
                    _format_value(symbol.get("skip_candidate")),
                    _md(_text(symbol.get("current_regime"), "N/A")),
                    _md(_text(symbol.get("stability"), "N/A")),
                    _md(_text(symbol.get("last_transition"), "N/A")),
                    _md(reasons.get(symbol_name, "N/A")),
                )
            )
            + " |"
        )
    return rows


def _candidate_reasons(brief: dict[str, Any]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for key in ("observation_candidates", "skip_candidates"):
        for candidate in _list_of_dicts(brief.get(key)):
            symbol = _text(candidate.get("symbol"), "")
            reason = _text(candidate.get("main_reason"), "")
            if symbol and reason:
                reasons[symbol] = reason
    return reasons


def _conclusion(status: str, *, l1_payload: Any, l2_payload: Any) -> str:
    if status == PASS:
        return "The L1-L2 pipeline produced a readable market context report for the requested interval."
    if not isinstance(l1_payload, dict):
        return "FAIL: BOOK-L1 timeline JSON was not available or readable."
    if not isinstance(l2_payload, dict):
        return "FAIL: BOOK-L2 context JSON was not available or readable."
    l2_status = str(l2_payload.get("status", "")).upper()
    if l2_status in {"INSUFFICIENT_DATA", "NO_CONTEXT", "FAIL", "ERROR"}:
        return f"{l2_status}: BOOK-L2 could not produce a complete readable answer for this interval."
    return "FAIL: The L1-L2 smoke checks did not all pass."


def _join_candidate_symbols(value: Any) -> str:
    candidates = _list_of_dicts(value)
    if not candidates:
        return "none"
    return ", ".join(_text(candidate.get("symbol"), "N/A") for candidate in candidates)


def _step_status(steps: tuple[L1L2IntervalAnswerSmokeStep, ...], name: str) -> str:
    for step in steps:
        if step.name == name:
            return step.status
    return "N/A"


def _pass(name: str, message: str) -> L1L2IntervalAnswerSmokeStep:
    return L1L2IntervalAnswerSmokeStep(name=name, status=PASS, message=message)


def _fail(name: str, message: str) -> L1L2IntervalAnswerSmokeStep:
    return L1L2IntervalAnswerSmokeStep(name=name, status=FAIL, message=message)


def _upsert_step(steps: list[L1L2IntervalAnswerSmokeStep], step: L1L2IntervalAnswerSmokeStep) -> None:
    for index, existing in enumerate(steps):
        if existing.name == step.name:
            if existing.status == PASS or step.status == FAIL:
                steps[index] = step
            return
    steps.append(step)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_of_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def _text(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _path_text(value: Any) -> str:
    return str(value).replace("\\", "/") if value is not None else ""


def _rank_text(value: Any) -> str:
    return "" if value is None else str(value)


def _score_text(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "N/A"
    return str(value)


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "DEFAULT_SYMBOLS",
    "DEFAULT_OUTPUT_MD",
    "L1L2IntervalAnswerSmokeConfig",
    "L1L2IntervalAnswerSmokeStep",
    "L1L2IntervalAnswerSmokeResult",
    "L1L2IntervalAnswerSmokeRunner",
    "L1L2IntervalAnswerSmokeFormatter",
    "build_evidence_markdown",
    "parse_smoke_symbols",
]
