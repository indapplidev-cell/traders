from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.integration.l1_l2_interval_answer_smoke import (
    DEFAULT_SYMBOLS,
    EXPECTED_SAFETY_FIELDS,
    L1L2IntervalAnswerSmokeConfig,
    L1L2IntervalAnswerSmokeResult,
    L1L2IntervalAnswerSmokeRunner,
    _forbidden_terms_in_text,
)


DEFAULT_INTERVALS = ("15m", "1h", "4h")
DEFAULT_OUTPUT_MD = Path("reports/book_l2/l1_l2_multi_interval_answer.md")
DEFAULT_INTERVAL_OUTPUT_DIR = Path("reports/book_l2/interval_answers")
PASS = "PASS"
FAIL = "FAIL"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class L1L2MultiIntervalAnswerSmokeConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    intervals: tuple[str, ...] = DEFAULT_INTERVALS
    window_size: int = 300
    window_count: int = 4
    min_candles: int = 50
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False
    continue_on_fail: bool = True

    def __post_init__(self) -> None:
        symbols = tuple(_normalize_symbol(symbol) for symbol in self.symbols if str(symbol).strip())
        intervals = tuple(str(interval).strip() for interval in self.intervals if str(interval).strip())
        object.__setattr__(self, "symbols", symbols or DEFAULT_SYMBOLS)
        object.__setattr__(self, "intervals", intervals or DEFAULT_INTERVALS)
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class L1L2IntervalSymbolContext:
    rank: str
    symbol: str
    bucket: str
    quality: str
    score: str
    skip: str
    current_regime: str
    stability: str
    last_transition: str
    main_reason: str


@dataclass(frozen=True)
class L1L2IntervalAnswerSummary:
    interval: str
    status: str
    overall_state: str | None = None
    brief: str | None = None
    observation_candidates: tuple[str, ...] = ()
    skip_candidates: tuple[str, ...] = ()
    key_points: tuple[str, ...] = ()
    symbol_contexts: tuple[L1L2IntervalSymbolContext, ...] = ()
    symbol_count: int = 0
    safety_status: str = UNKNOWN
    safety: dict[str, Any] = field(default_factory=dict)
    evidence_file: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class L1L2MultiIntervalAggregation:
    interval_count: int
    pass_count: int
    fail_count: int
    pass_with_warnings_count: int
    intervals_with_observation_candidates: tuple[str, ...] = ()
    intervals_with_all_symbols_skipped: tuple[str, ...] = ()
    most_common_overall_state: str = "N/A"
    repeated_observation_candidates: tuple[str, ...] = ()
    repeated_skip_candidates: tuple[str, ...] = ()


@dataclass(frozen=True)
class L1L2MultiIntervalAnswerSmokeResult:
    status: str
    output_md: str
    intervals: tuple[L1L2IntervalAnswerSummary, ...] = field(default_factory=tuple)
    aggregation: L1L2MultiIntervalAggregation | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status == PASS


class IntervalRunner(Protocol):
    def run(self, config: L1L2IntervalAnswerSmokeConfig) -> L1L2IntervalAnswerSmokeResult:
        ...


class L1L2MultiIntervalAnswerSmokeRunner:
    def __init__(self, interval_runner: IntervalRunner | None = None) -> None:
        self._interval_runner = interval_runner or L1L2IntervalAnswerSmokeRunner()

    def run(self, config: L1L2MultiIntervalAnswerSmokeConfig | None = None) -> L1L2MultiIntervalAnswerSmokeResult:
        active_config = config or L1L2MultiIntervalAnswerSmokeConfig()
        summaries: list[L1L2IntervalAnswerSummary] = []
        warnings: list[str] = []
        errors: list[str] = []

        for interval in active_config.intervals:
            evidence_path = _interval_evidence_path(interval, output_md=active_config.output_md)
            single_config = L1L2IntervalAnswerSmokeConfig(
                symbols=active_config.symbols,
                interval=interval,
                window_size=active_config.window_size,
                window_count=active_config.window_count,
                min_candles=active_config.min_candles,
                output_md=evidence_path,
                strict=active_config.strict,
                show_details=active_config.show_details,
            )
            try:
                single_result = self._interval_runner.run(single_config)
                summary = build_interval_summary(
                    interval=interval,
                    result=single_result,
                    evidence_file=evidence_path.as_posix(),
                )
            except Exception as exc:
                message = f"Interval {interval} failed before summary extraction: {exc}"
                summary = L1L2IntervalAnswerSummary(
                    interval=interval,
                    status=FAIL,
                    safety_status=UNKNOWN,
                    evidence_file=evidence_path.as_posix(),
                    error=message,
                )
            summaries.append(summary)
            if summary.status == FAIL:
                errors.append(f"Interval {interval}: {summary.error or 'failed.'}")
                if not active_config.continue_on_fail:
                    break

        aggregation = aggregate_interval_summaries(tuple(summaries))
        status = _result_status(tuple(summaries), strict=active_config.strict)
        validation_errors = validate_multi_interval_answer(tuple(summaries))
        errors.extend(validation_errors)
        if validation_errors:
            status = FAIL

        result = L1L2MultiIntervalAnswerSmokeResult(
            status=status,
            output_md=active_config.output_md.as_posix(),
            intervals=tuple(summaries),
            aggregation=aggregation,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
        )
        markdown = build_multi_interval_markdown(config=active_config, result=result)
        active_config.output_md.parent.mkdir(parents=True, exist_ok=True)
        active_config.output_md.write_text(markdown, encoding="utf-8")
        return result


class L1L2MultiIntervalAnswerSmokeFormatter:
    def format(
        self,
        result: L1L2MultiIntervalAnswerSmokeResult,
        *,
        config: L1L2MultiIntervalAnswerSmokeConfig,
    ) -> str:
        lines = [
            "BOOK-L1 -> BOOK-L2 Multi-Interval Answer Smoke",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Intervals: {', '.join(config.intervals)}",
            f"Window size: {config.window_size}",
            f"Window count: {config.window_count}",
            f"Min candles: {config.min_candles}",
            "",
            "Intervals:",
            _format_interval_table(result.intervals),
            "",
            "Answer file:",
            result.output_md,
        ]
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        if config.show_details:
            lines.extend(["", _format_details(result.intervals)])
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_smoke_intervals(intervals: str | None) -> tuple[str, ...]:
    if not intervals:
        return DEFAULT_INTERVALS
    parsed = tuple(item.strip() for item in intervals.split(",") if item.strip())
    return parsed or DEFAULT_INTERVALS


def build_interval_summary(
    *,
    interval: str,
    result: L1L2IntervalAnswerSmokeResult,
    evidence_file: str,
) -> L1L2IntervalAnswerSummary:
    payload = result.l2_payload if isinstance(result.l2_payload, dict) else {}
    l2_result = _dict(payload.get("result"))
    brief = _dict(l2_result.get("market_brief"))
    symbols = _list_of_dicts(l2_result.get("symbols"))
    safety = _dict(payload.get("safety"))
    safety_status = "LOCKED" if _safety_locked(safety) else "UNSAFE"
    error_parts = list(result.errors)
    warning_details = _payload_warning_details(symbols)
    if warning_details:
        error_parts.append(f"L2 warnings: {warning_details}")
    error = "; ".join(dict.fromkeys(error_parts)) if error_parts else None
    return L1L2IntervalAnswerSummary(
        interval=interval,
        status=result.status,
        overall_state=_text(l2_result.get("overall_state"), "N/A"),
        brief=_text(brief.get("brief") or brief.get("brief_state"), "N/A"),
        observation_candidates=_candidate_symbols(brief.get("observation_candidates")),
        skip_candidates=_candidate_symbols(brief.get("skip_candidates")),
        key_points=_text_items(brief.get("key_points")),
        symbol_contexts=_symbol_contexts(symbols, brief),
        symbol_count=len(symbols),
        safety_status=safety_status,
        safety=safety,
        evidence_file=evidence_file,
        error=error,
    )


def aggregate_interval_summaries(
    intervals: tuple[L1L2IntervalAnswerSummary, ...],
) -> L1L2MultiIntervalAggregation:
    status_counts = Counter(summary.status for summary in intervals)
    state_counts = Counter(
        summary.overall_state for summary in intervals if summary.overall_state and summary.overall_state != "N/A"
    )
    observation_counts = Counter(symbol for summary in intervals for symbol in summary.observation_candidates)
    skip_counts = Counter(symbol for summary in intervals for symbol in summary.skip_candidates)
    return L1L2MultiIntervalAggregation(
        interval_count=len(intervals),
        pass_count=status_counts[PASS],
        fail_count=status_counts[FAIL],
        pass_with_warnings_count=status_counts[PASS_WITH_WARNINGS],
        intervals_with_observation_candidates=tuple(
            summary.interval for summary in intervals if summary.observation_candidates
        ),
        intervals_with_all_symbols_skipped=tuple(
            summary.interval
            for summary in intervals
            if summary.symbol_count > 0 and len(summary.skip_candidates) >= summary.symbol_count
        ),
        most_common_overall_state=state_counts.most_common(1)[0][0] if state_counts else "N/A",
        repeated_observation_candidates=tuple(sorted(symbol for symbol, count in observation_counts.items() if count > 1)),
        repeated_skip_candidates=tuple(sorted(symbol for symbol, count in skip_counts.items() if count > 1)),
    )


def validate_multi_interval_answer(intervals: tuple[L1L2IntervalAnswerSummary, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    for summary in intervals:
        for text in (summary.brief or "", *summary.key_points):
            matches = _forbidden_terms_in_text(text)
            if matches:
                errors.append(
                    f"Interval {summary.interval} human answer contains forbidden term(s): "
                    + ", ".join(dict.fromkeys(matches))
                )
        for context in summary.symbol_contexts:
            matches = _forbidden_terms_in_text(context.main_reason)
            if matches:
                errors.append(
                    f"Interval {summary.interval} reason for {context.symbol} contains forbidden term(s): "
                    + ", ".join(dict.fromkeys(matches))
                )
        if summary.safety_status != "LOCKED":
            errors.append(f"Interval {summary.interval} safety is not fail-closed.")
    return tuple(errors)


def build_multi_interval_markdown(
    *,
    config: L1L2MultiIntervalAnswerSmokeConfig,
    result: L1L2MultiIntervalAnswerSmokeResult,
) -> str:
    aggregation = result.aggregation or aggregate_interval_summaries(result.intervals)
    lines = [
        "# L1-L2 Multi-Interval Answer Smoke",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Intervals | {_md(', '.join(config.intervals))} |",
        f"| Window size | `{config.window_size}` |",
        f"| Window count | `{config.window_count}` |",
        f"| Min candles | `{config.min_candles}` |",
        "",
        "## Interval Summary",
        "",
        "| Interval | Status | Overall State | Observation Candidates | Skip Candidates | Safety |",
        "|---|---|---|---|---|---|",
        *[_markdown_summary_row(summary) for summary in result.intervals],
        "",
        "## Actual Answers By Interval",
        "",
    ]
    for summary in result.intervals:
        lines.extend(_interval_markdown(summary))
    lines.extend(
        [
            "## Cross-Interval Observations",
            "",
            f"- Intervals checked: {aggregation.interval_count}",
            f"- Intervals PASS: {aggregation.pass_count}",
            f"- Intervals FAIL: {aggregation.fail_count}",
            f"- Intervals PASS_WITH_WARNINGS: {aggregation.pass_with_warnings_count}",
            f"- Intervals with observation candidates: {_join_or_none(aggregation.intervals_with_observation_candidates)}",
            f"- Intervals with all symbols skipped: {_join_or_none(aggregation.intervals_with_all_symbols_skipped)}",
            f"- Most common overall state: {_md(aggregation.most_common_overall_state)}",
            f"- Symbols repeatedly skipped: {_join_or_none(aggregation.repeated_skip_candidates)}",
            f"- Symbols repeatedly observed: {_join_or_none(aggregation.repeated_observation_candidates)}",
            "",
            "## Source Lineage",
            "",
            "- L1 runtime JSON: `reports/book_l1/timeline_preview.json`",
            "- L2 runtime JSON: `reports/book_l2/timeline_context.json`",
            "- Each interval was processed through L1 -> L2 pipeline.",
            "- Per-interval evidence files are stored in `reports/book_l2/interval_answers/`.",
            "",
            "## Conclusion",
            "",
            "The L1-L2 pipeline produced multi-interval context evidence.",
            "",
            "This is observe-only context. It is not a trading instruction.",
            "",
        ]
    )
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def _interval_markdown(summary: L1L2IntervalAnswerSummary) -> list[str]:
    lines = [
        f"### Interval: {_md(summary.interval)}",
        "",
        "#### Overall",
        "",
        f"- Status: `{summary.status}`",
        f"- Overall state: `{_md(summary.overall_state or 'N/A')}`",
        f"- Brief: {_md(summary.brief or 'N/A')}",
    ]
    if summary.error:
        lines.append(f"- Reason: {_md(summary.error)}")
    lines.extend(
        [
            "",
            "#### Observation candidates",
            "",
            *_list_lines(summary.observation_candidates),
            "",
            "#### Skip candidates",
            "",
            *_list_lines(summary.skip_candidates),
            "",
            "#### Key points",
            "",
            *_list_lines(summary.key_points),
            "",
            "#### Per-symbol Context",
            "",
            "| Rank | Symbol | Bucket | Quality | Score | Skip | Current regime | Stability | Last transition | Main reason |",
            "|---:|---|---|---|---:|---|---|---|---|---|",
            *_context_rows(summary.symbol_contexts),
            "",
            "#### Safety",
            "",
            f"- trade_signal: `{_md(_text(summary.safety.get('trade_signal'), 'N/A'))}`",
            f"- safe_for_runtime_trading: `{_format_value(summary.safety.get('safe_for_runtime_trading'))}`",
            f"- orders_enabled: `{_format_value(summary.safety.get('orders_enabled'))}`",
            f"- live_trading_connected: `{_format_value(summary.safety.get('live_trading_connected'))}`",
            f"- safety_status: `{summary.safety_status}`",
            "",
            f"- Evidence file: `{_md(summary.evidence_file or 'N/A')}`",
            "",
            "---",
            "",
        ]
    )
    return lines


def _format_interval_table(intervals: tuple[L1L2IntervalAnswerSummary, ...]) -> str:
    headers = ("Interval", "Status", "Overall State", "Observation Candidates", "Skip Candidates", "Safety")
    rows = tuple(
        (
            summary.interval,
            summary.status,
            summary.overall_state or "N/A",
            _join_or_none(summary.observation_candidates),
            _join_or_none(summary.skip_candidates),
            summary.safety_status,
        )
        for summary in intervals
    )
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


def _format_details(intervals: tuple[L1L2IntervalAnswerSummary, ...]) -> str:
    lines = ["Details:"]
    for summary in intervals:
        lines.append(
            f"{summary.interval}: state={summary.overall_state or 'N/A'}, "
            f"observation={_join_or_none(summary.observation_candidates)}, "
            f"skip={_join_or_none(summary.skip_candidates)}"
        )
    return "\n".join(lines)


def _result_status(intervals: tuple[L1L2IntervalAnswerSummary, ...], *, strict: bool) -> str:
    if any(summary.status == FAIL for summary in intervals):
        return FAIL if strict else PASS_WITH_WARNINGS
    if any(summary.status == PASS_WITH_WARNINGS for summary in intervals):
        return PASS_WITH_WARNINGS
    return PASS


def _interval_evidence_path(interval: str, *, output_md: Path) -> Path:
    safe_interval = "".join(char if char.isalnum() else "_" for char in interval)
    output_dir = DEFAULT_INTERVAL_OUTPUT_DIR if output_md == DEFAULT_OUTPUT_MD else output_md.parent / "interval_answers"
    return output_dir / f"l1_l2_interval_answer_{safe_interval}.md"


def _markdown_summary_row(summary: L1L2IntervalAnswerSummary) -> str:
    return (
        f"| {_md(summary.interval)} | {summary.status} | {_md(summary.overall_state or 'N/A')} | "
        f"{_md(_join_or_none(summary.observation_candidates))} | "
        f"{_md(_join_or_none(summary.skip_candidates))} | {summary.safety_status} |"
    )


def _context_rows(contexts: tuple[L1L2IntervalSymbolContext, ...]) -> list[str]:
    if not contexts:
        return ["|  | N/A | N/A | N/A |  | N/A | N/A | N/A | N/A | N/A |"]
    return [
        "| "
        + " | ".join(
            (
                _md(context.rank),
                _md(context.symbol),
                _md(context.bucket),
                _md(context.quality),
                _md(context.score),
                _md(context.skip),
                _md(context.current_regime),
                _md(context.stability),
                _md(context.last_transition),
                _md(context.main_reason),
            )
        )
        + " |"
        for context in contexts
    ]


def _symbol_contexts(symbols: tuple[dict[str, Any], ...], brief: dict[str, Any]) -> tuple[L1L2IntervalSymbolContext, ...]:
    reasons = _candidate_reasons(brief)
    sorted_symbols = sorted(
        symbols,
        key=lambda row: (row.get("context_rank") is None, row.get("context_rank") or 10**9, str(row.get("symbol"))),
    )
    contexts: list[L1L2IntervalSymbolContext] = []
    for symbol in sorted_symbols:
        symbol_name = _text(symbol.get("symbol"), "N/A")
        contexts.append(
            L1L2IntervalSymbolContext(
                rank="" if symbol.get("context_rank") is None else str(symbol.get("context_rank")),
                symbol=symbol_name,
                bucket=_text(symbol.get("bucket"), "N/A"),
                quality=_text(symbol.get("context_quality_grade") or symbol.get("quality_grade"), "N/A"),
                score=_score_text(symbol.get("context_quality_score")),
                skip=_format_value(symbol.get("skip_candidate")),
                current_regime=_text(symbol.get("current_regime"), "N/A"),
                stability=_text(symbol.get("stability"), "N/A"),
                last_transition=_text(symbol.get("last_transition"), "N/A"),
                main_reason=reasons.get(symbol_name, "N/A"),
            )
        )
    return tuple(contexts)


def _payload_warning_details(symbols: tuple[dict[str, Any], ...]) -> str:
    details: list[str] = []
    for symbol in symbols:
        warnings = symbol.get("warnings")
        if not isinstance(warnings, list) or not warnings:
            continue
        symbol_name = _text(symbol.get("symbol"), "N/A")
        warning_text = "; ".join(str(warning) for warning in warnings if str(warning).strip())
        if warning_text:
            details.append(f"{symbol_name}: {warning_text}")
    return "; ".join(details)


def _candidate_reasons(brief: dict[str, Any]) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for key in ("observation_candidates", "skip_candidates"):
        for candidate in _list_of_dicts(brief.get(key)):
            symbol = _text(candidate.get("symbol"), "")
            reason = _text(candidate.get("main_reason"), "")
            if symbol and reason:
                reasons[symbol] = reason
    return reasons


def _candidate_symbols(value: Any) -> tuple[str, ...]:
    return tuple(_text(candidate.get("symbol"), "N/A") for candidate in _list_of_dicts(value))


def _text_items(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _list_lines(values: tuple[str, ...]) -> list[str]:
    if not values:
        return ["- none"]
    return [f"- {_md(value)}" for value in values]


def _join_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _safety_locked(safety: dict[str, Any]) -> bool:
    for field_name, expected in EXPECTED_SAFETY_FIELDS.items():
        if safety.get(field_name) != expected:
            return False
    if "observe_only" in safety and safety.get("observe_only") is not True:
        return False
    return True


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
    "DEFAULT_INTERVALS",
    "DEFAULT_OUTPUT_MD",
    "L1L2IntervalAnswerSummary",
    "L1L2IntervalSymbolContext",
    "L1L2MultiIntervalAggregation",
    "L1L2MultiIntervalAnswerSmokeConfig",
    "L1L2MultiIntervalAnswerSmokeFormatter",
    "L1L2MultiIntervalAnswerSmokeResult",
    "L1L2MultiIntervalAnswerSmokeRunner",
    "aggregate_interval_summaries",
    "build_multi_interval_markdown",
    "parse_smoke_intervals",
    "validate_multi_interval_answer",
]
