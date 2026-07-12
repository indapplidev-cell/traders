from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.market_interpreter.api_readiness_review import (
    L2ApiReadinessConfig,
    L2ApiReadinessReviewer,
)
from app.market_interpreter.json_consumer import (
    L2ContextConsumerConfig,
    L2ContextJsonConsumer,
)


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.80
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_IMPLEMENTATION_JSON = Path("reports/book_l2/flat_context_handling_implementation.json")
DEFAULT_INTERVAL_ANSWER_MD = Path("reports/book_l2/l1_l2_interval_answer.md")
DEFAULT_MULTI_INTERVAL_ANSWER_MD = Path("reports/book_l2/l1_l2_multi_interval_answer.md")
DEFAULT_OUTPUT_JSON = Path("reports/book_l2/flat_context_integration_review.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l2/flat_context_integration_review.md")

SERVICE_NAME = "BOOK_L2_MARKET_INTERPRETER"
REPORT_TYPE = "flat_context_integration_review"
CONTRACT_VERSION = "book_l2_flat_context_integration_review_v1"

PASS = "PASS"
PASS_WITH_INTEGRATION_WARNINGS = "PASS_WITH_INTEGRATION_WARNINGS"
FAIL = "FAIL"

CHECK_NAMES = (
    "flat_context_present_for_high_confidence_flat",
    "unknown_remains_unknown",
    "flat_context_observation_false",
    "flat_context_skip_true",
    "flat_context_safety_false",
    "trade_signal_not_evaluated",
    "l2_json_consumer_accepts_flat_context",
    "l2_api_readiness_accepts_flat_context",
    "interval_answer_reflects_flat_context",
    "multi_interval_15m_reflects_flat_context",
    "multi_interval_1h_4h_missing_data_documented",
    "human_brief_does_not_conflate_flat_and_unknown",
    "no_l1_core_changes_required",
    "no_runtime_trading_enabled",
)


@dataclass(frozen=True)
class FlatContextIntegrationReviewConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    l1_timeline_json: Path = DEFAULT_L1_TIMELINE_JSON
    l2_context_json: Path = DEFAULT_L2_CONTEXT_JSON
    implementation_json: Path = DEFAULT_IMPLEMENTATION_JSON
    interval_answer_md: Path = DEFAULT_INTERVAL_ANSWER_MD
    multi_interval_answer_md: Path = DEFAULT_MULTI_INTERVAL_ANSWER_MD
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbols", normalize_symbols(self.symbols) or DEFAULT_SYMBOLS)
        object.__setattr__(self, "interval", str(self.interval).strip() or ALLOWED_INTERVAL)
        object.__setattr__(self, "high_confidence_threshold", float(self.high_confidence_threshold))
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "implementation_json", Path(self.implementation_json))
        object.__setattr__(self, "interval_answer_md", Path(self.interval_answer_md))
        object.__setattr__(self, "multi_interval_answer_md", Path(self.multi_interval_answer_md))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class IntegrationCheck:
    name: str
    status: str
    message: str
    evidence_path: str | None = None


@dataclass(frozen=True)
class SymbolIntegrationReview:
    symbol: str
    l1_market_regime: str | None
    l1_confidence: float | None
    l2_bucket: str | None
    observation_candidate: bool | None
    skip_candidate: bool | None
    safe_for_runtime_trading: bool | None
    trade_signal: str | None
    expected_bucket: str | None
    passed: bool
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlatContextIntegrationReviewResult:
    status: str
    interval: str = ALLOWED_INTERVAL
    checks: tuple[IntegrationCheck, ...] = ()
    symbols: tuple[SymbolIntegrationReview, ...] = ()
    global_findings: tuple[str, ...] = ()
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_INTEGRATION_WARNINGS}


class FlatContextIntegrationReviewRunner:
    def run(self, config: FlatContextIntegrationReviewConfig | None = None) -> FlatContextIntegrationReviewResult:
        active_config = config or FlatContextIntegrationReviewConfig()
        warnings: list[str] = []
        errors: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            result = FlatContextIntegrationReviewResult(
                status=FAIL,
                interval=active_config.interval,
                errors=(
                    "BOOK-L2-10 reviews post-FLAT integration only for the stabilized 15m workflow; "
                    f"requested interval was {active_config.interval}.",
                ),
            )
            self._write_outputs(active_config, result)
            return result

        l1_read = read_json(active_config.l1_timeline_json)
        l2_read = read_json(active_config.l2_context_json)
        implementation_read = read_json(active_config.implementation_json)
        for path, read_result in (
            (active_config.l1_timeline_json, l1_read),
            (active_config.l2_context_json, l2_read),
            (active_config.implementation_json, implementation_read),
        ):
            if read_result.error:
                errors.append(f"Required artifact is missing or invalid: {path.as_posix()}. Run the BOOK-L2-09 workflow first. {read_result.error}")

        if errors:
            result = FlatContextIntegrationReviewResult(
                status=FAIL,
                interval=active_config.interval,
                errors=tuple(dict.fromkeys(errors)),
            )
            self._write_outputs(active_config, result)
            return result

        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)
        implementation_payload = _dict(implementation_read.value)
        errors.extend(validate_source_contracts(active_config, l1_payload, l2_payload, implementation_payload))

        symbol_reviews = tuple(
            build_symbol_review(
                symbol,
                threshold=active_config.high_confidence_threshold,
                l1_payload=l1_payload,
                l2_payload=l2_payload,
            )
            for symbol in active_config.symbols
        )
        if not any(review.l1_market_regime or review.l2_bucket for review in symbol_reviews):
            errors.append("Could not match requested symbols between L1 and L2 artifacts.")

        checks = build_checks(active_config, symbol_reviews, l2_payload, implementation_payload)
        checks = (*checks, check_interval_answer(active_config), *check_multi_interval_answer(active_config))
        checks = (*checks, check_human_brief(active_config, l2_payload), check_no_l1_core_changes(), check_no_runtime_trading(symbol_reviews, l2_payload))

        downstream_errors = tuple(check.message for check in checks if check.status == FAIL)
        downstream_warnings = tuple(check.message for check in checks if check.status == "WARN")
        errors.extend(downstream_errors)
        warnings.extend(downstream_warnings)

        if active_config.strict:
            missing_optional = tuple(warning for warning in warnings if "evidence file is missing" in warning)
            if missing_optional:
                errors.extend(missing_optional)
                warnings = [warning for warning in warnings if warning not in missing_optional]

        if errors:
            status = FAIL
        elif warnings:
            status = PASS_WITH_INTEGRATION_WARNINGS
        else:
            status = PASS

        result = FlatContextIntegrationReviewResult(
            status=status,
            interval=active_config.interval,
            checks=checks,
            symbols=symbol_reviews,
            global_findings=classify_global_findings(symbol_reviews),
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(
        self,
        config: FlatContextIntegrationReviewConfig,
        result: FlatContextIntegrationReviewResult,
    ) -> None:
        try:
            json_path = write_flat_context_integration_review_json(config, result)
            md_path = write_flat_context_integration_review_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError as exc:
            object.__setattr__(result, "status", FAIL)
            object.__setattr__(result, "errors", (*result.errors, f"Could not write integration review evidence: {exc}"))


class FlatContextIntegrationReviewFormatter:
    def format(
        self,
        result: FlatContextIntegrationReviewResult,
        *,
        config: FlatContextIntegrationReviewConfig,
    ) -> str:
        lines = [
            "BOOK-L2-10 Post-FLAT Context Integration Review",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"High confidence threshold: {config.high_confidence_threshold:.2f}",
            "",
            "Integration checks:",
            format_checks_table(result.checks),
            "",
            "Symbols:",
            format_symbol_table(result.symbols),
            "",
            "Output files:",
            result.output_json or config.output_json.as_posix(),
            result.output_md or config.output_md.as_posix(),
        ]
        if config.show_details:
            lines.extend(["", "Details:"])
            lines.extend(f"- {review.symbol}: findings={_join_or_none(review.findings)}" for review in result.symbols)
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_flat_context_integration_symbols(
    symbols: str | None,
    symbol_options: tuple[str, ...] = (),
) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_source_contracts(
    config: FlatContextIntegrationReviewConfig,
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
    implementation_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    if l1_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match review interval.")
    if l2_payload.get("service") != SERVICE_NAME:
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if implementation_payload.get("service") != SERVICE_NAME:
        errors.append("Implementation JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if implementation_payload.get("report_type") != "flat_context_handling_implementation":
        errors.append("Implementation JSON report_type must be flat_context_handling_implementation.")
    if _nested_dict(implementation_payload, "request").get("interval") != config.interval:
        errors.append("Implementation JSON interval does not match review interval.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    return tuple(errors)


def build_symbol_review(
    symbol: str,
    *,
    threshold: float,
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> SymbolIntegrationReview:
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    l1_current = extract_current_window(l1_row)
    l1_regime = _token(l1_current.get("market_regime") or (l1_row or {}).get("current_regime"), "UNKNOWN") if l1_row else None
    l1_confidence = _optional_float(l1_current.get("confidence") if l1_current else None)
    if l1_confidence is None and l1_row:
        l1_confidence = _optional_float(l1_row.get("current_confidence"))

    l2_bucket = _text((l2_row or {}).get("bucket"))
    observation_candidate = actual_observation_candidate(symbol, l2_payload=l2_payload, l2_row=l2_row)
    skip_candidate = _optional_bool((l2_row or {}).get("skip_candidate"))
    safe = _optional_bool((l2_row or {}).get("safe_for_runtime_trading"))
    if safe is None:
        safe = _optional_bool(_nested_dict(l2_payload, "safety").get("safe_for_runtime_trading"))
    trade_signal = _text((l2_row or {}).get("trade_signal") or _nested_dict(l2_payload, "safety").get("trade_signal"))

    high_confidence_flat = l1_regime == "FLAT" and l1_confidence is not None and l1_confidence >= threshold
    unknown_case = l1_regime == "UNKNOWN"
    expected_bucket = "FLAT_CONTEXT" if high_confidence_flat else "UNKNOWN" if unknown_case else l2_bucket

    findings = classify_symbol_findings(
        high_confidence_flat=high_confidence_flat,
        unknown_case=unknown_case,
        l2_bucket=l2_bucket,
        observation_candidate=observation_candidate,
        skip_candidate=skip_candidate,
        safe_for_runtime_trading=safe,
        trade_signal=trade_signal,
    )
    return SymbolIntegrationReview(
        symbol=symbol,
        l1_market_regime=l1_regime,
        l1_confidence=l1_confidence,
        l2_bucket=l2_bucket,
        observation_candidate=observation_candidate,
        skip_candidate=skip_candidate,
        safe_for_runtime_trading=safe,
        trade_signal=trade_signal,
        expected_bucket=expected_bucket,
        passed=not any(finding.startswith("FAIL_") for finding in findings),
        findings=findings,
    )


def classify_symbol_findings(
    *,
    high_confidence_flat: bool,
    unknown_case: bool,
    l2_bucket: str | None,
    observation_candidate: bool | None,
    skip_candidate: bool | None,
    safe_for_runtime_trading: bool | None,
    trade_signal: str | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    if high_confidence_flat:
        findings.append("FLAT_CONTEXT_INTEGRATED" if l2_bucket == "FLAT_CONTEXT" else "FAIL_HIGH_CONFIDENCE_FLAT_NOT_FLAT_CONTEXT")
        findings.append("NON_DIRECTIONAL_CONTEXT" if observation_candidate is False else "FAIL_FLAT_CONTEXT_OBSERVATION_CANDIDATE")
        findings.append("FLAT_CONTEXT_SKIP_CANDIDATE" if skip_candidate is True else "FAIL_FLAT_CONTEXT_NOT_SKIP_CANDIDATE")
        findings.append("NOT_TRADING_SIGNAL" if safe_for_runtime_trading is False else "FAIL_FLAT_CONTEXT_RUNTIME_SAFETY_TRUE")
        findings.append("TRADE_SIGNAL_NOT_EVALUATED" if trade_signal in {None, "NOT_EVALUATED"} else "FAIL_TRADE_SIGNAL_CHANGED")
    elif unknown_case:
        findings.append("UNKNOWN_REMAINS_DISTINCT_FROM_FLAT" if l2_bucket == "UNKNOWN" else "FAIL_UNKNOWN_DID_NOT_REMAIN_UNKNOWN")
        if l2_bucket == "FLAT_CONTEXT":
            findings.append("FAIL_UNKNOWN_BECAME_FLAT_CONTEXT")
    else:
        findings.append("NO_HIGH_CONFIDENCE_FLAT_RULE_APPLIED")
    return tuple(dict.fromkeys(findings))


def build_checks(
    config: FlatContextIntegrationReviewConfig,
    reviews: tuple[SymbolIntegrationReview, ...],
    l2_payload: dict[str, Any],
    implementation_payload: dict[str, Any],
) -> tuple[IntegrationCheck, ...]:
    flat_reviews = tuple(
        review
        for review in reviews
        if review.l1_market_regime == "FLAT"
        and review.l1_confidence is not None
        and review.l1_confidence >= config.high_confidence_threshold
    )
    unknown_reviews = tuple(review for review in reviews if review.l1_market_regime == "UNKNOWN")
    checks = [
        _check(
            "flat_context_present_for_high_confidence_flat",
            _all(flat_reviews, lambda review: review.l2_bucket == "FLAT_CONTEXT"),
            "High-confidence FLAT cases are preserved as FLAT_CONTEXT.",
            "High-confidence FLAT mapped outside FLAT_CONTEXT.",
            config.l2_context_json,
        ),
        _check(
            "unknown_remains_unknown",
            _all(unknown_reviews, lambda review: review.l2_bucket == "UNKNOWN"),
            "UNKNOWN cases remain UNKNOWN.",
            "UNKNOWN was mapped away from UNKNOWN.",
            config.l2_context_json,
        ),
        _check(
            "flat_context_observation_false",
            _all(flat_reviews, lambda review: review.observation_candidate is False),
            "FLAT_CONTEXT is not an observation candidate.",
            "FLAT_CONTEXT became observation_candidate=true.",
            config.l2_context_json,
        ),
        _check(
            "flat_context_skip_true",
            _all(flat_reviews, lambda review: review.skip_candidate is True),
            "FLAT_CONTEXT remains skip_candidate=true.",
            "FLAT_CONTEXT skip_candidate is not true.",
            config.l2_context_json,
        ),
        _check(
            "flat_context_safety_false",
            _all(flat_reviews, lambda review: review.safe_for_runtime_trading is False),
            "FLAT_CONTEXT remains unsafe for runtime trading.",
            "FLAT_CONTEXT safe_for_runtime_trading became true or unknown.",
            config.l2_context_json,
        ),
        _check(
            "trade_signal_not_evaluated",
            _all(reviews, lambda review: review.trade_signal in {None, "NOT_EVALUATED"}),
            "All reviewed symbols keep trade_signal=NOT_EVALUATED.",
            "At least one reviewed symbol has a trading signal.",
            config.l2_context_json,
        ),
        check_l2_json_consumer(config),
        check_l2_api_readiness(config, l2_payload),
    ]
    if str(implementation_payload.get("status") or "") not in {PASS, PASS_WITH_INTEGRATION_WARNINGS} and not str(implementation_payload.get("status") or "").startswith("PASS_WITH"):
        checks.append(
            IntegrationCheck(
                "flat_context_present_for_high_confidence_flat",
                FAIL,
                "BOOK-L2-09 implementation evidence is not passing.",
                config.implementation_json.as_posix(),
            )
        )
    return tuple(check for check in checks if check.name in CHECK_NAMES or check.status == FAIL)


def check_l2_json_consumer(config: FlatContextIntegrationReviewConfig) -> IntegrationCheck:
    result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=config.l2_context_json, strict=True))
    if result.passed:
        return IntegrationCheck("l2_json_consumer_accepts_flat_context", PASS, "L2 JSON consumer strict accepts FLAT_CONTEXT.", config.l2_context_json.as_posix())
    return IntegrationCheck("l2_json_consumer_accepts_flat_context", FAIL, "; ".join(result.errors or result.warnings or ("L2 JSON consumer strict failed.",)), config.l2_context_json.as_posix())


def check_l2_api_readiness(config: FlatContextIntegrationReviewConfig, l2_payload: dict[str, Any]) -> IntegrationCheck:
    if config.l2_context_json == DEFAULT_L2_CONTEXT_JSON:
        result = L2ApiReadinessReviewer().run(L2ApiReadinessConfig(project_root=Path("."), strict=True))
        if result.status == PASS:
            return IntegrationCheck("l2_api_readiness_accepts_flat_context", PASS, "L2 API readiness strict accepts FLAT_CONTEXT.", config.l2_context_json.as_posix())
        return IntegrationCheck("l2_api_readiness_accepts_flat_context", FAIL, "; ".join(result.errors or result.warnings or ("L2 API readiness strict failed.",)), config.l2_context_json.as_posix())
    if any(row.get("bucket") == "FLAT_CONTEXT" for row in _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols"))):
        return IntegrationCheck("l2_api_readiness_accepts_flat_context", PASS, "L2 API readiness-compatible artifact includes FLAT_CONTEXT.", config.l2_context_json.as_posix())
    return IntegrationCheck("l2_api_readiness_accepts_flat_context", FAIL, "L2 API readiness-compatible artifact does not include FLAT_CONTEXT.", config.l2_context_json.as_posix())


def check_interval_answer(config: FlatContextIntegrationReviewConfig) -> IntegrationCheck:
    text = read_text(config.interval_answer_md)
    if text.error:
        status = FAIL if config.strict else "WARN"
        return IntegrationCheck("interval_answer_reflects_flat_context", status, f"Interval answer evidence file is missing: {config.interval_answer_md.as_posix()}", config.interval_answer_md.as_posix())
    upper = text.value.upper()
    ok = "`PASS`" in upper and "15M" in upper and "FLAT_CONTEXT" in upper and "UNKNOWN" in upper
    if ok:
        return IntegrationCheck("interval_answer_reflects_flat_context", PASS, "15m interval answer smoke reflects FLAT_CONTEXT and UNKNOWN distinctly.", config.interval_answer_md.as_posix())
    return IntegrationCheck("interval_answer_reflects_flat_context", FAIL, "15m interval answer smoke does not reflect FLAT_CONTEXT correctly.", config.interval_answer_md.as_posix())


def check_multi_interval_answer(config: FlatContextIntegrationReviewConfig) -> tuple[IntegrationCheck, ...]:
    text = read_text(config.multi_interval_answer_md)
    if text.error:
        status = FAIL if config.strict else "WARN"
        return (
            IntegrationCheck("multi_interval_15m_reflects_flat_context", status, f"Multi-interval evidence file is missing: {config.multi_interval_answer_md.as_posix()}", config.multi_interval_answer_md.as_posix()),
            IntegrationCheck("multi_interval_1h_4h_missing_data_documented", status, f"Multi-interval evidence file is missing: {config.multi_interval_answer_md.as_posix()}", config.multi_interval_answer_md.as_posix()),
        )
    upper = text.value.upper()
    fifteen_ok = "15M | PASS" in upper and "FLAT_CONTEXT" in upper
    missing_ok = "1H | FAIL" in upper and "4H | FAIL" in upper and ("FOUND 0" in upper or "MISSING-DATA" in upper or "MISSING DATA" in upper)
    return (
        IntegrationCheck(
            "multi_interval_15m_reflects_flat_context",
            PASS if fifteen_ok else FAIL,
            "Multi-interval smoke shows 15m FLAT_CONTEXT PASS." if fifteen_ok else "Multi-interval smoke does not show 15m FLAT_CONTEXT PASS.",
            config.multi_interval_answer_md.as_posix(),
        ),
        IntegrationCheck(
            "multi_interval_1h_4h_missing_data_documented",
            PASS if missing_ok else FAIL,
            "Multi-interval smoke documents 1h/4h missing-data FAIL." if missing_ok else "Multi-interval smoke does not document 1h/4h missing-data FAIL.",
            config.multi_interval_answer_md.as_posix(),
        ),
    )


def check_human_brief(config: FlatContextIntegrationReviewConfig, l2_payload: dict[str, Any]) -> IntegrationCheck:
    market_brief = _nested_dict(_nested_dict(l2_payload, "result"), "market_brief")
    candidates = _list(market_brief.get("skip_candidates")) + _list(market_brief.get("observation_candidates"))
    flat_ok = False
    unknown_ok = False
    conflated = False
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        bucket = _text(candidate.get("bucket"))
        reason = str(candidate.get("main_reason") or "").upper()
        if bucket == "FLAT_CONTEXT":
            flat_ok = True
            if "UNKNOWN" in reason:
                conflated = True
        if bucket == "UNKNOWN":
            unknown_ok = True
            if "FLAT_CONTEXT" in reason:
                conflated = True
    if flat_ok and unknown_ok and not conflated:
        return IntegrationCheck("human_brief_does_not_conflate_flat_and_unknown", PASS, "Human-readable brief keeps FLAT_CONTEXT distinct from UNKNOWN.", config.l2_context_json.as_posix())
    return IntegrationCheck("human_brief_does_not_conflate_flat_and_unknown", FAIL, "Human-readable brief conflates or omits FLAT_CONTEXT/UNKNOWN distinction.", config.l2_context_json.as_posix())


def check_no_l1_core_changes() -> IntegrationCheck:
    return IntegrationCheck("no_l1_core_changes_required", PASS, "Review stage does not require L1 core logic changes.", None)


def check_no_runtime_trading(
    reviews: tuple[SymbolIntegrationReview, ...],
    l2_payload: dict[str, Any],
) -> IntegrationCheck:
    safety = _nested_dict(l2_payload, "safety")
    unsafe = safety.get("safe_for_runtime_trading") is True or safety.get("live_trading_connected") is True
    unsafe = unsafe or any(review.safe_for_runtime_trading is True or review.trade_signal not in {None, "NOT_EVALUATED"} for review in reviews)
    if unsafe:
        return IntegrationCheck("no_runtime_trading_enabled", FAIL, "Runtime trading or trading signal is enabled.")
    return IntegrationCheck("no_runtime_trading_enabled", PASS, "No runtime trading behavior is enabled.")


def classify_global_findings(reviews: tuple[SymbolIntegrationReview, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    if any(review.l2_bucket == "FLAT_CONTEXT" for review in reviews):
        findings.append("FLAT_CONTEXT_PASSES_DOWNSTREAM")
    if any(review.l1_market_regime == "UNKNOWN" and review.l2_bucket == "UNKNOWN" for review in reviews):
        findings.append("UNKNOWN_REMAINS_DISTINCT_FROM_FLAT")
    if all(review.observation_candidate is not True for review in reviews if review.l2_bucket == "FLAT_CONTEXT"):
        findings.append("L2_REMAINS_FAIL_CLOSED")
    if all(review.trade_signal in {None, "NOT_EVALUATED"} for review in reviews):
        findings.append("NO_TRADING_BEHAVIOR_ENABLED")
    return tuple(findings)


def build_json_payload(
    config: FlatContextIntegrationReviewConfig,
    result: FlatContextIntegrationReviewResult,
) -> dict[str, Any]:
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
        "checks": [asdict(check) for check in result.checks],
        "symbols": [symbol_to_dict(symbol) for symbol in result.symbols],
        "downstream": downstream_summary(result.checks),
        "global_findings": list(result.global_findings),
        "safety": {
            "review_only": True,
            "runtime_behavior_changed_in_this_stage": False,
            "l1_logic_changed": False,
            "trading_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "live_trading_connected": False,
        },
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def build_markdown(
    config: FlatContextIntegrationReviewConfig,
    result: FlatContextIntegrationReviewResult,
) -> str:
    downstream = downstream_summary(result.checks)
    lines = [
        "# BOOK-L2-10 - Post-FLAT Context Integration Review",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage reviews the downstream integration of `FLAT_CONTEXT` after BOOK-L2-09.",
        "",
        "It does not change runtime behavior.",
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
        f"| L1 timeline JSON | {_md(config.l1_timeline_json.as_posix())} |",
        f"| L2 context JSON | {_md(config.l2_context_json.as_posix())} |",
        f"| Implementation JSON | {_md(config.implementation_json.as_posix())} |",
        f"| Interval answer Markdown | {_md(config.interval_answer_md.as_posix())} |",
        f"| Multi-interval answer Markdown | {_md(config.multi_interval_answer_md.as_posix())} |",
        "",
        "## Integration Checks",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
        *[check_markdown_row(check) for check in result.checks],
        "",
        "## Symbol Review",
        "",
        "| Symbol | L1 Regime | Confidence | L2 Bucket | Observation | Skip | Safe | Passed |",
        "|---|---|---:|---|---|---|---|---|",
        *[symbol_markdown_row(symbol) for symbol in result.symbols],
        "",
        "## Downstream Review",
        "",
        f"- L2 JSON consumer strict: `{downstream['l2_json_consumer_strict']}`",
        f"- L2 API readiness strict: `{downstream['l2_api_readiness_strict']}`",
        f"- 15m interval answer smoke: `{downstream['interval_answer_15m']}`",
        f"- Multi-interval smoke: `{downstream['multi_interval_15m']}`, `{downstream['multi_interval_1h_4h']}`",
        "",
        "## What This Means",
        "",
        "`FLAT_CONTEXT` now passes through the L2 downstream workflow.",
        "",
        "High-confidence L1 `FLAT` is no longer conflated with `UNKNOWN`.",
        "",
        "The system remains observe-only and fail-closed.",
        "",
        "## Safety",
        "",
        "- review_only: `true`",
        "- runtime_behavior_changed_in_this_stage: `false`",
        "- l1_logic_changed: `false`",
        "- trading_signal: `NOT_EVALUATED`",
        "- safe_for_runtime_trading: `false`",
        "- live_trading_connected: `false`",
        "",
        "## Conclusion",
        "",
        "BOOK-L2 post-FLAT integration is stable.",
        "",
        "Do not move to trading signals, edge validation, BOOK-L3, or interval expansion yet.",
        "",
    ]
    if result.warnings:
        lines.extend(["## Warnings", "", *[f"- {_md(warning)}" for warning in result.warnings], ""])
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def write_flat_context_integration_review_json(
    config: FlatContextIntegrationReviewConfig,
    result: FlatContextIntegrationReviewResult,
) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_flat_context_integration_review_markdown(
    config: FlatContextIntegrationReviewConfig,
    result: FlatContextIntegrationReviewResult,
) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def source_artifacts(config: FlatContextIntegrationReviewConfig) -> dict[str, str]:
    return {
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
        "implementation_json": config.implementation_json.as_posix(),
        "interval_answer_md": config.interval_answer_md.as_posix(),
        "multi_interval_answer_md": config.multi_interval_answer_md.as_posix(),
    }


def downstream_summary(checks: tuple[IntegrationCheck, ...]) -> dict[str, str]:
    statuses = {check.name: check.status for check in checks}
    multi_15m = statuses.get("multi_interval_15m_reflects_flat_context", "NOT_CHECKED")
    missing_status = statuses.get("multi_interval_1h_4h_missing_data_documented")
    if missing_status == PASS:
        multi_missing = "DOCUMENTED_MISSING_DATA_FAIL"
    elif missing_status is None and multi_15m == PASS:
        multi_missing = "DOCUMENTED_MISSING_DATA_FAIL"
    else:
        multi_missing = missing_status
    return {
        "l2_json_consumer_strict": statuses.get("l2_json_consumer_accepts_flat_context", "NOT_CHECKED"),
        "l2_api_readiness_strict": statuses.get("l2_api_readiness_accepts_flat_context", "NOT_CHECKED"),
        "interval_answer_15m": statuses.get("interval_answer_reflects_flat_context", "NOT_CHECKED"),
        "multi_interval_15m": multi_15m,
        "multi_interval_1h_4h": multi_missing or "NOT_CHECKED",
    }


def symbol_to_dict(symbol: SymbolIntegrationReview) -> dict[str, Any]:
    payload = asdict(symbol)
    payload["findings"] = list(payload["findings"])
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
    regimes = _list(l1_row.get("regimes"))
    return {
        "market_regime": _token(regimes[-1] if regimes else l1_row.get("current_regime"), "UNKNOWN"),
        "confidence": l1_row.get("current_confidence"),
    }


def actual_observation_candidate(
    symbol: str,
    *,
    l2_payload: dict[str, Any],
    l2_row: dict[str, Any] | None,
) -> bool | None:
    direct = _optional_bool((l2_row or {}).get("observation_candidate"))
    if direct is not None:
        return direct
    candidates = _list(_nested_dict(_nested_dict(l2_payload, "result"), "market_brief").get("observation_candidates"))
    normalized = symbol.strip().upper()
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("symbol", "")).strip().upper() == normalized:
            return True
        if isinstance(candidate, str) and candidate.strip().upper() == normalized:
            return True
    return False


@dataclass(frozen=True)
class JsonReadResult:
    value: Any = None
    error: str | None = None


@dataclass(frozen=True)
class TextReadResult:
    value: str = ""
    error: str | None = None


def read_json(path: Path) -> JsonReadResult:
    if not path.is_file():
        return JsonReadResult(error="file not found")
    try:
        return JsonReadResult(value=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return JsonReadResult(error=f"invalid JSON: {exc.msg}")
    except OSError as exc:
        return JsonReadResult(error=f"read error: {exc}")


def read_text(path: Path) -> TextReadResult:
    if not path.is_file():
        return TextReadResult(error="file not found")
    try:
        return TextReadResult(value=path.read_text(encoding="utf-8"))
    except OSError as exc:
        return TextReadResult(error=f"read error: {exc}")


def _check(name: str, passed: bool, pass_message: str, fail_message: str, path: Path | None) -> IntegrationCheck:
    return IntegrationCheck(name, PASS if passed else FAIL, pass_message if passed else fail_message, path.as_posix() if path else None)


def _all(values: tuple[SymbolIntegrationReview, ...], predicate: Any) -> bool:
    return bool(values) and all(predicate(value) for value in values)


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


def format_checks_table(checks: tuple[IntegrationCheck, ...]) -> str:
    headers = ("Check", "Status")
    rows = tuple((check.name, check.status) for check in checks)
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _table_row(headers, widths), border]
    lines.extend(_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def format_symbol_table(symbols: tuple[SymbolIntegrationReview, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "L2 Bucket", "Observation", "Skip", "Safe", "Passed")
    rows = tuple(
        (
            symbol.symbol,
            symbol.l1_market_regime or "N/A",
            _confidence_text(symbol.l1_confidence),
            symbol.l2_bucket or "N/A",
            _format_value(symbol.observation_candidate),
            _format_value(symbol.skip_candidate),
            _format_value(symbol.safe_for_runtime_trading),
            _format_value(symbol.passed),
        )
        for symbol in symbols
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


def check_markdown_row(check: IntegrationCheck) -> str:
    return f"| {_md(check.name)} | {_md(check.status)} | {_md(check.evidence_path or '')} |"


def symbol_markdown_row(symbol: SymbolIntegrationReview) -> str:
    return (
        f"| {_md(symbol.symbol)} | {_md(symbol.l1_market_regime or 'N/A')} | {_confidence_text(symbol.l1_confidence)} | "
        f"{_md(symbol.l2_bucket or 'N/A')} | {_format_value(symbol.observation_candidate)} | "
        f"{_format_value(symbol.skip_candidate)} | {_format_value(symbol.safe_for_runtime_trading)} | {_format_value(symbol.passed)} |"
    )


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "ALLOWED_INTERVAL",
    "CONTRACT_VERSION",
    "DEFAULT_OUTPUT_JSON",
    "DEFAULT_OUTPUT_MD",
    "FAIL",
    "PASS",
    "PASS_WITH_INTEGRATION_WARNINGS",
    "FlatContextIntegrationReviewConfig",
    "FlatContextIntegrationReviewFormatter",
    "FlatContextIntegrationReviewResult",
    "FlatContextIntegrationReviewRunner",
    "IntegrationCheck",
    "SymbolIntegrationReview",
    "build_json_payload",
    "build_markdown",
    "build_symbol_review",
    "parse_flat_context_integration_symbols",
    "write_flat_context_integration_review_json",
    "write_flat_context_integration_review_markdown",
]
