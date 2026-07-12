from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_L2_ANSWER_MD = Path("reports/book_l2/l1_l2_interval_answer.md")
DEFAULT_STABILIZATION_JSON = Path("reports/book_data/market_reader_15m_stabilization.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_l1/market_reader_15m_quality_review.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l1/market_reader_15m_quality_review.md")

SERVICE_NAME = "BOOK_L1_MARKET_READER"
REPORT_TYPE = "market_reader_15m_quality_review"
CONTRACT_VERSION = "book_l1_15m_quality_review_v1"

PASS = "PASS"
PASS_WITH_QUALITY_WARNINGS = "PASS_WITH_QUALITY_WARNINGS"
FAIL = "FAIL"

UNKNOWN_REGIME_DOMINANT = "UNKNOWN_REGIME_DOMINANT"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
MIXED_TREND_STRUCTURE = "MIXED_TREND_STRUCTURE"
RANGE_DOMINANT = "RANGE_DOMINANT"
NO_ACTIVE_BREAKOUT = "NO_ACTIVE_BREAKOUT"
CONFLICTING_TECHNICAL_CONTEXT = "CONFLICTING_TECHNICAL_CONTEXT"
INSUFFICIENT_REASON_DETAIL = "INSUFFICIENT_REASON_DETAIL"
ALL_SYMBOLS_SKIPPED = "ALL_SYMBOLS_SKIPPED"
NO_OBSERVATION_CANDIDATES = "NO_OBSERVATION_CANDIDATES"
STABLE_PIPELINE_BUT_WEAK_CONTEXT = "STABLE_PIPELINE_BUT_WEAK_CONTEXT"
CONTRACT_FIELD_MISSING = "CONTRACT_FIELD_MISSING"

LOW_CONFIDENCE_THRESHOLD = 0.45

CRITICAL_SAFETY_FIELDS: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "live_trading_connected": False,
}


@dataclass(frozen=True)
class MarketReader15mQualityReviewConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    window_size: int = 300
    window_count: int = 4
    min_candles: int = 50
    l1_timeline_json: Path = DEFAULT_L1_TIMELINE_JSON
    l2_context_json: Path = DEFAULT_L2_CONTEXT_JSON
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False
    l2_answer_md: Path = DEFAULT_L2_ANSWER_MD
    stabilization_json: Path = DEFAULT_STABILIZATION_JSON

    def __post_init__(self) -> None:
        symbols = normalize_symbols(self.symbols)
        object.__setattr__(self, "symbols", symbols or DEFAULT_SYMBOLS)
        object.__setattr__(self, "interval", str(self.interval).strip() or ALLOWED_INTERVAL)
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))
        object.__setattr__(self, "l2_answer_md", Path(self.l2_answer_md))
        object.__setattr__(self, "stabilization_json", Path(self.stabilization_json))


@dataclass(frozen=True)
class SymbolQualityReview:
    symbol: str
    market_regime: str
    confidence: float | None
    l1_reason_codes: tuple[str, ...] = ()
    l2_bucket: str | None = None
    l2_skip_candidate: bool | None = None
    l2_quality_score: float | None = None
    l2_quality_grade: str | None = None
    l2_main_reason: str | None = None
    findings: tuple[str, ...] = ()
    recommended_next_focus: tuple[str, ...] = ()
    directional_bias: str | None = None
    trend_strength: str | None = None
    stability: str | None = None
    last_transition: str | None = None
    l2_context_reason_codes: tuple[str, ...] = ()
    l2_context_quality_reason_codes: tuple[str, ...] = ()
    timeline_windows: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class MarketReader15mQualityReviewResult:
    status: str
    overall_state: str | None = None
    symbols: tuple[SymbolQualityReview, ...] = ()
    global_findings: tuple[str, ...] = ()
    next_focus: tuple[str, ...] = ()
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    observation_candidates: tuple[str, ...] = ()
    skip_candidates: tuple[str, ...] = ()
    reason_code_counts: dict[str, int] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_QUALITY_WARNINGS}


class MarketReader15mQualityReviewRunner:
    def run(self, config: MarketReader15mQualityReviewConfig | None = None) -> MarketReader15mQualityReviewResult:
        active_config = config or MarketReader15mQualityReviewConfig()
        warnings: list[str] = []
        errors: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            message = f"BOOK-L1-26 reviews only 15m; requested interval was {active_config.interval}."
            result = MarketReader15mQualityReviewResult(
                status=FAIL,
                overall_state=None,
                global_findings=(),
                next_focus=default_next_focus(),
                warnings=(),
                errors=(message,),
                safety=build_review_safety_payload(None),
            )
            self._write_outputs(active_config, result)
            return result

        l1_read = read_json(active_config.l1_timeline_json)
        if l1_read.error:
            errors.append(l1_read.error)
        l2_read = read_json(active_config.l2_context_json)
        if l2_read.error:
            errors.append(l2_read.error)
        if errors:
            result = MarketReader15mQualityReviewResult(
                status=FAIL,
                global_findings=(),
                next_focus=default_next_focus(),
                warnings=tuple(warnings),
                errors=tuple(errors),
                safety=build_review_safety_payload(_dict(l2_read.value)),
            )
            self._write_outputs(active_config, result)
            return result

        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)
        contract_errors = validate_contracts(active_config, l1_payload, l2_payload)
        safety_errors = validate_fail_closed_safety(l1_payload, l2_payload)
        errors.extend(contract_errors)
        errors.extend(safety_errors)

        symbol_reviews = tuple(build_symbol_review(symbol, l1_payload=l1_payload, l2_payload=l2_payload) for symbol in active_config.symbols)
        contract_findings = tuple(CONTRACT_FIELD_MISSING for review in symbol_reviews if CONTRACT_FIELD_MISSING in review.findings)
        if contract_findings:
            errors.append("Required L1/L2 contract fields are missing for one or more symbols.")

        overall_state = extract_l2_overall_state(l2_payload)
        observation_candidates = extract_candidate_symbols(l2_payload, "observation_candidates")
        skip_candidates = extract_candidate_symbols(l2_payload, "skip_candidates")
        global_findings = classify_global_findings(
            reviews=symbol_reviews,
            overall_state=overall_state,
            requested_symbols=active_config.symbols,
            observation_candidates=observation_candidates,
            skip_candidates=skip_candidates,
        )
        reason_code_counts = count_l1_reason_codes(symbol_reviews)

        if errors:
            status = FAIL
        elif has_useful_context(symbol_reviews):
            status = PASS
        else:
            status = PASS_WITH_QUALITY_WARNINGS

        result = MarketReader15mQualityReviewResult(
            status=status,
            overall_state=overall_state,
            symbols=symbol_reviews,
            global_findings=global_findings,
            next_focus=default_next_focus(),
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
            observation_candidates=observation_candidates,
            skip_candidates=skip_candidates,
            reason_code_counts=reason_code_counts,
            safety=build_review_safety_payload(l2_payload),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(
        self,
        config: MarketReader15mQualityReviewConfig,
        result: MarketReader15mQualityReviewResult,
    ) -> None:
        try:
            json_path = write_quality_review_json(config, result)
            md_path = write_quality_review_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError:
            # The runner reports writer failures only through explicit write helpers in tests.
            pass


class MarketReader15mQualityReviewFormatter:
    def format(self, result: MarketReader15mQualityReviewResult, *, config: MarketReader15mQualityReviewConfig) -> str:
        lines = [
            "BOOK-L1-26 15m Market Reader Quality Review",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"Window size: {config.window_size}",
            f"Window count: {config.window_count}",
            f"Min candles: {config.min_candles}",
            "",
            "Current 15m answer:",
            f"Overall state: {result.overall_state or 'N/A'}",
            f"Observation candidates: {_join_or_none(result.observation_candidates)}",
            f"Skip candidates: {_join_or_none(result.skip_candidates)}",
            "",
            "Global findings:",
            *([f"- {finding}" for finding in result.global_findings] if result.global_findings else ["- none"]),
            "",
            "Symbols:",
            format_symbol_table(result.symbols),
            "",
            "Recommended next focus:",
            "- inspect L1 reason codes",
            "- inspect UNKNOWN composer path",
            "- review trend/range/breakout contribution",
            "",
            "Output files:",
            result.output_json or config.output_json.as_posix(),
            result.output_md or config.output_md.as_posix(),
        ]
        if config.show_details:
            lines.extend(["", "Details:"])
            for review in result.symbols:
                lines.append(f"- {review.symbol}: findings={_join_or_none(review.findings)}; reasons={_join_or_none(review.l1_reason_codes)}")
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_quality_review_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_contracts(config: MarketReader15mQualityReviewConfig, l1_payload: dict[str, Any], l2_payload: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match review interval.")
    if l1_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if l2_payload.get("service") != "BOOK_L2_MARKET_INTERPRETER":
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    if not isinstance(_nested_dict(l2_payload, "result").get("market_brief"), dict):
        errors.append("L2 context JSON must contain result.market_brief.")
    return tuple(errors)


def validate_fail_closed_safety(l1_payload: dict[str, Any], l2_payload: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for source_name, payload in (("L1", l1_payload), ("L2", l2_payload)):
        safety = _dict(payload.get("safety"))
        if not safety:
            errors.append(f"{source_name} safety must be an object.")
            continue
        for field_name, expected in CRITICAL_SAFETY_FIELDS.items():
            if field_name not in safety:
                errors.append(f"{source_name} safety missing field: {field_name}")
            elif safety[field_name] != expected:
                errors.append(f"{source_name} safety.{field_name} must be {_format_value(expected)}")
    return tuple(errors)


def build_symbol_review(symbol: str, *, l1_payload: dict[str, Any], l2_payload: dict[str, Any]) -> SymbolQualityReview:
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    current = extract_current_window(l1_row)
    l2_main_reason = extract_l2_main_reason(l2_payload, symbol) or _text(l2_row.get("observe_reason") if l2_row else None)
    l1_reason_codes = tuple(str(item) for item in _list(current.get("reason_codes")))
    confidence = _optional_float(current.get("confidence"))
    market_regime = _token(current.get("market_regime"), "UNKNOWN")
    findings = classify_symbol_findings(
        market_regime=market_regime,
        confidence=confidence,
        l1_reason_codes=l1_reason_codes,
        l2_row=l2_row,
        has_contract_fields=has_required_symbol_contract_fields(l1_row, l2_row, current),
    )
    return SymbolQualityReview(
        symbol=symbol,
        market_regime=market_regime,
        confidence=confidence,
        l1_reason_codes=l1_reason_codes,
        l2_bucket=_text(l2_row.get("bucket") if l2_row else None),
        l2_skip_candidate=_optional_bool(l2_row.get("skip_candidate") if l2_row else None),
        l2_quality_score=_optional_float(l2_row.get("context_quality_score") if l2_row else None),
        l2_quality_grade=_text(l2_row.get("context_quality_grade") if l2_row else None),
        l2_main_reason=l2_main_reason,
        findings=findings,
        recommended_next_focus=build_symbol_next_focus(findings),
        directional_bias=_text(current.get("directional_bias")),
        trend_strength=_text(current.get("trend_strength")),
        stability=_text(l1_row.get("stability") if l1_row else None),
        last_transition=_text(l1_row.get("last_transition") if l1_row else None),
        l2_context_reason_codes=tuple(str(item) for item in _list(l2_row.get("context_reason_codes") if l2_row else None)),
        l2_context_quality_reason_codes=tuple(str(item) for item in _list(l2_row.get("context_quality_reason_codes") if l2_row else None)),
        timeline_windows=extract_timeline_windows(l1_row),
    )


def has_required_symbol_contract_fields(
    l1_row: dict[str, Any] | None,
    l2_row: dict[str, Any] | None,
    current: dict[str, Any],
) -> bool:
    if not l1_row or not l2_row or not current:
        return False
    l1_required = ("market_regime", "confidence", "reason_codes")
    l2_required = ("bucket", "skip_candidate", "context_quality_score", "context_quality_grade")
    return all(field in current for field in l1_required) and all(field in l2_row for field in l2_required)


def classify_symbol_findings(
    *,
    market_regime: str,
    confidence: float | None,
    l1_reason_codes: tuple[str, ...],
    l2_row: dict[str, Any] | None,
    has_contract_fields: bool,
) -> tuple[str, ...]:
    findings: list[str] = []
    reason_set = set(l1_reason_codes)
    l2_bucket = _token(l2_row.get("bucket") if l2_row else None, "")

    if not has_contract_fields:
        findings.append(CONTRACT_FIELD_MISSING)
    if market_regime == "UNKNOWN" or l2_bucket == "UNKNOWN":
        findings.append(UNKNOWN_REGIME_DOMINANT)
    if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
        findings.append(LOW_CONFIDENCE)
    if "MIXED_SWING_STRUCTURE" in reason_set or "COMPOSER_MIXED_OR_WEAK_CONTEXT" in reason_set:
        findings.append(MIXED_TREND_STRUCTURE)
    if "COMPOSER_FLAT_RANGE_DOMINANT" in reason_set or "RANGE_STRUCTURE_DETECTED" in reason_set:
        findings.append(RANGE_DOMINANT)
    if reason_set.intersection({"NO_ACTIVE_BREAKOUT", "NO_CLOSE_BREAKOUT", "PRICE_INSIDE_RANGE"}):
        findings.append(NO_ACTIVE_BREAKOUT)
    if reason_set.intersection({"EMA_TREND_MIXED", "TECHNICAL_CONTEXT_NEUTRAL", "TECHNICAL_CONTEXT_CONFLICTING"}):
        findings.append(CONFLICTING_TECHNICAL_CONTEXT)
    if not l1_reason_codes:
        findings.append(INSUFFICIENT_REASON_DETAIL)
    return tuple(dict.fromkeys(findings))


def classify_global_findings(
    *,
    reviews: tuple[SymbolQualityReview, ...],
    overall_state: str | None,
    requested_symbols: tuple[str, ...],
    observation_candidates: tuple[str, ...],
    skip_candidates: tuple[str, ...],
) -> tuple[str, ...]:
    findings: list[str] = []
    if requested_symbols and all(review.l2_skip_candidate is True for review in reviews):
        findings.append(ALL_SYMBOLS_SKIPPED)
    elif requested_symbols and set(skip_candidates) >= set(requested_symbols):
        findings.append(ALL_SYMBOLS_SKIPPED)
    if not observation_candidates:
        findings.append(NO_OBSERVATION_CANDIDATES)
    if overall_state == "UNKNOWN" or ALL_SYMBOLS_SKIPPED in findings or NO_OBSERVATION_CANDIDATES in findings:
        findings.append(STABLE_PIPELINE_BUT_WEAK_CONTEXT)
    for review in reviews:
        if CONTRACT_FIELD_MISSING in review.findings:
            findings.append(CONTRACT_FIELD_MISSING)
            break
    return tuple(dict.fromkeys(findings))


def has_useful_context(reviews: tuple[SymbolQualityReview, ...]) -> bool:
    for review in reviews:
        if review.l2_skip_candidate:
            continue
        if review.l2_quality_grade in {"HIGH", "MEDIUM"}:
            return True
        if review.market_regime in {"UP", "DOWN", "FLAT"} and review.l2_bucket not in {None, "UNKNOWN", "ERROR"}:
            return True
    return False


def build_symbol_next_focus(findings: tuple[str, ...]) -> tuple[str, ...]:
    focus: list[str] = []
    if UNKNOWN_REGIME_DOMINANT in findings:
        focus.append("review composer unknown decision path")
    if MIXED_TREND_STRUCTURE in findings:
        focus.append("review trend structure reason codes")
    if RANGE_DOMINANT in findings:
        focus.append("review range dominance contribution")
    if NO_ACTIVE_BREAKOUT in findings:
        focus.append("review breakout/retest contribution")
    if CONFLICTING_TECHNICAL_CONTEXT in findings:
        focus.append("review technical context conflicts")
    if LOW_CONFIDENCE in findings:
        focus.append("review low confidence windows")
    if not focus:
        focus.append("continue monitoring readable 15m context")
    return tuple(dict.fromkeys(focus))


def default_next_focus() -> tuple[str, ...]:
    return (
        "BOOK-L1-27 - 15m Reason Codes Inspection",
        "BOOK-L1-28 - 15m UNKNOWN/FLAT Reduction Diagnostic",
    )


def build_json_payload(config: MarketReader15mQualityReviewConfig, result: MarketReader15mQualityReviewResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "request": {
            "symbols": list(config.symbols),
            "interval": config.interval,
            "window_size": config.window_size,
            "window_count": config.window_count,
            "min_candles": config.min_candles,
        },
        "source_artifacts": source_artifacts(config),
        "overall": {
            "l2_overall_state": result.overall_state,
            "observation_candidates": list(result.observation_candidates),
            "skip_candidates": list(result.skip_candidates),
            "global_findings": list(result.global_findings),
            "reason_code_counts": dict(result.reason_code_counts),
        },
        "symbols": [symbol_review_to_dict(review) for review in result.symbols],
        "next_focus": list(result.next_focus),
        "safety": result.safety,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def write_quality_review_json(config: MarketReader15mQualityReviewConfig, result: MarketReader15mQualityReviewResult) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_quality_review_markdown(config: MarketReader15mQualityReviewConfig, result: MarketReader15mQualityReviewResult) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def build_markdown(config: MarketReader15mQualityReviewConfig, result: MarketReader15mQualityReviewResult) -> str:
    lines = [
        "# BOOK-L1-26 - 15m Market Reader Quality Review",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage reviews the quality of the current 15m Market Reader output.",
        "",
        "It does not change market analysis logic.",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Interval | {_md(config.interval)} |",
        f"| Window size | {config.window_size} |",
        f"| Window count | {config.window_count} |",
        f"| Min candles | {config.min_candles} |",
        "",
        "## Source Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        f"| L1 timeline JSON | {_md(config.l1_timeline_json.as_posix())} |",
        f"| L2 context JSON | {_md(config.l2_context_json.as_posix())} |",
        f"| L2 answer Markdown | {_md(config.l2_answer_md.as_posix())} |",
        f"| 15m stabilization JSON | {_md(config.stabilization_json.as_posix())} |",
        "",
        "## Current 15m Answer",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| L2 overall state | {_md(result.overall_state or 'N/A')} |",
        f"| Observation candidates | {_md(_join_or_none(result.observation_candidates))} |",
        f"| Skip candidates | {_md(_join_or_none(result.skip_candidates))} |",
        "",
        "## Global Findings",
        "",
        *([f"- {_md(finding)}" for finding in result.global_findings] if result.global_findings else ["- none"]),
        "",
        "## Per-Symbol Review",
        "",
        "| Symbol | L1 Regime | Confidence | L2 Bucket | L2 Quality | Skip | Main Findings |",
        "|---|---|---:|---|---|---|---|",
        *[symbol_markdown_row(review) for review in result.symbols],
        "",
        "## Symbol Details",
        "",
    ]
    for review in result.symbols:
        lines.extend(symbol_detail_lines(review))
    lines.extend(
        [
            "## What This Means",
            "",
            meaning_text(result),
            "",
            "This is a quality issue, not a pipeline failure." if result.status == PASS_WITH_QUALITY_WARNINGS else "The review outcome is based on the current evidence files.",
            "",
            "## Safety",
            "",
            "- read_only: `true`",
            "- market_logic_changed: `false`",
            "- trading_signal: `NOT_EVALUATED`",
            "- safe_for_runtime_trading: `false`",
            "- live_trading_connected: `false`",
            "",
            "## Recommended Next Stage",
            "",
            "`BOOK-L1-27 - 15m Reason Codes Inspection`",
            "",
            "or:",
            "",
            "`BOOK-L1-28 - 15m UNKNOWN/FLAT Reduction Diagnostic`",
            "",
            "## Conclusion",
            "",
            "Continue improving Market Reader quality on `15m`.",
            "",
            "Do not move to runtime execution, interval expansion, or BOOK-L3 yet.",
            "",
        ]
    )
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def symbol_markdown_row(review: SymbolQualityReview) -> str:
    return (
        f"| {_md(review.symbol)} | {_md(review.market_regime)} | {_confidence_text(review.confidence)} | "
        f"{_md(review.l2_bucket or 'N/A')} | {_md(review.l2_quality_grade or 'N/A')} | "
        f"{_format_value(review.l2_skip_candidate)} | {_md(_join_or_none(review.findings))} |"
    )


def symbol_detail_lines(review: SymbolQualityReview) -> list[str]:
    lines = [
        f"### {_md(review.symbol)}",
        "",
        "#### L1",
        "",
        f"- Market regime: `{_md(review.market_regime)}`",
        f"- Confidence: `{_confidence_text(review.confidence)}`",
        f"- Directional bias: `{_md(review.directional_bias or 'N/A')}`",
        f"- Trend strength: `{_md(review.trend_strength or 'N/A')}`",
        f"- Stability: `{_md(review.stability or 'N/A')}`",
        f"- Last transition: `{_md(review.last_transition or 'N/A')}`",
        "- Reason codes:",
        *([f"  - {_md(code)}" for code in review.l1_reason_codes] if review.l1_reason_codes else ["  - none"]),
        "",
        "#### L2",
        "",
        f"- Bucket: `{_md(review.l2_bucket or 'N/A')}`",
        f"- Skip candidate: `{_format_value(review.l2_skip_candidate)}`",
        f"- Quality score: `{_score_text(review.l2_quality_score)}`",
        f"- Quality grade: `{_md(review.l2_quality_grade or 'N/A')}`",
        f"- Main reason: {_md(review.l2_main_reason or 'N/A')}",
        "- Context reason codes:",
        *([f"  - {_md(code)}" for code in review.l2_context_reason_codes] if review.l2_context_reason_codes else ["  - none"]),
        "- Quality reason codes:",
        *([f"  - {_md(code)}" for code in review.l2_context_quality_reason_codes] if review.l2_context_quality_reason_codes else ["  - none"]),
        "",
        "#### Quality findings",
        "",
        *([f"- {_md(finding)}" for finding in review.findings] if review.findings else ["- none"]),
        "",
        "#### Recommended next focus",
        "",
        *[f"- {_md(focus)}" for focus in review.recommended_next_focus],
        "",
    ]
    return lines


def meaning_text(result: MarketReader15mQualityReviewResult) -> str:
    if result.status == FAIL:
        return "The current 15m quality review could not be completed from the available evidence."
    if result.status == PASS_WITH_QUALITY_WARNINGS:
        return "The current 15m pipeline is technically stable, but the Market Reader does not yet produce a strong readable market context for the tested symbols."
    return "The current 15m evidence contains at least one readable market context for review."


def format_symbol_table(reviews: tuple[SymbolQualityReview, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "L2 Bucket", "L2 Quality", "Skip")
    rows = tuple(
        (
            review.symbol,
            review.market_regime,
            _confidence_text(review.confidence),
            review.l2_bucket or "N/A",
            review.l2_quality_grade or "N/A",
            _format_value(review.l2_skip_candidate),
        )
        for review in reviews
    )
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _table_row(headers, widths), border]
    lines.extend(_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def build_review_safety_payload(l2_payload: dict[str, Any] | None) -> dict[str, Any]:
    l2_safety = _dict(l2_payload.get("safety") if isinstance(l2_payload, dict) else None)
    payload = {
        "read_only": True,
        "market_logic_changed": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
    }
    for field_name in ("trade_signal", "orders_enabled", "traders_core_connected", "approved_for_live_trading", "approved_for_auto_activation"):
        if field_name in l2_safety:
            payload[field_name] = l2_safety[field_name]
    return payload


def source_artifacts(config: MarketReader15mQualityReviewConfig) -> dict[str, str]:
    return {
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
        "l2_answer_md": config.l2_answer_md.as_posix(),
        "stabilization_json": config.stabilization_json.as_posix(),
    }


def symbol_review_to_dict(review: SymbolQualityReview) -> dict[str, Any]:
    payload = asdict(review)
    for key in (
        "l1_reason_codes",
        "findings",
        "recommended_next_focus",
        "l2_context_reason_codes",
        "l2_context_quality_reason_codes",
        "timeline_windows",
    ):
        payload[key] = list(payload[key])
    return payload


def count_l1_reason_codes(reviews: tuple[SymbolQualityReview, ...]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for review in reviews:
        counter.update(review.l1_reason_codes)
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def extract_l2_overall_state(l2_payload: dict[str, Any]) -> str | None:
    return _text(_nested_dict(l2_payload, "result").get("overall_state"))


def extract_candidate_symbols(l2_payload: dict[str, Any], field_name: str) -> tuple[str, ...]:
    brief = _dict(_nested_dict(l2_payload, "result").get("market_brief"))
    return tuple(str(candidate.get("symbol")).strip().upper() for candidate in _list_of_dicts(brief.get(field_name)) if candidate.get("symbol"))


def extract_l2_main_reason(l2_payload: dict[str, Any], symbol: str) -> str | None:
    brief = _dict(_nested_dict(l2_payload, "result").get("market_brief"))
    for key in ("observation_candidates", "skip_candidates"):
        candidate = find_symbol_row(_list_of_dicts(brief.get(key)), symbol)
        if candidate:
            return _text(candidate.get("main_reason"))
    return None


def find_symbol_row(rows: tuple[dict[str, Any], ...], symbol: str) -> dict[str, Any] | None:
    normalized = str(symbol).strip().upper()
    for row in rows:
        if str(row.get("symbol", "")).strip().upper() == normalized:
            return row
    return None


def extract_current_window(l1_row: dict[str, Any] | None) -> dict[str, Any]:
    if not l1_row:
        return {}
    windows = _list_of_dicts(l1_row.get("windows"))
    if windows:
        for window in reversed(windows):
            label = str(window.get("label") or window.get("window_label") or "").strip().upper()
            if label == "CURRENT":
                return window
        return windows[-1]
    return {
        "market_regime": _extract_current_regime(l1_row),
        "confidence": l1_row.get("current_confidence"),
        "trend_strength": l1_row.get("current_trend_strength"),
        "reason_codes": l1_row.get("reason_codes", []),
    }


def extract_timeline_windows(l1_row: dict[str, Any] | None) -> tuple[dict[str, Any], ...]:
    if not l1_row:
        return ()
    windows = []
    for window in _list_of_dicts(l1_row.get("windows")):
        windows.append(
            {
                "label": window.get("label") or window.get("window_label"),
                "market_regime": window.get("market_regime"),
                "confidence": window.get("confidence"),
                "trend_strength": window.get("trend_strength"),
                "reason_codes": list(_list(window.get("reason_codes"))),
            }
        )
    return tuple(windows)


def _extract_current_regime(row: dict[str, Any]) -> str:
    regimes = _list(row.get("regimes"))
    if regimes:
        return _token(regimes[-1], "UNKNOWN")
    return _token(row.get("current_regime"), "UNKNOWN")


@dataclass(frozen=True)
class JsonReadResult:
    value: Any = None
    error: str | None = None


def read_json(path: Path) -> JsonReadResult:
    if not path.is_file():
        return JsonReadResult(error=f"Required artifact is missing: {path.as_posix()}. Run book-data-15m-stabilization first.")
    try:
        return JsonReadResult(value=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return JsonReadResult(error=f"Invalid JSON in {path.as_posix()}: {exc.msg}")
    except OSError as exc:
        return JsonReadResult(error=f"Could not read {path.as_posix()}: {exc}")


def _nested_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    return _dict(payload.get(key))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _token(value: Any, default: str) -> str:
    text = str(value or "").strip().upper()
    return text or default


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _confidence_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _score_text(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "N/A"
    return str(value)


def _join_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "ALLOWED_INTERVAL",
    "CONTRACT_VERSION",
    "DEFAULT_OUTPUT_JSON",
    "DEFAULT_OUTPUT_MD",
    "FAIL",
    "PASS",
    "PASS_WITH_QUALITY_WARNINGS",
    "ALL_SYMBOLS_SKIPPED",
    "CONTRACT_FIELD_MISSING",
    "LOW_CONFIDENCE",
    "MIXED_TREND_STRUCTURE",
    "NO_ACTIVE_BREAKOUT",
    "NO_OBSERVATION_CANDIDATES",
    "UNKNOWN_REGIME_DOMINANT",
    "MarketReader15mQualityReviewConfig",
    "MarketReader15mQualityReviewFormatter",
    "MarketReader15mQualityReviewResult",
    "MarketReader15mQualityReviewRunner",
    "SymbolQualityReview",
    "build_json_payload",
    "build_markdown",
    "parse_quality_review_symbols",
    "write_quality_review_json",
    "write_quality_review_markdown",
]
