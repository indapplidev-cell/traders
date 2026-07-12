from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.80
DEFAULT_FLAT_DIAGNOSTIC_JSON = Path("reports/book_l1/flat_context_alignment_diagnostic.json")
DEFAULT_ALIGNMENT_REVIEW_JSON = Path("reports/book_l1/l1_l2_regime_alignment_review.json")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_l2/flat_context_handling_proposal.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l2/flat_context_handling_proposal.md")

SERVICE_NAME = "BOOK_L2_MARKET_INTERPRETER"
REPORT_TYPE = "flat_context_handling_proposal"
CONTRACT_VERSION = "book_l2_flat_context_handling_proposal_v1"

PASS = "PASS"
PASS_WITH_PROPOSAL_WARNINGS = "PASS_WITH_PROPOSAL_WARNINGS"
FAIL = "FAIL"

RECOMMENDED_OPTION = "OPTION_C_FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE"
RECOMMENDED_NEXT_STAGE = "BOOK-L2-09 — Implement FLAT Context Handling"

CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN = "CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN"
HIGH_CONFIDENCE_FLAT_PRESENT = "HIGH_CONFIDENCE_FLAT_PRESENT"
FLAT_RECEIVED_BY_L2 = "FLAT_RECEIVED_BY_L2"
FLAT_CURRENTLY_MAPPED_TO_UNKNOWN = "FLAT_CURRENTLY_MAPPED_TO_UNKNOWN"
FLAT_CONTEXT_SHOULD_BE_PRESERVED = "FLAT_CONTEXT_SHOULD_BE_PRESERVED"
FLAT_SHOULD_REMAIN_NON_TRADING = "FLAT_SHOULD_REMAIN_NON_TRADING"
FLAT_OBSERVATION_CANDIDATE_NOT_APPROVED = "FLAT_OBSERVATION_CANDIDATE_NOT_APPROVED"
L2_CONTEXT_CONTRACT_UPDATE_PROPOSED = "L2_CONTEXT_CONTRACT_UPDATE_PROPOSED"
L2_CONTEXT_RULE_UPDATE_PROPOSED = "L2_CONTEXT_RULE_UPDATE_PROPOSED"
BOOK_L2_09_IMPLEMENTATION_RECOMMENDED = "BOOK_L2_09_IMPLEMENTATION_RECOMMENDED"

CRITICAL_FALSE_FIELDS = (
    "safe_for_runtime_trading",
    "live_trading_connected",
    "orders_enabled",
    "traders_core_connected",
    "approved_for_live_trading",
    "approved_for_auto_activation",
)


@dataclass(frozen=True)
class FlatContextHandlingProposalConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    flat_diagnostic_json: Path = DEFAULT_FLAT_DIAGNOSTIC_JSON
    alignment_review_json: Path = DEFAULT_ALIGNMENT_REVIEW_JSON
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
        object.__setattr__(self, "flat_diagnostic_json", Path(self.flat_diagnostic_json))
        object.__setattr__(self, "alignment_review_json", Path(self.alignment_review_json))
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class FlatContextHandlingCaseProposal:
    symbol: str
    l1_market_regime: str | None
    l1_confidence: float | None
    current_l2_bucket: str | None
    current_skip_candidate: bool | None
    is_high_confidence_flat: bool = False
    proposed_l2_bucket: str = "FLAT_CONTEXT"
    proposed_context_label: str = "HIGH_CONFIDENCE_FLAT"
    proposed_observation_candidate: bool = False
    proposed_skip_candidate: bool = True
    proposed_reason_codes: tuple[str, ...] = (
        "L1_FLAT_HIGH_CONFIDENCE",
        "FLAT_CONTEXT_PRESERVED",
        "NON_DIRECTIONAL_CONTEXT",
        "NOT_TRADING_SIGNAL",
    )
    proposed_main_reason: str = (
        "L1 identifies a high-confidence FLAT regime; "
        "L2 preserves it as non-directional observe-only context."
    )
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlatContextHandlingProposalResult:
    status: str
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    recommended_option: str = RECOMMENDED_OPTION
    recommended_next_stage: str = RECOMMENDED_NEXT_STAGE
    cases: tuple[FlatContextHandlingCaseProposal, ...] = ()
    global_findings: tuple[str, ...] = ()
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    safety: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_PROPOSAL_WARNINGS}


class FlatContextHandlingProposalRunner:
    def run(
        self,
        config: FlatContextHandlingProposalConfig | None = None,
    ) -> FlatContextHandlingProposalResult:
        active_config = config or FlatContextHandlingProposalConfig()
        errors: list[str] = []
        warnings: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            result = FlatContextHandlingProposalResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                errors=(
                    "BOOK-L2-08 proposes FLAT handling only for the stabilized 15m workflow; "
                    f"requested interval was {active_config.interval}.",
                ),
                safety=build_proposal_safety_payload(),
            )
            self._write_outputs(active_config, result)
            return result

        flat_read = read_json(
            active_config.flat_diagnostic_json,
            missing_hint="Run book-l1-flat-context-alignment-diagnostic first.",
        )
        alignment_read = read_json(
            active_config.alignment_review_json,
            missing_hint="Run book-l1-l2-regime-alignment-review first.",
        )
        l1_read = read_json(active_config.l1_timeline_json, missing_hint="Run book-l1-timeline-preview export first.")
        l2_read = read_json(active_config.l2_context_json, missing_hint="Run book-l2-timeline-context export first.")
        for read_result in (flat_read, alignment_read, l1_read, l2_read):
            if read_result.error:
                errors.append(read_result.error)

        if errors:
            result = FlatContextHandlingProposalResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                warnings=tuple(dict.fromkeys(warnings)),
                errors=tuple(dict.fromkeys(errors)),
                safety=build_proposal_safety_payload(
                    _dict(flat_read.value),
                    _dict(alignment_read.value),
                    _dict(l1_read.value),
                    _dict(l2_read.value),
                ),
            )
            self._write_outputs(active_config, result)
            return result

        flat_payload = _dict(flat_read.value)
        alignment_payload = _dict(alignment_read.value)
        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)

        errors.extend(validate_source_contracts(active_config, flat_payload, alignment_payload, l1_payload, l2_payload))
        errors.extend(validate_fail_closed_safety(flat_payload, alignment_payload, l1_payload, l2_payload))

        cases = tuple(
            build_case_proposal(
                symbol,
                threshold=active_config.high_confidence_threshold,
                flat_payload=flat_payload,
                alignment_payload=alignment_payload,
                l1_payload=l1_payload,
                l2_payload=l2_payload,
            )
            for symbol in active_config.symbols
        )
        if not any(case.l1_market_regime or case.current_l2_bucket for case in cases):
            errors.append("Could not match requested symbols between proposal source artifacts.")

        global_findings = classify_global_findings(cases)
        if not any(case.is_high_confidence_flat for case in cases):
            warnings.append("No high-confidence FLAT cases were found for the requested symbols.")

        if errors:
            status = FAIL
        elif has_current_flat_unknown_mapping(cases):
            status = PASS_WITH_PROPOSAL_WARNINGS
        else:
            status = PASS

        result = FlatContextHandlingProposalResult(
            status=status,
            interval=active_config.interval,
            high_confidence_threshold=active_config.high_confidence_threshold,
            cases=cases,
            global_findings=global_findings,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
            safety=build_proposal_safety_payload(flat_payload, alignment_payload, l1_payload, l2_payload),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(
        self,
        config: FlatContextHandlingProposalConfig,
        result: FlatContextHandlingProposalResult,
    ) -> None:
        try:
            json_path = write_flat_context_handling_proposal_json(config, result)
            md_path = write_flat_context_handling_proposal_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError:
            pass


class FlatContextHandlingProposalFormatter:
    def format(
        self,
        result: FlatContextHandlingProposalResult,
        *,
        config: FlatContextHandlingProposalConfig,
    ) -> str:
        lines = [
            "BOOK-L2-08 FLAT Context Handling Proposal",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"High confidence threshold: {config.high_confidence_threshold:.2f}",
            "",
            "Current problem:",
            current_problem_summary(result),
            "",
            "Proposed behavior:",
            "L1 FLAT high confidence -> L2 FLAT_CONTEXT",
            "observation_candidate: false",
            "skip_candidate: true",
            "safe_for_runtime_trading: false",
            "",
            "Cases:",
            format_case_table(result.cases),
            "",
            "Recommended option:",
            result.recommended_option,
            "",
            "Recommended next stage:",
            result.recommended_next_stage,
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
                    f"proposed_reason_codes={_join_or_none(case.proposed_reason_codes)}"
                )
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_flat_context_proposal_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_source_contracts(
    config: FlatContextHandlingProposalConfig,
    flat_payload: dict[str, Any],
    alignment_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    if flat_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("FLAT diagnostic JSON service must be BOOK_L1_MARKET_READER.")
    if flat_payload.get("report_type") != "flat_context_alignment_diagnostic":
        errors.append("FLAT diagnostic JSON report_type must be flat_context_alignment_diagnostic.")
    if _nested_dict(flat_payload, "request").get("interval") != config.interval:
        errors.append("FLAT diagnostic JSON interval does not match proposal interval.")
    if alignment_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("Alignment review JSON service must be BOOK_L1_MARKET_READER.")
    if alignment_payload.get("report_type") != "l1_l2_regime_alignment_review":
        errors.append("Alignment review JSON report_type must be l1_l2_regime_alignment_review.")
    if _nested_dict(alignment_payload, "request").get("interval") != config.interval:
        errors.append("Alignment review JSON interval does not match proposal interval.")
    if l1_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match proposal interval.")
    if l2_payload.get("service") != SERVICE_NAME:
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if not _list_of_dicts(flat_payload.get("cases")):
        errors.append("FLAT diagnostic JSON must contain cases.")
    if not _list_of_dicts(alignment_payload.get("symbols")):
        errors.append("Alignment review JSON must contain symbols.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    return tuple(errors)


def validate_fail_closed_safety(*payloads: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for source_name, payload in (
        ("FLAT diagnostic", payloads[0] if len(payloads) > 0 else {}),
        ("alignment review", payloads[1] if len(payloads) > 1 else {}),
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


def build_case_proposal(
    symbol: str,
    *,
    threshold: float,
    flat_payload: dict[str, Any],
    alignment_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> FlatContextHandlingCaseProposal:
    flat_case = find_symbol_row(_list_of_dicts(flat_payload.get("cases")), symbol)
    alignment_row = find_symbol_row(_list_of_dicts(alignment_payload.get("symbols")), symbol)
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    l1_current = extract_current_window(l1_row)

    l1_regime = (
        _text(flat_case.get("l1_regime") if flat_case else None)
        or _text(flat_case.get("l1_market_regime") if flat_case else None)
        or _text(alignment_row.get("l1_regime") if alignment_row else None)
        or _text(l1_current.get("market_regime"))
    )
    l1_confidence = _optional_float(flat_case.get("l1_confidence") if flat_case else None)
    if l1_confidence is None:
        l1_confidence = _optional_float(alignment_row.get("l1_confidence") if alignment_row else None)
    if l1_confidence is None:
        l1_confidence = _optional_float(l1_current.get("confidence"))

    current_l2_bucket = (
        _text(flat_case.get("l2_bucket") if flat_case else None)
        or _text(flat_case.get("current_l2_bucket") if flat_case else None)
        or _text(alignment_row.get("l2_bucket") if alignment_row else None)
        or _text(l2_row.get("bucket") if l2_row else None)
    )
    current_skip_candidate = _optional_bool(flat_case.get("l2_skip_candidate") if flat_case else None)
    if current_skip_candidate is None:
        current_skip_candidate = _optional_bool(flat_case.get("current_skip_candidate") if flat_case else None)
    if current_skip_candidate is None:
        current_skip_candidate = _optional_bool(alignment_row.get("l2_skip_candidate") if alignment_row else None)
    if current_skip_candidate is None:
        current_skip_candidate = _optional_bool(l2_row.get("skip_candidate") if l2_row else None)

    l2_received_regime = _text(flat_case.get("l2_received_regime") if flat_case else None) or _text(
        l2_row.get("current_regime") if l2_row else None
    )
    is_high_confidence_flat = l1_regime == "FLAT" and l1_confidence is not None and l1_confidence >= threshold
    findings = classify_case_findings(
        is_high_confidence_flat=is_high_confidence_flat,
        l2_received_regime=l2_received_regime,
        current_l2_bucket=current_l2_bucket,
        current_skip_candidate=current_skip_candidate,
    )
    if is_high_confidence_flat:
        return FlatContextHandlingCaseProposal(
            symbol=symbol,
            l1_market_regime=l1_regime,
            l1_confidence=l1_confidence,
            current_l2_bucket=current_l2_bucket,
            current_skip_candidate=current_skip_candidate,
            is_high_confidence_flat=True,
            findings=findings,
        )
    return FlatContextHandlingCaseProposal(
        symbol=symbol,
        l1_market_regime=l1_regime,
        l1_confidence=l1_confidence,
        current_l2_bucket=current_l2_bucket,
        current_skip_candidate=current_skip_candidate,
        is_high_confidence_flat=False,
        proposed_l2_bucket=current_l2_bucket or "UNKNOWN",
        proposed_context_label=current_l2_bucket or "UNKNOWN",
        proposed_observation_candidate=False,
        proposed_skip_candidate=True if current_skip_candidate is None else current_skip_candidate,
        proposed_reason_codes=(),
        proposed_main_reason="No high-confidence FLAT proposal applies to this symbol.",
        findings=findings,
    )


def classify_case_findings(
    *,
    is_high_confidence_flat: bool,
    l2_received_regime: str | None,
    current_l2_bucket: str | None,
    current_skip_candidate: bool | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    if is_high_confidence_flat:
        findings.extend(
            (
                HIGH_CONFIDENCE_FLAT_PRESENT,
                FLAT_CONTEXT_SHOULD_BE_PRESERVED,
                FLAT_SHOULD_REMAIN_NON_TRADING,
                FLAT_OBSERVATION_CANDIDATE_NOT_APPROVED,
                L2_CONTEXT_CONTRACT_UPDATE_PROPOSED,
                L2_CONTEXT_RULE_UPDATE_PROPOSED,
                BOOK_L2_09_IMPLEMENTATION_RECOMMENDED,
            )
        )
        if l2_received_regime == "FLAT":
            findings.append(FLAT_RECEIVED_BY_L2)
        if current_l2_bucket == "UNKNOWN":
            findings.append(FLAT_CURRENTLY_MAPPED_TO_UNKNOWN)
        if current_l2_bucket == "UNKNOWN" and current_skip_candidate is True:
            findings.append(CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN)
    return tuple(dict.fromkeys(findings))


def classify_global_findings(cases: tuple[FlatContextHandlingCaseProposal, ...]) -> tuple[str, ...]:
    ordered_categories = (
        CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN,
        HIGH_CONFIDENCE_FLAT_PRESENT,
        FLAT_RECEIVED_BY_L2,
        FLAT_CURRENTLY_MAPPED_TO_UNKNOWN,
        FLAT_CONTEXT_SHOULD_BE_PRESERVED,
        FLAT_SHOULD_REMAIN_NON_TRADING,
        FLAT_OBSERVATION_CANDIDATE_NOT_APPROVED,
        L2_CONTEXT_CONTRACT_UPDATE_PROPOSED,
        L2_CONTEXT_RULE_UPDATE_PROPOSED,
        BOOK_L2_09_IMPLEMENTATION_RECOMMENDED,
    )
    return tuple(category for category in ordered_categories if any(category in case.findings for case in cases))


def has_current_flat_unknown_mapping(cases: tuple[FlatContextHandlingCaseProposal, ...]) -> bool:
    return any(FLAT_CURRENTLY_MAPPED_TO_UNKNOWN in case.findings for case in cases)


def build_json_payload(
    config: FlatContextHandlingProposalConfig,
    result: FlatContextHandlingProposalResult,
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
        "current_behavior": {
            "summary": current_problem_summary(result),
            "problem": "FLAT and UNKNOWN are conflated at L2 context interpretation boundary."
            if has_current_flat_unknown_mapping(result.cases)
            else "No current FLAT to UNKNOWN mapping was found in the reviewed cases.",
        },
        "proposed_behavior": {
            "recommended_option": result.recommended_option,
            "summary": (
                "High-confidence L1 FLAT should be preserved by L2 as FLAT_CONTEXT, "
                "but remain non-observation by default."
            ),
            "default_l2_bucket": "FLAT_CONTEXT",
            "default_context_label": "HIGH_CONFIDENCE_FLAT",
            "default_observation_candidate": False,
            "default_skip_candidate": True,
            "runtime_change_approved": False,
        },
        "cases": [case_to_dict(case) for case in result.cases],
        "semantic_options": semantic_options_payload(),
        "implementation_plan": implementation_plan_payload(result),
        "global_findings": list(result.global_findings),
        "safety": result.safety,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def write_flat_context_handling_proposal_json(
    config: FlatContextHandlingProposalConfig,
    result: FlatContextHandlingProposalResult,
) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_flat_context_handling_proposal_markdown(
    config: FlatContextHandlingProposalConfig,
    result: FlatContextHandlingProposalResult,
) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def build_markdown(
    config: FlatContextHandlingProposalConfig,
    result: FlatContextHandlingProposalResult,
) -> str:
    lines = [
        "# BOOK-L2-08 - FLAT Context Handling Proposal",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage proposes how BOOK-L2 should handle high-confidence L1 `FLAT`.",
        "",
        "It does not change L1 or L2 runtime logic.",
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
        f"| FLAT diagnostic JSON | {_md(config.flat_diagnostic_json.as_posix())} |",
        f"| Alignment review JSON | {_md(config.alignment_review_json.as_posix())} |",
        f"| L1 timeline JSON | {_md(config.l1_timeline_json.as_posix())} |",
        f"| L2 context JSON | {_md(config.l2_context_json.as_posix())} |",
        "",
        "## Current Problem",
        "",
        current_problem_summary(result),
        "",
        "This conflates two different meanings:",
        "",
        "- `FLAT` means the market was read as non-directional / range-like.",
        "- `UNKNOWN` means the market was not read clearly.",
        "",
        "## Proposed Interpretation",
        "",
        "High-confidence L1 `FLAT` should be preserved by L2 as `FLAT_CONTEXT`.",
        "",
        "Default proposal:",
        "",
        "| Field | Proposed value |",
        "|---|---|",
        "| L2 bucket | FLAT_CONTEXT |",
        "| Context label | HIGH_CONFIDENCE_FLAT |",
        "| Observation candidate | false |",
        "| Skip candidate | true |",
        "| Trading signal | NOT_EVALUATED |",
        "| Safe for runtime trading | false |",
        "",
        "## Case Proposals",
        "",
        "| Symbol | L1 Regime | Confidence | Current L2 Bucket | Current Skip | Proposed Bucket | Proposed Observation |",
        "|---|---|---:|---|---|---|---|",
        *[case_markdown_row(case) for case in result.cases],
        "",
        "## Semantic Options Considered",
        "",
        "### Option A - Keep current behavior",
        "",
        "Not recommended.",
        "",
        "### Option B - FLAT as observation candidate",
        "",
        "Not recommended now.",
        "",
        "### Option C - FLAT context but not observation candidate",
        "",
        "Recommended safe default.",
        "",
        "### Option D - FLAT quality depends on reason codes",
        "",
        "Recommended later after reason-code review.",
        "",
        "## Recommended Option",
        "",
        f"`{result.recommended_option}`",
        "",
        "Meaning:",
        "",
        "High-confidence `FLAT` should not become `UNKNOWN`.",
        "",
        "It should be preserved as market context, but should not become an observation candidate by default.",
        "",
        "## Implementation Not Approved Yet",
        "",
        "This stage does not implement the rule.",
        "",
        "Runtime implementation should be done in:",
        "",
        f"`{result.recommended_next_stage}`",
        "",
        "## Proposed BOOK-L2-09 Scope",
        "",
        "- update L2 context mapping so high-confidence FLAT maps to FLAT_CONTEXT;",
        "- keep observation_candidate false by default;",
        "- keep skip_candidate true by default;",
        "- keep safe_for_runtime_trading false;",
        "- ensure UNKNOWN remains distinct from FLAT;",
        "- update L2 JSON consumer/API readiness tests.",
        "",
        "## Safety",
        "",
        "- read_only: `true`",
        "- proposal_only: `true`",
        "- runtime_behavior_changed: `false`",
        "- l1_logic_changed: `false`",
        "- l2_rules_changed: `false`",
        "- trading_signal: `NOT_EVALUATED`",
        "- safe_for_runtime_trading: `false`",
        "- live_trading_connected: `false`",
        "",
        "## Conclusion",
        "",
        "BOOK-L2 should preserve high-confidence L1 `FLAT` as `FLAT_CONTEXT`.",
        "",
        "Do not move to edge validation, BOOK-L3, interval expansion, or runtime execution yet.",
        "",
    ]
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def current_problem_summary(result: FlatContextHandlingProposalResult) -> str:
    if result.status == FAIL:
        return "The FLAT context handling proposal could not be completed from the available artifacts."
    if has_current_flat_unknown_mapping(result.cases):
        return "High-confidence L1 FLAT is currently mapped by L2 to UNKNOWN/SKIP."
    if any(case.is_high_confidence_flat for case in result.cases):
        return "High-confidence L1 FLAT is already preserved outside UNKNOWN/SKIP in the reviewed evidence."
    return "No high-confidence L1 FLAT cases are present in the reviewed evidence."


def source_artifacts(config: FlatContextHandlingProposalConfig) -> dict[str, str]:
    return {
        "flat_diagnostic_json": config.flat_diagnostic_json.as_posix(),
        "alignment_review_json": config.alignment_review_json.as_posix(),
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
    }


def semantic_options_payload() -> list[dict[str, str]]:
    return [
        {
            "option_id": "OPTION_A_KEEP_CURRENT_BEHAVIOR",
            "recommendation": "not recommended",
            "reason": "It conflates FLAT and UNKNOWN and loses L1 information.",
        },
        {
            "option_id": "OPTION_B_FLAT_AS_OBSERVATION_CANDIDATE",
            "recommendation": "not recommended now",
            "reason": "Could be interpreted as stronger action than needed for the current stage.",
        },
        {
            "option_id": RECOMMENDED_OPTION,
            "recommendation": "recommended safe default",
            "reason": "Preserves L1 reading, does not create runtime behavior, and keeps L2 conservative.",
        },
        {
            "option_id": "OPTION_D_FLAT_QUALITY_DEPENDS_ON_REASON_CODES",
            "recommendation": "recommended later",
            "reason": "Better long-term quality, but requires a future reason-code improvement stage.",
        },
    ]


def implementation_plan_payload(result: FlatContextHandlingProposalResult) -> dict[str, Any]:
    return {
        "recommended_next_stage": result.recommended_next_stage,
        "approved_now": False,
        "planned_files_to_review": [
            "app/market_interpreter/context_rules.py",
            "app/market_interpreter/context_quality.py",
            "app/market_interpreter/context_summary.py",
            "app/market_interpreter/l1_timeline_consumer.py",
        ],
        "planned_tests": [
            "high-confidence FLAT maps to FLAT_CONTEXT",
            "FLAT_CONTEXT does not create observation candidate by default",
            "FLAT_CONTEXT remains safe_for_runtime_trading false",
            "UNKNOWN remains distinct from FLAT",
        ],
    }


def build_proposal_safety_payload(*payloads: dict[str, Any]) -> dict[str, Any]:
    safety = {
        "read_only": True,
        "proposal_only": True,
        "runtime_behavior_changed": False,
        "l1_logic_changed": False,
        "l2_rules_changed": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
    }
    for payload in payloads:
        source_safety = _dict(payload.get("safety"))
        for field_name in (
            "trade_signal",
            "traders_core_connected",
            "approved_for_live_trading",
            "approved_for_auto_activation",
            "model_training_executed",
            "binance_download_executed",
        ):
            if field_name in source_safety:
                safety[field_name] = source_safety[field_name]
    return safety


def case_to_dict(case: FlatContextHandlingCaseProposal) -> dict[str, Any]:
    payload = asdict(case)
    payload["proposed_reason_codes"] = list(payload["proposed_reason_codes"])
    payload["findings"] = list(payload["findings"])
    return payload


def case_markdown_row(case: FlatContextHandlingCaseProposal) -> str:
    return (
        f"| {_md(case.symbol)} | {_md(case.l1_market_regime or 'N/A')} | {_confidence_text(case.l1_confidence)} | "
        f"{_md(case.current_l2_bucket or 'N/A')} | {_format_value(case.current_skip_candidate)} | "
        f"{_md(case.proposed_l2_bucket)} | {_format_value(case.proposed_observation_candidate)} |"
    )


def format_case_table(cases: tuple[FlatContextHandlingCaseProposal, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "Current L2 Bucket", "Current Skip", "Proposed Bucket")
    rows = tuple(
        (
            case.symbol,
            case.l1_market_regime or "N/A",
            _confidence_text(case.l1_confidence),
            case.current_l2_bucket or "N/A",
            _format_value(case.current_skip_candidate),
            case.proposed_l2_bucket,
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
    }


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
    "PASS_WITH_PROPOSAL_WARNINGS",
    "CURRENT_L2_CONFLATES_FLAT_WITH_UNKNOWN",
    "HIGH_CONFIDENCE_FLAT_PRESENT",
    "FLAT_RECEIVED_BY_L2",
    "FLAT_CURRENTLY_MAPPED_TO_UNKNOWN",
    "FLAT_CONTEXT_SHOULD_BE_PRESERVED",
    "FLAT_SHOULD_REMAIN_NON_TRADING",
    "FLAT_OBSERVATION_CANDIDATE_NOT_APPROVED",
    "L2_CONTEXT_CONTRACT_UPDATE_PROPOSED",
    "L2_CONTEXT_RULE_UPDATE_PROPOSED",
    "BOOK_L2_09_IMPLEMENTATION_RECOMMENDED",
    "RECOMMENDED_NEXT_STAGE",
    "RECOMMENDED_OPTION",
    "FlatContextHandlingCaseProposal",
    "FlatContextHandlingProposalConfig",
    "FlatContextHandlingProposalFormatter",
    "FlatContextHandlingProposalResult",
    "FlatContextHandlingProposalRunner",
    "build_json_payload",
    "build_markdown",
    "parse_flat_context_proposal_symbols",
    "write_flat_context_handling_proposal_json",
    "write_flat_context_handling_proposal_markdown",
]
