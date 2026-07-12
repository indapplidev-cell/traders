from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_QUALITY_REVIEW_JSON = Path("reports/book_l1/market_reader_15m_quality_review.json")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_l1/l1_l2_regime_alignment_review.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l1/l1_l2_regime_alignment_review.md")

SERVICE_NAME = "BOOK_L1_MARKET_READER"
REPORT_TYPE = "l1_l2_regime_alignment_review"
CONTRACT_VERSION = "book_l1_l2_regime_alignment_review_v1"

PASS = "PASS"
PASS_WITH_ALIGNMENT_WARNINGS = "PASS_WITH_ALIGNMENT_WARNINGS"
FAIL = "FAIL"

HIGH_CONFIDENCE_THRESHOLD = 0.75

L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP = "L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP"
L1_UNKNOWN_PROPAGATED_TO_L2_SKIP = "L1_UNKNOWN_PROPAGATED_TO_L2_SKIP"
L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS = "L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS"
L2_SKIPS_FLAT_CONTEXT = "L2_SKIPS_FLAT_CONTEXT"
L2_FLAT_CONTEXT_NOT_OBSERVABLE = "L2_FLAT_CONTEXT_NOT_OBSERVABLE"
L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE = "L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE"
L1_TO_L2_REGIME_FIELD_MISSING = "L1_TO_L2_REGIME_FIELD_MISSING"
L1_TO_L2_CONFIDENCE_FIELD_MISSING = "L1_TO_L2_CONFIDENCE_FIELD_MISSING"
L2_CONTEXT_REASON_CODES_MISSING = "L2_CONTEXT_REASON_CODES_MISSING"
L2_MAIN_REASON_MISSING = "L2_MAIN_REASON_MISSING"
FIELD_MAPPING_NEEDS_REVIEW = "FIELD_MAPPING_NEEDS_REVIEW"
CONTRACT_ALIGNMENT_NEEDS_REVIEW = "CONTRACT_ALIGNMENT_NEEDS_REVIEW"
ALL_SYMBOLS_SKIPPED = "ALL_SYMBOLS_SKIPPED"
NO_OBSERVATION_CANDIDATES = "NO_OBSERVATION_CANDIDATES"
L1_TO_L2_REGIME_MISMATCH = "L1_TO_L2_REGIME_MISMATCH"

RECOMMENDED_NEXT_STAGE = "BOOK-L1-28 - FLAT Context Alignment Diagnostic"

CRITICAL_FALSE_FIELDS = (
    "safe_for_runtime_trading",
    "live_trading_connected",
    "orders_enabled",
    "traders_core_connected",
    "approved_for_live_trading",
    "approved_for_auto_activation",
)


@dataclass(frozen=True)
class RegimeAlignmentReviewConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    quality_review_json: Path = DEFAULT_QUALITY_REVIEW_JSON
    l1_timeline_json: Path = DEFAULT_L1_TIMELINE_JSON
    l2_context_json: Path = DEFAULT_L2_CONTEXT_JSON
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbols", normalize_symbols(self.symbols) or DEFAULT_SYMBOLS)
        object.__setattr__(self, "interval", str(self.interval).strip() or ALLOWED_INTERVAL)
        object.__setattr__(self, "quality_review_json", Path(self.quality_review_json))
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class SymbolRegimeAlignment:
    symbol: str
    l1_regime: str | None
    l1_confidence: float | None
    l1_reason_codes: tuple[str, ...] = ()
    l1_directional_bias: str | None = None
    l1_trend_strength: str | None = None
    l1_timeline_stability: str | None = None
    l1_last_transition: str | None = None
    l2_received_regime: str | None = None
    l2_received_confidence: float | None = None
    l2_overall_state: str | None = None
    l2_bucket: str | None = None
    l2_skip_candidate: bool | None = None
    l2_quality_score: float | None = None
    l2_quality_grade: str | None = None
    l2_main_reason: str | None = None
    l2_context_reason_codes: tuple[str, ...] = ()
    l2_context_quality_reason_codes: tuple[str, ...] = ()
    alignment_status: str = "UNKNOWN"
    findings: tuple[str, ...] = ()
    interpretation: str | None = None
    recommended_next_focus: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegimeAlignmentReviewResult:
    status: str
    interval: str = ALLOWED_INTERVAL
    overall_state: str | None = None
    alignments: tuple[SymbolRegimeAlignment, ...] = ()
    global_findings: tuple[str, ...] = ()
    recommended_next_stage: str | None = None
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    safety: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_ALIGNMENT_WARNINGS}


class RegimeAlignmentReviewRunner:
    def run(self, config: RegimeAlignmentReviewConfig | None = None) -> RegimeAlignmentReviewResult:
        active_config = config or RegimeAlignmentReviewConfig()
        warnings: list[str] = []
        errors: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            result = RegimeAlignmentReviewResult(
                status=FAIL,
                interval=active_config.interval,
                recommended_next_stage=RECOMMENDED_NEXT_STAGE,
                errors=(
                    f"BOOK-L1-27 reviews only 15m alignment; requested interval was {active_config.interval}.",
                ),
                safety=build_review_safety_payload(),
            )
            self._write_outputs(active_config, result)
            return result

        quality_read = read_json(active_config.quality_review_json, missing_hint="Run book-l1-15m-quality-review first.")
        l1_read = read_json(active_config.l1_timeline_json, missing_hint="Run book-l1-timeline-preview export first.")
        l2_read = read_json(active_config.l2_context_json, missing_hint="Run book-l2-timeline-context export first.")
        for read_result in (quality_read, l1_read, l2_read):
            if read_result.error:
                errors.append(read_result.error)

        if errors:
            result = RegimeAlignmentReviewResult(
                status=FAIL,
                interval=active_config.interval,
                recommended_next_stage=RECOMMENDED_NEXT_STAGE,
                errors=tuple(errors),
                safety=build_review_safety_payload(),
            )
            self._write_outputs(active_config, result)
            return result

        quality_payload = _dict(quality_read.value)
        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)
        errors.extend(validate_source_contracts(active_config, quality_payload, l1_payload, l2_payload))
        errors.extend(validate_fail_closed_safety(quality_payload, l1_payload, l2_payload))

        alignments = tuple(
            build_symbol_alignment(
                symbol,
                quality_payload=quality_payload,
                l1_payload=l1_payload,
                l2_payload=l2_payload,
            )
            for symbol in active_config.symbols
        )

        if not any(alignment.l1_regime or alignment.l2_bucket for alignment in alignments):
            errors.append("Could not match requested symbols between L1 and L2 artifacts.")
        if any(_has_critical_contract_finding(alignment) for alignment in alignments):
            errors.append("Required L1/L2 alignment fields are missing for one or more symbols.")

        overall_state = extract_l2_overall_state(l2_payload)
        global_findings = classify_global_findings(
            alignments=alignments,
            l2_payload=l2_payload,
            overall_state=overall_state,
        )

        if errors:
            status = FAIL
        elif global_findings or any(alignment.alignment_status == "WARNING" for alignment in alignments):
            status = PASS_WITH_ALIGNMENT_WARNINGS
        else:
            status = PASS

        result = RegimeAlignmentReviewResult(
            status=status,
            interval=active_config.interval,
            overall_state=overall_state,
            alignments=alignments,
            global_findings=global_findings,
            recommended_next_stage=RECOMMENDED_NEXT_STAGE,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
            safety=build_review_safety_payload(quality_payload, l1_payload, l2_payload),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(self, config: RegimeAlignmentReviewConfig, result: RegimeAlignmentReviewResult) -> None:
        try:
            json_path = write_regime_alignment_review_json(config, result)
            md_path = write_regime_alignment_review_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError:
            pass


class RegimeAlignmentReviewFormatter:
    def format(self, result: RegimeAlignmentReviewResult, *, config: RegimeAlignmentReviewConfig) -> str:
        lines = [
            "BOOK-L1-27 L1-L2 Regime Alignment Review",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            "",
            "Main finding:",
            main_finding_text(result),
            "",
            "Symbols:",
            format_symbol_table(result.alignments),
            "",
            "Global findings:",
            *([f"- {finding}" for finding in result.global_findings] if result.global_findings else ["- none"]),
            "",
            "Recommended next stage:",
            result.recommended_next_stage or RECOMMENDED_NEXT_STAGE,
            "",
            "Output files:",
            result.output_json or config.output_json.as_posix(),
            result.output_md or config.output_md.as_posix(),
        ]
        if config.show_details:
            lines.extend(["", "Details:"])
            for alignment in result.alignments:
                lines.append(
                    f"- {alignment.symbol}: findings={_join_or_none(alignment.findings)}; "
                    f"L2 reasons={_join_or_none(alignment.l2_context_reason_codes)}; "
                    f"main_reason={alignment.l2_main_reason or 'N/A'}"
                )
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_regime_alignment_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_source_contracts(
    config: RegimeAlignmentReviewConfig,
    quality_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    if quality_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("Quality review JSON service must be BOOK_L1_MARKET_READER.")
    if quality_payload.get("report_type") != "market_reader_15m_quality_review":
        errors.append("Quality review JSON report_type must be market_reader_15m_quality_review.")
    if _nested_dict(quality_payload, "request").get("interval") != config.interval:
        errors.append("Quality review JSON interval does not match review interval.")
    if l1_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match review interval.")
    if l2_payload.get("service") != "BOOK_L2_MARKET_INTERPRETER":
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if not _list_of_dicts(quality_payload.get("symbols")):
        errors.append("Quality review JSON must contain symbols.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    if not isinstance(_nested_dict(l2_payload, "result").get("market_brief"), dict):
        errors.append("L2 context JSON must contain result.market_brief.")
    return tuple(errors)


def validate_fail_closed_safety(
    quality_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    for source_name, payload in (("quality review", quality_payload), ("L1", l1_payload), ("L2", l2_payload)):
        safety = _dict(payload.get("safety"))
        if not safety:
            errors.append(f"{source_name} safety must be an object.")
            continue
        signal_value = safety.get("trading_signal", safety.get("trade_signal"))
        if signal_value != "NOT_EVALUATED":
            errors.append(f"{source_name} safety signal must be NOT_EVALUATED.")
        for field_name in CRITICAL_FALSE_FIELDS:
            if field_name in safety and safety[field_name] is not False:
                errors.append(f"{source_name} safety.{field_name} must be false.")
    return tuple(errors)


def build_symbol_alignment(
    symbol: str,
    *,
    quality_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> SymbolRegimeAlignment:
    quality_row = find_symbol_row(_list_of_dicts(quality_payload.get("symbols")), symbol)
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    l1_current = extract_current_window(l1_row)

    l1_regime = _text(quality_row.get("market_regime") if quality_row else None) or _text(l1_current.get("market_regime"))
    l1_confidence = _optional_float(quality_row.get("confidence") if quality_row else None)
    if l1_confidence is None:
        l1_confidence = _optional_float(l1_current.get("confidence"))
    l1_reason_codes = tuple(str(item) for item in _list(quality_row.get("l1_reason_codes") if quality_row else None))
    if not l1_reason_codes:
        l1_reason_codes = tuple(str(item) for item in _list(l1_current.get("reason_codes")))

    l2_main_reason = extract_l2_main_reason(l2_payload, symbol) or _text(l2_row.get("observe_reason") if l2_row else None)
    findings = classify_symbol_findings(
        l1_regime=l1_regime,
        l1_confidence=l1_confidence,
        l2_row=l2_row,
        l2_main_reason=l2_main_reason,
    )
    status = "WARNING" if findings else "PASS"
    return SymbolRegimeAlignment(
        symbol=symbol,
        l1_regime=l1_regime,
        l1_confidence=l1_confidence,
        l1_reason_codes=l1_reason_codes,
        l1_directional_bias=_text(quality_row.get("directional_bias") if quality_row else None)
        or _text(l1_current.get("directional_bias")),
        l1_trend_strength=_text(quality_row.get("trend_strength") if quality_row else None)
        or _text(l1_current.get("trend_strength")),
        l1_timeline_stability=_text(quality_row.get("stability") if quality_row else None)
        or _text(l1_row.get("stability") if l1_row else None),
        l1_last_transition=_text(quality_row.get("last_transition") if quality_row else None)
        or _text(l1_row.get("last_transition") if l1_row else None),
        l2_received_regime=_text(l2_row.get("current_regime") if l2_row else None),
        l2_received_confidence=_optional_float(l2_row.get("current_confidence") if l2_row else None),
        l2_overall_state=extract_l2_overall_state(l2_payload),
        l2_bucket=_text(l2_row.get("bucket") if l2_row else None),
        l2_skip_candidate=_optional_bool(l2_row.get("skip_candidate") if l2_row else None),
        l2_quality_score=_optional_float(l2_row.get("context_quality_score") if l2_row else None),
        l2_quality_grade=_text(l2_row.get("context_quality_grade") if l2_row else None),
        l2_main_reason=l2_main_reason,
        l2_context_reason_codes=tuple(str(item) for item in _list(l2_row.get("context_reason_codes") if l2_row else None)),
        l2_context_quality_reason_codes=tuple(
            str(item) for item in _list(l2_row.get("context_quality_reason_codes") if l2_row else None)
        ),
        alignment_status=status,
        findings=findings,
        interpretation=build_symbol_interpretation(findings, l1_regime=l1_regime, l2_bucket=_text(l2_row.get("bucket") if l2_row else None)),
        recommended_next_focus=build_recommended_next_focus(findings),
    )


def classify_symbol_findings(
    *,
    l1_regime: str | None,
    l1_confidence: float | None,
    l2_row: dict[str, Any] | None,
    l2_main_reason: str | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    l2_regime = _text(l2_row.get("current_regime") if l2_row else None)
    l2_confidence = _optional_float(l2_row.get("current_confidence") if l2_row else None)
    l2_bucket = _token(l2_row.get("bucket") if l2_row else None, "")
    l2_skip = _optional_bool(l2_row.get("skip_candidate") if l2_row else None)
    l2_grade = _token(l2_row.get("context_quality_grade") if l2_row else None, "")
    l2_score = _optional_float(l2_row.get("context_quality_score") if l2_row else None)
    l2_reason_codes = tuple(str(item) for item in _list(l2_row.get("context_reason_codes") if l2_row else None))

    if not l1_regime:
        findings.append(L1_TO_L2_REGIME_FIELD_MISSING)
    if l1_confidence is None:
        findings.append(L1_TO_L2_CONFIDENCE_FIELD_MISSING)
    if not l2_regime:
        findings.append(L1_TO_L2_REGIME_FIELD_MISSING)
    elif l1_regime and l2_regime != l1_regime:
        findings.append(L1_TO_L2_REGIME_MISMATCH)
        findings.append(FIELD_MAPPING_NEEDS_REVIEW)
    if l2_confidence is None:
        findings.append(L1_TO_L2_CONFIDENCE_FIELD_MISSING)
    if not l2_reason_codes:
        findings.append(L2_CONTEXT_REASON_CODES_MISSING)
    if not l2_main_reason:
        findings.append(L2_MAIN_REASON_MISSING)

    if l1_regime == "FLAT" and l1_confidence is not None and l1_confidence >= HIGH_CONFIDENCE_THRESHOLD:
        if l2_bucket == "UNKNOWN" and l2_skip is True:
            findings.append(L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP)
            findings.append(L2_SKIPS_FLAT_CONTEXT)
            findings.append(L2_FLAT_CONTEXT_NOT_OBSERVABLE)
            findings.append(CONTRACT_ALIGNMENT_NEEDS_REVIEW)
        elif l2_skip is True:
            findings.append(L2_SKIPS_FLAT_CONTEXT)
        if l2_grade == "SKIP" or (l2_score is not None and l2_score < 0.25):
            findings.append(L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE)
    if l1_regime == "UNKNOWN" and l2_skip is True:
        findings.append(L1_UNKNOWN_PROPAGATED_TO_L2_SKIP)
    return tuple(dict.fromkeys(findings))


def classify_global_findings(
    *,
    alignments: tuple[SymbolRegimeAlignment, ...],
    l2_payload: dict[str, Any],
    overall_state: str | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    high_conf_flat = tuple(
        alignment
        for alignment in alignments
        if alignment.l1_regime == "FLAT"
        and alignment.l1_confidence is not None
        and alignment.l1_confidence >= HIGH_CONFIDENCE_THRESHOLD
    )
    if overall_state == "UNKNOWN" and high_conf_flat:
        findings.append(L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS)
    if any(L2_SKIPS_FLAT_CONTEXT in alignment.findings for alignment in alignments):
        findings.append(L2_SKIPS_FLAT_CONTEXT)
    if alignments and all(alignment.l2_skip_candidate is True for alignment in alignments):
        findings.append(ALL_SYMBOLS_SKIPPED)
    if not extract_candidate_symbols(l2_payload, "observation_candidates"):
        findings.append(NO_OBSERVATION_CANDIDATES)
    if any(CONTRACT_ALIGNMENT_NEEDS_REVIEW in alignment.findings for alignment in alignments):
        findings.append(CONTRACT_ALIGNMENT_NEEDS_REVIEW)
    if any(FIELD_MAPPING_NEEDS_REVIEW in alignment.findings for alignment in alignments):
        findings.append(FIELD_MAPPING_NEEDS_REVIEW)
    return tuple(dict.fromkeys(findings))


def build_symbol_interpretation(findings: tuple[str, ...], *, l1_regime: str | None, l2_bucket: str | None) -> str:
    if L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP in findings:
        return "L1 classifies the symbol as high-confidence FLAT, but L2 keeps the symbol in UNKNOWN/SKIP context."
    if L1_UNKNOWN_PROPAGATED_TO_L2_SKIP in findings:
        return "L1 UNKNOWN is propagated to L2 skip context."
    if findings:
        return f"L1 regime {l1_regime or 'N/A'} maps to L2 bucket {l2_bucket or 'N/A'} with alignment findings."
    return f"L1 regime {l1_regime or 'N/A'} maps to L2 bucket {l2_bucket or 'N/A'} without alignment warnings."


def build_recommended_next_focus(findings: tuple[str, ...]) -> tuple[str, ...]:
    focus: list[str] = []
    if L2_SKIPS_FLAT_CONTEXT in findings or L2_FLAT_CONTEXT_NOT_OBSERVABLE in findings:
        focus.append("inspect L2 flat-context handling")
        focus.append("decide whether high-confidence FLAT can be observe-only context")
    if FIELD_MAPPING_NEEDS_REVIEW in findings or CONTRACT_ALIGNMENT_NEEDS_REVIEW in findings:
        focus.append("inspect L1-to-L2 contract mapping for market_regime/confidence")
    if L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE in findings:
        focus.append("inspect L2 quality scoring for high-confidence FLAT")
    if L1_UNKNOWN_PROPAGATED_TO_L2_SKIP in findings:
        focus.append("confirm UNKNOWN propagation remains expected")
    if not focus:
        focus.append("continue monitoring L1-L2 regime alignment")
    return tuple(dict.fromkeys(focus))


def build_json_payload(config: RegimeAlignmentReviewConfig, result: RegimeAlignmentReviewResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "request": {"symbols": list(config.symbols), "interval": config.interval},
        "source_artifacts": source_artifacts(config),
        "overall": {
            "l2_overall_state": result.overall_state,
            "global_findings": list(result.global_findings),
        },
        "symbols": [symbol_alignment_to_dict(alignment) for alignment in result.alignments],
        "recommended_next_stage": result.recommended_next_stage,
        "safety": result.safety,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def write_regime_alignment_review_json(config: RegimeAlignmentReviewConfig, result: RegimeAlignmentReviewResult) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_regime_alignment_review_markdown(config: RegimeAlignmentReviewConfig, result: RegimeAlignmentReviewResult) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def build_markdown(config: RegimeAlignmentReviewConfig, result: RegimeAlignmentReviewResult) -> str:
    lines = [
        "# BOOK-L1-27 - L1-L2 Regime Alignment Review",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage reviews whether BOOK-L2 preserves and explains BOOK-L1 regimes correctly.",
        "",
        "It does not change L1 or L2 logic.",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Interval | {_md(config.interval)} |",
        "",
        "## Source Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        f"| Quality review JSON | {_md(config.quality_review_json.as_posix())} |",
        f"| L1 timeline JSON | {_md(config.l1_timeline_json.as_posix())} |",
        f"| L2 context JSON | {_md(config.l2_context_json.as_posix())} |",
        "",
        "## Main Finding",
        "",
        main_finding_text(result),
        "",
        "## Overall Alignment",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| L2 overall state | {_md(result.overall_state or 'N/A')} |",
        f"| Global findings | {_md(_join_or_none(result.global_findings))} |",
        "",
        "## Per-Symbol Alignment",
        "",
        "| Symbol | L1 Regime | L1 Confidence | L2 Bucket | L2 Skip | Alignment Status | Main Findings |",
        "|---|---|---:|---|---|---|---|",
        *[symbol_markdown_row(alignment) for alignment in result.alignments],
        "",
        "## Symbol Details",
        "",
    ]
    for alignment in result.alignments:
        lines.extend(symbol_detail_lines(alignment))
    lines.extend(
        [
            "## What This Means",
            "",
            what_this_means(result),
            "",
            "## Safety",
            "",
            "- read_only: `true`",
            "- market_logic_changed: `false`",
            "- l2_rules_changed: `false`",
            "- trading_signal: `NOT_EVALUATED`",
            "- safe_for_runtime_trading: `false`",
            "- live_trading_connected: `false`",
            "",
            "## Recommended Next Stage",
            "",
            f"`{result.recommended_next_stage or RECOMMENDED_NEXT_STAGE}`",
            "",
            "## Conclusion",
            "",
            "Do not move to BOOK-L3, edge validation, interval expansion, or runtime execution yet.",
            "",
            "First, review the interpretation boundary between L1 FLAT and L2 context/skip behavior.",
            "",
        ]
    )
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def symbol_markdown_row(alignment: SymbolRegimeAlignment) -> str:
    return (
        f"| {_md(alignment.symbol)} | {_md(alignment.l1_regime or 'N/A')} | {_confidence_text(alignment.l1_confidence)} | "
        f"{_md(alignment.l2_bucket or 'N/A')} | {_format_value(alignment.l2_skip_candidate)} | "
        f"{_md(alignment.alignment_status)} | {_md(_join_or_none(alignment.findings))} |"
    )


def symbol_detail_lines(alignment: SymbolRegimeAlignment) -> list[str]:
    return [
        f"### {_md(alignment.symbol)}",
        "",
        "#### L1",
        "",
        f"- Regime: `{_md(alignment.l1_regime or 'N/A')}`",
        f"- Confidence: `{_confidence_text(alignment.l1_confidence)}`",
        f"- Directional bias: `{_md(alignment.l1_directional_bias or 'N/A')}`",
        f"- Trend strength: `{_md(alignment.l1_trend_strength or 'N/A')}`",
        f"- Timeline stability: `{_md(alignment.l1_timeline_stability or 'N/A')}`",
        f"- Last transition: `{_md(alignment.l1_last_transition or 'N/A')}`",
        "- Reason codes:",
        *([f"  - {_md(code)}" for code in alignment.l1_reason_codes] if alignment.l1_reason_codes else ["  - none"]),
        "",
        "#### L2",
        "",
        f"- Received regime: `{_md(alignment.l2_received_regime or 'N/A')}`",
        f"- Received confidence: `{_confidence_text(alignment.l2_received_confidence)}`",
        f"- Overall state: `{_md(alignment.l2_overall_state or 'N/A')}`",
        f"- Bucket: `{_md(alignment.l2_bucket or 'N/A')}`",
        f"- Skip candidate: `{_format_value(alignment.l2_skip_candidate)}`",
        f"- Quality score: `{_score_text(alignment.l2_quality_score)}`",
        f"- Quality grade: `{_md(alignment.l2_quality_grade or 'N/A')}`",
        f"- Main reason: {_md(alignment.l2_main_reason or 'N/A')}",
        "- Context reason codes:",
        *(
            [f"  - {_md(code)}" for code in alignment.l2_context_reason_codes]
            if alignment.l2_context_reason_codes
            else ["  - none"]
        ),
        "- Quality reason codes:",
        *(
            [f"  - {_md(code)}" for code in alignment.l2_context_quality_reason_codes]
            if alignment.l2_context_quality_reason_codes
            else ["  - none"]
        ),
        "",
        "#### Alignment interpretation",
        "",
        alignment.interpretation or "No interpretation available.",
        "",
        "#### Recommended next focus",
        "",
        *[f"- {_md(focus)}" for focus in alignment.recommended_next_focus],
        "",
    ]


def format_symbol_table(alignments: tuple[SymbolRegimeAlignment, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "L2 Bucket", "L2 Skip", "Alignment Status")
    rows = tuple(
        (
            alignment.symbol,
            alignment.l1_regime or "N/A",
            _confidence_text(alignment.l1_confidence),
            alignment.l2_bucket or "N/A",
            _format_value(alignment.l2_skip_candidate),
            alignment.alignment_status,
        )
        for alignment in alignments
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


def main_finding_text(result: RegimeAlignmentReviewResult) -> str:
    high_conf_flat_symbols = tuple(
        alignment.symbol
        for alignment in result.alignments
        if L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP in alignment.findings
    )
    if high_conf_flat_symbols:
        return (
            "High-confidence L1 FLAT becomes L2 UNKNOWN/SKIP for "
            f"{', '.join(high_conf_flat_symbols)}."
        )
    if result.status == FAIL:
        return "The alignment review could not be completed from the available artifacts."
    return "No high-confidence L1 regime is unexplained by L2 in the reviewed artifacts."


def what_this_means(result: RegimeAlignmentReviewResult) -> str:
    if result.status == FAIL:
        return "The review did not have enough valid evidence to explain L1-L2 alignment."
    if any(L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP in alignment.findings for alignment in result.alignments):
        return (
            "The pipeline is technically stable, but high-confidence L1 FLAT currently becomes "
            "L2 UNKNOWN/SKIP. This is an alignment/interpretation issue."
        )
    return "The current L1-L2 regime mapping is explained by the reviewed evidence."


def build_review_safety_payload(*payloads: dict[str, Any]) -> dict[str, Any]:
    safety = {
        "read_only": True,
        "market_logic_changed": False,
        "l2_rules_changed": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
    }
    for payload in payloads:
        source_safety = _dict(payload.get("safety"))
        for field_name in (
            "trade_signal",
            "orders_enabled",
            "traders_core_connected",
            "approved_for_live_trading",
            "approved_for_auto_activation",
            "model_training_executed",
            "binance_download_executed",
        ):
            if field_name in source_safety:
                safety[field_name] = source_safety[field_name]
    return safety


def source_artifacts(config: RegimeAlignmentReviewConfig) -> dict[str, str]:
    return {
        "quality_review_json": config.quality_review_json.as_posix(),
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
    }


def symbol_alignment_to_dict(alignment: SymbolRegimeAlignment) -> dict[str, Any]:
    payload = asdict(alignment)
    for key in (
        "l1_reason_codes",
        "l2_context_reason_codes",
        "l2_context_quality_reason_codes",
        "findings",
        "recommended_next_focus",
    ):
        payload[key] = list(payload[key])
    return payload


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


def _extract_current_regime(row: dict[str, Any]) -> str:
    regimes = _list(row.get("regimes"))
    if regimes:
        return _token(regimes[-1], "UNKNOWN")
    return _token(row.get("current_regime"), "UNKNOWN")


def _has_critical_contract_finding(alignment: SymbolRegimeAlignment) -> bool:
    critical = {
        L1_TO_L2_REGIME_FIELD_MISSING,
        L1_TO_L2_CONFIDENCE_FIELD_MISSING,
        L2_CONTEXT_REASON_CODES_MISSING,
        L2_MAIN_REASON_MISSING,
    }
    return bool(critical.intersection(alignment.findings))


@dataclass(frozen=True)
class JsonReadResult:
    value: Any = None
    error: str | None = None


def read_json(path: Path, *, missing_hint: str) -> JsonReadResult:
    if not path.is_file():
        return JsonReadResult(error=f"Required artifact is missing: {path.as_posix()}. {missing_hint}")
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
    "PASS_WITH_ALIGNMENT_WARNINGS",
    "L1_FLAT_HIGH_CONFIDENCE_BUT_L2_UNKNOWN_SKIP",
    "L1_UNKNOWN_PROPAGATED_TO_L2_SKIP",
    "L2_OVERALL_UNKNOWN_DESPITE_L1_FLAT_SYMBOLS",
    "L2_SKIPS_FLAT_CONTEXT",
    "L2_FLAT_CONTEXT_NOT_OBSERVABLE",
    "L2_QUALITY_LOW_DESPITE_L1_CONFIDENCE",
    "L1_TO_L2_REGIME_FIELD_MISSING",
    "L1_TO_L2_CONFIDENCE_FIELD_MISSING",
    "L2_CONTEXT_REASON_CODES_MISSING",
    "L2_MAIN_REASON_MISSING",
    "FIELD_MAPPING_NEEDS_REVIEW",
    "CONTRACT_ALIGNMENT_NEEDS_REVIEW",
    "RegimeAlignmentReviewConfig",
    "RegimeAlignmentReviewFormatter",
    "RegimeAlignmentReviewResult",
    "RegimeAlignmentReviewRunner",
    "SymbolRegimeAlignment",
    "build_json_payload",
    "build_markdown",
    "parse_regime_alignment_symbols",
    "write_regime_alignment_review_json",
    "write_regime_alignment_review_markdown",
]
