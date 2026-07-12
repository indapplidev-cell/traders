from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_ALIGNMENT_REVIEW_JSON = Path("reports/book_l1/l1_l2_regime_alignment_review.json")
DEFAULT_QUALITY_REVIEW_JSON = Path("reports/book_l1/market_reader_15m_quality_review.json")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_l1/flat_context_alignment_diagnostic.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l1/flat_context_alignment_diagnostic.md")

SERVICE_NAME = "BOOK_L1_MARKET_READER"
REPORT_TYPE = "flat_context_alignment_diagnostic"
CONTRACT_VERSION = "book_l1_flat_context_alignment_diagnostic_v1"

PASS = "PASS"
PASS_WITH_FLAT_ALIGNMENT_WARNINGS = "PASS_WITH_FLAT_ALIGNMENT_WARNINGS"
FAIL = "FAIL"

DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.80
RECOMMENDED_OPTION = "OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE"
RECOMMENDED_NEXT_STAGE = "BOOK-L2-08 - FLAT Context Handling Proposal"

HIGH_CONFIDENCE_FLAT_PRESENT = "HIGH_CONFIDENCE_FLAT_PRESENT"
FLAT_RECEIVED_BY_L2 = "FLAT_RECEIVED_BY_L2"
FLAT_MAPPED_TO_UNKNOWN_BUCKET = "FLAT_MAPPED_TO_UNKNOWN_BUCKET"
FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT = "FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT"
FLAT_CONTEXT_SEMANTIC_GAP = "FLAT_CONTEXT_SEMANTIC_GAP"
FLAT_CAN_BE_VALID_OBSERVE_ONLY_CONTEXT = "FLAT_CAN_BE_VALID_OBSERVE_ONLY_CONTEXT"
FLAT_SHOULD_NOT_BE_TRADING_SIGNAL = "FLAT_SHOULD_NOT_BE_TRADING_SIGNAL"
UNKNOWN_AND_FLAT_ARE_CONFLATED = "UNKNOWN_AND_FLAT_ARE_CONFLATED"
L2_BUCKET_MAPPING_NEEDS_REVIEW = "L2_BUCKET_MAPPING_NEEDS_REVIEW"
L2_SKIP_REASON_NEEDS_DETAIL = "L2_SKIP_REASON_NEEDS_DETAIL"
CONTRACT_UPDATE_CANDIDATE = "CONTRACT_UPDATE_CANDIDATE"

CRITICAL_FALSE_FIELDS = (
    "safe_for_runtime_trading",
    "live_trading_connected",
    "orders_enabled",
    "traders_core_connected",
    "approved_for_live_trading",
    "approved_for_auto_activation",
)


@dataclass(frozen=True)
class FlatContextAlignmentConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    alignment_review_json: Path = DEFAULT_ALIGNMENT_REVIEW_JSON
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
        object.__setattr__(self, "high_confidence_threshold", float(self.high_confidence_threshold))
        object.__setattr__(self, "alignment_review_json", Path(self.alignment_review_json))
        object.__setattr__(self, "quality_review_json", Path(self.quality_review_json))
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class FlatContextCase:
    symbol: str
    l1_regime: str | None
    l1_confidence: float | None
    l2_bucket: str | None
    l2_skip_candidate: bool | None
    l2_quality_grade: str | None = None
    l2_main_reason: str | None = None
    l2_received_regime: str | None = None
    l2_context_reason_codes: tuple[str, ...] = ()
    l2_context_quality_reason_codes: tuple[str, ...] = ()
    is_high_confidence_flat: bool = False
    current_behavior: str = "UNKNOWN"
    expected_semantic_options: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()
    recommendation: str | None = None


@dataclass(frozen=True)
class FlatContextAlignmentResult:
    status: str
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    cases: tuple[FlatContextCase, ...] = ()
    global_findings: tuple[str, ...] = ()
    recommended_option: str | None = None
    recommended_next_stage: str | None = None
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    safety: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_FLAT_ALIGNMENT_WARNINGS}


class FlatContextAlignmentRunner:
    def run(self, config: FlatContextAlignmentConfig | None = None) -> FlatContextAlignmentResult:
        active_config = config or FlatContextAlignmentConfig()
        errors: list[str] = []
        warnings: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            result = FlatContextAlignmentResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                recommended_option=RECOMMENDED_OPTION,
                recommended_next_stage=RECOMMENDED_NEXT_STAGE,
                errors=(
                    f"BOOK-L1-28 reviews only 15m FLAT context alignment; requested interval was {active_config.interval}.",
                ),
                safety=build_review_safety_payload(),
            )
            self._write_outputs(active_config, result)
            return result

        alignment_read = read_json(
            active_config.alignment_review_json,
            missing_hint="Run book-l1-l2-regime-alignment-review first.",
        )
        quality_read = read_json(
            active_config.quality_review_json,
            missing_hint="Run book-l1-15m-quality-review first.",
        )
        l1_read = read_json(active_config.l1_timeline_json, missing_hint="Run book-l1-timeline-preview export first.")
        l2_read = read_json(active_config.l2_context_json, missing_hint="Run book-l2-timeline-context export first.")
        for read_result in (alignment_read, quality_read, l1_read, l2_read):
            if read_result.error:
                errors.append(read_result.error)

        if errors:
            result = FlatContextAlignmentResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                recommended_option=RECOMMENDED_OPTION,
                recommended_next_stage=RECOMMENDED_NEXT_STAGE,
                warnings=tuple(dict.fromkeys(warnings)),
                errors=tuple(dict.fromkeys(errors)),
                safety=build_review_safety_payload(
                    _dict(alignment_read.value),
                    _dict(quality_read.value),
                    _dict(l1_read.value),
                    _dict(l2_read.value),
                ),
            )
            self._write_outputs(active_config, result)
            return result

        alignment_payload = _dict(alignment_read.value)
        quality_payload = _dict(quality_read.value)
        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)

        errors.extend(validate_source_contracts(active_config, alignment_payload, quality_payload, l1_payload, l2_payload))
        errors.extend(validate_fail_closed_safety(alignment_payload, quality_payload, l1_payload, l2_payload))

        cases = tuple(
            build_flat_context_case(
                symbol,
                threshold=active_config.high_confidence_threshold,
                alignment_payload=alignment_payload,
                quality_payload=quality_payload,
                l1_payload=l1_payload,
                l2_payload=l2_payload,
            )
            for symbol in active_config.symbols
        )
        if not any(case.l1_regime or case.l2_bucket for case in cases):
            errors.append("Could not match requested symbols between L1 and L2 artifacts.")

        global_findings = classify_global_findings(cases)
        if errors:
            status = FAIL
        elif has_flat_alignment_warning(cases):
            status = PASS_WITH_FLAT_ALIGNMENT_WARNINGS
        else:
            status = PASS

        result = FlatContextAlignmentResult(
            status=status,
            interval=active_config.interval,
            high_confidence_threshold=active_config.high_confidence_threshold,
            cases=cases,
            global_findings=global_findings,
            recommended_option=RECOMMENDED_OPTION,
            recommended_next_stage=RECOMMENDED_NEXT_STAGE,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
            safety=build_review_safety_payload(alignment_payload, quality_payload, l1_payload, l2_payload),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(self, config: FlatContextAlignmentConfig, result: FlatContextAlignmentResult) -> None:
        try:
            json_path = write_flat_context_alignment_json(config, result)
            md_path = write_flat_context_alignment_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError:
            pass


class FlatContextAlignmentFormatter:
    def format(self, result: FlatContextAlignmentResult, *, config: FlatContextAlignmentConfig) -> str:
        lines = [
            "BOOK-L1-28 FLAT Context Alignment Diagnostic",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"High confidence threshold: {config.high_confidence_threshold:.2f}",
            "",
            "Main finding:",
            main_finding_text(result),
            "",
            "Cases:",
            format_case_table(result.cases),
            "",
            "Global findings:",
            *([f"- {finding}" for finding in result.global_findings] if result.global_findings else ["- none"]),
            "",
            "Recommended option:",
            result.recommended_option or RECOMMENDED_OPTION,
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
            for case in result.cases:
                lines.append(
                    f"- {case.symbol}: findings={_join_or_none(case.findings)}; "
                    f"L2 reasons={_join_or_none(case.l2_context_reason_codes)}; "
                    f"main_reason={case.l2_main_reason or 'N/A'}"
                )
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_flat_context_alignment_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_source_contracts(
    config: FlatContextAlignmentConfig,
    alignment_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    if alignment_payload.get("service") != SERVICE_NAME:
        errors.append("Alignment review JSON service must be BOOK_L1_MARKET_READER.")
    if alignment_payload.get("report_type") != "l1_l2_regime_alignment_review":
        errors.append("Alignment review JSON report_type must be l1_l2_regime_alignment_review.")
    if _nested_dict(alignment_payload, "request").get("interval") != config.interval:
        errors.append("Alignment review JSON interval does not match diagnostic interval.")
    if quality_payload.get("service") != SERVICE_NAME:
        errors.append("Quality review JSON service must be BOOK_L1_MARKET_READER.")
    if quality_payload.get("report_type") != "market_reader_15m_quality_review":
        errors.append("Quality review JSON report_type must be market_reader_15m_quality_review.")
    if _nested_dict(quality_payload, "request").get("interval") != config.interval:
        errors.append("Quality review JSON interval does not match diagnostic interval.")
    if l1_payload.get("service") != SERVICE_NAME:
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match diagnostic interval.")
    if l2_payload.get("service") != "BOOK_L2_MARKET_INTERPRETER":
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if not _list_of_dicts(alignment_payload.get("symbols")):
        errors.append("Alignment review JSON must contain symbols.")
    if not _list_of_dicts(quality_payload.get("symbols")):
        errors.append("Quality review JSON must contain symbols.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    return tuple(errors)


def validate_fail_closed_safety(*payloads: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for source_name, payload in (
        ("alignment review", payloads[0] if len(payloads) > 0 else {}),
        ("quality review", payloads[1] if len(payloads) > 1 else {}),
        ("L1", payloads[2] if len(payloads) > 2 else {}),
        ("L2", payloads[3] if len(payloads) > 3 else {}),
    ):
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


def build_flat_context_case(
    symbol: str,
    *,
    threshold: float,
    alignment_payload: dict[str, Any],
    quality_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> FlatContextCase:
    alignment_row = find_symbol_row(_list_of_dicts(alignment_payload.get("symbols")), symbol)
    quality_row = find_symbol_row(_list_of_dicts(quality_payload.get("symbols")), symbol)
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    l1_current = extract_current_window(l1_row)

    l1_regime = (
        _text(alignment_row.get("l1_regime") if alignment_row else None)
        or _text(quality_row.get("market_regime") if quality_row else None)
        or _text(l1_current.get("market_regime"))
    )
    l1_confidence = _optional_float(alignment_row.get("l1_confidence") if alignment_row else None)
    if l1_confidence is None:
        l1_confidence = _optional_float(quality_row.get("confidence") if quality_row else None)
    if l1_confidence is None:
        l1_confidence = _optional_float(l1_current.get("confidence"))

    l2_bucket = _text(alignment_row.get("l2_bucket") if alignment_row else None) or _text(
        l2_row.get("bucket") if l2_row else None
    )
    l2_skip_candidate = _optional_bool(alignment_row.get("l2_skip_candidate") if alignment_row else None)
    if l2_skip_candidate is None:
        l2_skip_candidate = _optional_bool(l2_row.get("skip_candidate") if l2_row else None)
    l2_received_regime = _text(alignment_row.get("l2_received_regime") if alignment_row else None) or _text(
        l2_row.get("current_regime") if l2_row else None
    )
    l2_quality_grade = _text(alignment_row.get("l2_quality_grade") if alignment_row else None) or _text(
        l2_row.get("context_quality_grade") if l2_row else None
    )
    l2_main_reason = (
        _text(alignment_row.get("l2_main_reason") if alignment_row else None)
        or extract_l2_main_reason(l2_payload, symbol)
        or _text(l2_row.get("observe_reason") if l2_row else None)
    )
    l2_reason_codes = tuple(
        str(item)
        for item in _list(
            (alignment_row.get("l2_context_reason_codes") if alignment_row else None)
            or (l2_row.get("context_reason_codes") if l2_row else None)
        )
    )
    l2_quality_reason_codes = tuple(
        str(item)
        for item in _list(
            (alignment_row.get("l2_context_quality_reason_codes") if alignment_row else None)
            or (l2_row.get("context_quality_reason_codes") if l2_row else None)
        )
    )

    is_high_confidence_flat = l1_regime == "FLAT" and l1_confidence is not None and l1_confidence >= threshold
    findings = classify_case_findings(
        l1_regime=l1_regime,
        is_high_confidence_flat=is_high_confidence_flat,
        l2_received_regime=l2_received_regime,
        l2_bucket=l2_bucket,
        l2_skip_candidate=l2_skip_candidate,
        l2_main_reason=l2_main_reason,
    )
    return FlatContextCase(
        symbol=symbol,
        l1_regime=l1_regime,
        l1_confidence=l1_confidence,
        l2_bucket=l2_bucket,
        l2_skip_candidate=l2_skip_candidate,
        l2_quality_grade=l2_quality_grade,
        l2_main_reason=l2_main_reason,
        l2_received_regime=l2_received_regime,
        l2_context_reason_codes=l2_reason_codes,
        l2_context_quality_reason_codes=l2_quality_reason_codes,
        is_high_confidence_flat=is_high_confidence_flat,
        current_behavior=current_behavior_text(
            is_high_confidence_flat=is_high_confidence_flat,
            l2_received_regime=l2_received_regime,
            l2_bucket=l2_bucket,
            l2_skip_candidate=l2_skip_candidate,
        ),
        expected_semantic_options=expected_semantic_options(is_high_confidence_flat),
        findings=findings,
        recommendation=recommendation_text(findings),
    )


def classify_case_findings(
    *,
    l1_regime: str | None,
    is_high_confidence_flat: bool,
    l2_received_regime: str | None,
    l2_bucket: str | None,
    l2_skip_candidate: bool | None,
    l2_main_reason: str | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    bucket = _token(l2_bucket, "")
    main_reason = str(l2_main_reason or "").upper()
    if is_high_confidence_flat:
        findings.append(HIGH_CONFIDENCE_FLAT_PRESENT)
        findings.append(FLAT_CAN_BE_VALID_OBSERVE_ONLY_CONTEXT)
        findings.append(FLAT_SHOULD_NOT_BE_TRADING_SIGNAL)
        if l2_received_regime == "FLAT":
            findings.append(FLAT_RECEIVED_BY_L2)
        if bucket == "UNKNOWN":
            findings.append(FLAT_MAPPED_TO_UNKNOWN_BUCKET)
            findings.append(L2_BUCKET_MAPPING_NEEDS_REVIEW)
            findings.append(UNKNOWN_AND_FLAT_ARE_CONFLATED)
        if l2_skip_candidate is True and "FLAT" not in main_reason:
            findings.append(FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT)
            findings.append(L2_SKIP_REASON_NEEDS_DETAIL)
        if FLAT_MAPPED_TO_UNKNOWN_BUCKET in findings or FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT in findings:
            findings.append(FLAT_CONTEXT_SEMANTIC_GAP)
            findings.append(CONTRACT_UPDATE_CANDIDATE)
    elif l1_regime == "FLAT":
        findings.append(FLAT_SHOULD_NOT_BE_TRADING_SIGNAL)
    return tuple(dict.fromkeys(findings))


def classify_global_findings(cases: tuple[FlatContextCase, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    ordered_categories = (
        HIGH_CONFIDENCE_FLAT_PRESENT,
        FLAT_RECEIVED_BY_L2,
        FLAT_MAPPED_TO_UNKNOWN_BUCKET,
        FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT,
        FLAT_CONTEXT_SEMANTIC_GAP,
        FLAT_CAN_BE_VALID_OBSERVE_ONLY_CONTEXT,
        FLAT_SHOULD_NOT_BE_TRADING_SIGNAL,
        UNKNOWN_AND_FLAT_ARE_CONFLATED,
        L2_BUCKET_MAPPING_NEEDS_REVIEW,
        L2_SKIP_REASON_NEEDS_DETAIL,
        CONTRACT_UPDATE_CANDIDATE,
    )
    for category in ordered_categories:
        if any(category in case.findings for case in cases):
            findings.append(category)
    return tuple(findings)


def has_flat_alignment_warning(cases: tuple[FlatContextCase, ...]) -> bool:
    warning_findings = {FLAT_MAPPED_TO_UNKNOWN_BUCKET, FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT, FLAT_CONTEXT_SEMANTIC_GAP}
    return any(bool(warning_findings.intersection(case.findings)) for case in cases)


def current_behavior_text(
    *,
    is_high_confidence_flat: bool,
    l2_received_regime: str | None,
    l2_bucket: str | None,
    l2_skip_candidate: bool | None,
) -> str:
    if is_high_confidence_flat and l2_received_regime == "FLAT" and l2_bucket == "UNKNOWN" and l2_skip_candidate is True:
        return "L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP."
    if is_high_confidence_flat and l2_received_regime == "FLAT":
        return "L1 FLAT is received by L2 and preserved outside UNKNOWN/SKIP."
    if is_high_confidence_flat:
        return "L1 FLAT is high confidence but L2 receipt is unclear."
    return "No high-confidence FLAT case for this symbol."


def expected_semantic_options(is_high_confidence_flat: bool) -> tuple[str, ...]:
    if not is_high_confidence_flat:
        return ()
    return (
        "FLAT as valid observe-only context",
        "FLAT as skip but preserved as FLAT context",
    )


def recommendation_text(findings: tuple[str, ...]) -> str:
    if FLAT_CONTEXT_SEMANTIC_GAP in findings:
        return "Do not change logic in this stage. Prepare FLAT context handling proposal."
    return "No BOOK-L1-28 rule change is approved."


def build_json_payload(config: FlatContextAlignmentConfig, result: FlatContextAlignmentResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "request": {
            "symbols": list(config.symbols),
            "interval": config.interval,
            "high_confidence_threshold": config.high_confidence_threshold,
        },
        "source_artifacts": source_artifacts(config),
        "global_findings": list(result.global_findings),
        "cases": [case_to_dict(case) for case in result.cases],
        "semantic_options": semantic_options_payload(),
        "recommended_option": result.recommended_option,
        "recommended_next_stage": result.recommended_next_stage,
        "safety": result.safety,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def write_flat_context_alignment_json(config: FlatContextAlignmentConfig, result: FlatContextAlignmentResult) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_flat_context_alignment_markdown(config: FlatContextAlignmentConfig, result: FlatContextAlignmentResult) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def build_markdown(config: FlatContextAlignmentConfig, result: FlatContextAlignmentResult) -> str:
    lines = [
        "# BOOK-L1-28 - FLAT Context Alignment Diagnostic",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage diagnoses how high-confidence L1 `FLAT` should be interpreted by BOOK-L2.",
        "",
        "It does not change L1 or L2 logic.",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Interval | {_md(config.interval)} |",
        f"| High confidence threshold | {config.high_confidence_threshold:.2f} |",
        "",
        "## Source Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        f"| Alignment review JSON | {_md(config.alignment_review_json.as_posix())} |",
        f"| Quality review JSON | {_md(config.quality_review_json.as_posix())} |",
        f"| L1 timeline JSON | {_md(config.l1_timeline_json.as_posix())} |",
        f"| L2 context JSON | {_md(config.l2_context_json.as_posix())} |",
        "",
        "## Main Finding",
        "",
        main_finding_text(result),
        "",
        "## FLAT Cases",
        "",
        "| Symbol | L1 Regime | Confidence | High Confidence FLAT | L2 Bucket | L2 Skip | Current Behavior |",
        "|---|---|---:|---|---|---|---|",
        *[case_markdown_row(case) for case in result.cases],
        "",
        "## Semantic Options Considered",
        "",
        "### Option A - FLAT is always skip",
        "",
        "High-confidence `FLAT` always remains a skip case.",
        "",
        "This is conservative, but L2 should still explain it as `FLAT/SKIP`, not `UNKNOWN/SKIP`.",
        "",
        "### Option B - FLAT is valid observe-only context",
        "",
        "High-confidence `FLAT` is a valid market context, without becoming an action signal.",
        "",
        "This preserves L1 meaning, but requires careful L2 bucket and reason-code handling.",
        "",
        "### Option C - FLAT is context but not observation candidate",
        "",
        "High-confidence `FLAT` is preserved as market context, but does not enter observation candidates.",
        "",
        "This is the recommended safe interpretation for the current project goal.",
        "",
        "### Option D - FLAT quality depends on reason codes",
        "",
        "`FLAT` becomes valid context only when reason codes show a readable range/flat structure.",
        "",
        "This is a useful follow-up after reason-code review.",
        "",
        "## Recommended Interpretation",
        "",
        f"`{result.recommended_option or RECOMMENDED_OPTION}`",
        "",
        "Meaning:",
        "",
        "High-confidence `FLAT` should not become `UNKNOWN`.",
        "",
        "It may remain non-observation / skip, but L2 should preserve and explain it as `FLAT` context.",
        "",
        "## Recommended Next Stage",
        "",
        f"`{result.recommended_next_stage or RECOMMENDED_NEXT_STAGE}`",
        "",
        "Purpose:",
        "",
        "Prepare a safe proposal for L2 to preserve high-confidence FLAT as observe-only context without creating action signals.",
        "",
        "## Not Approved In This Stage",
        "",
        "- L1 logic changes",
        "- L2 rule changes",
        "- Bucket behavior changes",
        "- Trading signals",
        "- Edge validation",
        "- Runtime execution",
        "- 1h/4h expansion",
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
        "## Conclusion",
        "",
        "The next work should propose how L2 handles high-confidence `FLAT`.",
        "",
        "Do not move to BOOK-L3, edge validation, runtime execution, or interval expansion yet.",
        "",
    ]
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def case_markdown_row(case: FlatContextCase) -> str:
    return (
        f"| {_md(case.symbol)} | {_md(case.l1_regime or 'N/A')} | {_confidence_text(case.l1_confidence)} | "
        f"{_format_value(case.is_high_confidence_flat)} | {_md(case.l2_bucket or 'N/A')} | "
        f"{_format_value(case.l2_skip_candidate)} | {_md(case.current_behavior)} |"
    )


def format_case_table(cases: tuple[FlatContextCase, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "High Confidence FLAT", "L2 Bucket", "L2 Skip")
    rows = tuple(
        (
            case.symbol,
            case.l1_regime or "N/A",
            _confidence_text(case.l1_confidence),
            _format_value(case.is_high_confidence_flat),
            case.l2_bucket or "N/A",
            _format_value(case.l2_skip_candidate),
        )
        for case in cases
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


def main_finding_text(result: FlatContextAlignmentResult) -> str:
    if result.status == FAIL:
        return "The FLAT context diagnostic could not be completed from the available artifacts."
    if has_flat_alignment_warning(result.cases):
        return "High-confidence L1 FLAT is received by L2 but mapped to UNKNOWN/SKIP."
    if any(case.is_high_confidence_flat for case in result.cases):
        return "High-confidence L1 FLAT is present and L2 preserves it outside UNKNOWN/SKIP."
    return "No high-confidence L1 FLAT cases are present in the reviewed artifacts."


def source_artifacts(config: FlatContextAlignmentConfig) -> dict[str, str]:
    return {
        "alignment_review_json": config.alignment_review_json.as_posix(),
        "quality_review_json": config.quality_review_json.as_posix(),
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
    }


def semantic_options_payload() -> list[dict[str, str]]:
    return [
        {
            "option_id": "OPTION_A_FLAT_ALWAYS_SKIP",
            "title": "FLAT is always skip",
            "recommendation": "not preferred unless L2 preserves FLAT explanation",
        },
        {
            "option_id": "OPTION_B_FLAT_VALID_OBSERVE_ONLY_CONTEXT",
            "title": "FLAT is valid observe-only context",
            "recommendation": "possible future direction",
        },
        {
            "option_id": "OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE",
            "title": "FLAT is context but not observation candidate",
            "recommendation": "recommended safe interpretation",
        },
        {
            "option_id": "OPTION_D_FLAT_QUALITY_DEPENDS_ON_REASON_CODES",
            "title": "FLAT quality depends on reason codes",
            "recommendation": "recommended after reason-code review",
        },
    ]


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


def case_to_dict(case: FlatContextCase) -> dict[str, Any]:
    payload = asdict(case)
    for key in (
        "l2_context_reason_codes",
        "l2_context_quality_reason_codes",
        "expected_semantic_options",
        "findings",
    ):
        payload[key] = list(payload[key])
    return payload


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
        "reason_codes": l1_row.get("reason_codes", []),
    }


def extract_l2_main_reason(l2_payload: dict[str, Any], symbol: str) -> str | None:
    brief = _dict(_nested_dict(l2_payload, "result").get("market_brief"))
    for key in ("observation_candidates", "skip_candidates"):
        candidate = find_symbol_row(_list_of_dicts(brief.get(key)), symbol)
        if candidate:
            return _text(candidate.get("main_reason"))
    return None


def _extract_current_regime(row: dict[str, Any]) -> str:
    regimes = _list(row.get("regimes"))
    if regimes:
        return _token(regimes[-1], "UNKNOWN")
    return _token(row.get("current_regime"), "UNKNOWN")


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
    "PASS_WITH_FLAT_ALIGNMENT_WARNINGS",
    "HIGH_CONFIDENCE_FLAT_PRESENT",
    "FLAT_RECEIVED_BY_L2",
    "FLAT_MAPPED_TO_UNKNOWN_BUCKET",
    "FLAT_SKIPPED_WITHOUT_FLAT_CONTEXT",
    "FLAT_CONTEXT_SEMANTIC_GAP",
    "FLAT_CAN_BE_VALID_OBSERVE_ONLY_CONTEXT",
    "FLAT_SHOULD_NOT_BE_TRADING_SIGNAL",
    "UNKNOWN_AND_FLAT_ARE_CONFLATED",
    "L2_BUCKET_MAPPING_NEEDS_REVIEW",
    "L2_SKIP_REASON_NEEDS_DETAIL",
    "CONTRACT_UPDATE_CANDIDATE",
    "RECOMMENDED_NEXT_STAGE",
    "RECOMMENDED_OPTION",
    "FlatContextAlignmentConfig",
    "FlatContextAlignmentFormatter",
    "FlatContextAlignmentResult",
    "FlatContextAlignmentRunner",
    "FlatContextCase",
    "build_json_payload",
    "build_markdown",
    "parse_flat_context_alignment_symbols",
    "write_flat_context_alignment_json",
    "write_flat_context_alignment_markdown",
]
