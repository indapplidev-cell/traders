from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ALLOWED_INTERVAL = "15m"
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.80
DEFAULT_PROPOSAL_JSON = Path("reports/book_l2/flat_context_handling_proposal.json")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_l2/flat_context_handling_implementation.json")
DEFAULT_OUTPUT_MD = Path("reports/book_l2/flat_context_handling_implementation.md")

SERVICE_NAME = "BOOK_L2_MARKET_INTERPRETER"
REPORT_TYPE = "flat_context_handling_implementation"
CONTRACT_VERSION = "book_l2_flat_context_handling_implementation_v1"

PASS = "PASS"
PASS_WITH_IMPLEMENTATION_WARNINGS = "PASS_WITH_IMPLEMENTATION_WARNINGS"
FAIL = "FAIL"

FLAT_CONTEXT_REASON_CODES = (
    "L1_FLAT_HIGH_CONFIDENCE",
    "FLAT_CONTEXT_PRESERVED",
    "NON_DIRECTIONAL_CONTEXT",
    "NOT_TRADING_SIGNAL",
)

CRITICAL_FALSE_FIELDS = (
    "safe_for_runtime_trading",
    "live_trading_connected",
    "orders_enabled",
    "traders_core_connected",
    "approved_for_live_trading",
    "approved_for_auto_activation",
)


@dataclass(frozen=True)
class FlatContextHandlingImplementationConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    proposal_json: Path = DEFAULT_PROPOSAL_JSON
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
        object.__setattr__(self, "proposal_json", Path(self.proposal_json))
        object.__setattr__(self, "l1_timeline_json", Path(self.l1_timeline_json))
        object.__setattr__(self, "l2_context_json", Path(self.l2_context_json))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class FlatContextHandlingImplementationCase:
    symbol: str
    l1_market_regime: str | None
    l1_confidence: float | None
    actual_l2_bucket: str | None
    actual_observation_candidate: bool | None
    actual_skip_candidate: bool | None
    actual_safe_for_runtime_trading: bool | None
    expected_l2_bucket: str | None
    expected_observation_candidate: bool | None
    expected_skip_candidate: bool | None
    passed: bool
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FlatContextHandlingImplementationResult:
    status: str
    interval: str = ALLOWED_INTERVAL
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    cases: tuple[FlatContextHandlingImplementationCase, ...] = ()
    global_findings: tuple[str, ...] = ()
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_IMPLEMENTATION_WARNINGS}


class FlatContextHandlingImplementationRunner:
    def run(
        self,
        config: FlatContextHandlingImplementationConfig | None = None,
    ) -> FlatContextHandlingImplementationResult:
        active_config = config or FlatContextHandlingImplementationConfig()
        errors: list[str] = []
        warnings: list[str] = []

        if active_config.interval != ALLOWED_INTERVAL:
            result = FlatContextHandlingImplementationResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                errors=(
                    "BOOK-L2-09 implements FLAT handling only for stabilized 15m workflow; "
                    f"requested interval was {active_config.interval}.",
                ),
            )
            self._write_outputs(active_config, result)
            return result

        proposal_read = read_json(
            active_config.proposal_json,
            missing_hint="Required proposal artifact is missing. Run book-l2-flat-context-handling-proposal first.",
        )
        if proposal_read.error:
            result = FlatContextHandlingImplementationResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                errors=(proposal_read.error,),
            )
            self._write_outputs(active_config, result)
            return result

        l1_read = read_json(active_config.l1_timeline_json, missing_hint="Run book-l1-timeline-preview export first.")
        l2_read = read_json(active_config.l2_context_json, missing_hint="Run book-l2-timeline-context export first.")
        for read_result in (l1_read, l2_read):
            if read_result.error:
                errors.append(read_result.error)

        if errors:
            result = FlatContextHandlingImplementationResult(
                status=FAIL,
                interval=active_config.interval,
                high_confidence_threshold=active_config.high_confidence_threshold,
                errors=tuple(dict.fromkeys(errors)),
            )
            self._write_outputs(active_config, result)
            return result

        proposal_payload = _dict(proposal_read.value)
        l1_payload = _dict(l1_read.value)
        l2_payload = _dict(l2_read.value)
        errors.extend(validate_source_contracts(active_config, proposal_payload, l1_payload, l2_payload))
        errors.extend(validate_fail_closed_safety(l1_payload, l2_payload))

        cases = tuple(
            build_implementation_case(
                symbol,
                threshold=active_config.high_confidence_threshold,
                l1_payload=l1_payload,
                l2_payload=l2_payload,
            )
            for symbol in active_config.symbols
        )
        if not any(case.l1_market_regime or case.actual_l2_bucket for case in cases):
            errors.append("Could not match requested symbols between L1 and L2 artifacts.")

        case_errors = tuple(f"{case.symbol}: {'; '.join(case.findings)}" for case in cases if not case.passed)
        errors.extend(case_errors)

        high_confidence_flat_count = sum(
            1
            for case in cases
            if case.l1_market_regime == "FLAT"
            and case.l1_confidence is not None
            and case.l1_confidence >= active_config.high_confidence_threshold
        )
        if high_confidence_flat_count == 0:
            warnings.append("No high-confidence FLAT cases were found for the requested symbols.")

        global_findings = classify_global_findings(cases)
        if errors:
            status = FAIL
        elif warnings:
            status = PASS_WITH_IMPLEMENTATION_WARNINGS
        else:
            status = PASS

        result = FlatContextHandlingImplementationResult(
            status=status,
            interval=active_config.interval,
            high_confidence_threshold=active_config.high_confidence_threshold,
            cases=cases,
            global_findings=global_findings,
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
        )
        self._write_outputs(active_config, result)
        return result

    def _write_outputs(
        self,
        config: FlatContextHandlingImplementationConfig,
        result: FlatContextHandlingImplementationResult,
    ) -> None:
        try:
            json_path = write_flat_context_handling_implementation_json(config, result)
            md_path = write_flat_context_handling_implementation_markdown(config, result)
            object.__setattr__(result, "output_json", json_path.as_posix())
            object.__setattr__(result, "output_md", md_path.as_posix())
        except OSError as exc:
            object.__setattr__(result, "status", FAIL)
            object.__setattr__(result, "errors", (*result.errors, f"Could not write implementation evidence: {exc}"))


class FlatContextHandlingImplementationFormatter:
    def format(
        self,
        result: FlatContextHandlingImplementationResult,
        *,
        config: FlatContextHandlingImplementationConfig,
    ) -> str:
        lines = [
            "BOOK-L2-09 Implement FLAT Context Handling",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Interval: {config.interval}",
            f"High confidence threshold: {config.high_confidence_threshold:.2f}",
            "",
            "Implemented behavior:",
            "High-confidence FLAT -> FLAT_CONTEXT",
            "observation_candidate: false",
            "skip_candidate: true",
            "safe_for_runtime_trading: false",
            "UNKNOWN remains distinct from FLAT: true",
            "",
            "Cases:",
            format_case_table(result.cases),
            "",
            "Output files:",
            result.output_json or config.output_json.as_posix(),
            result.output_md or config.output_md.as_posix(),
        ]
        if config.show_details:
            lines.extend(["", "Details:"])
            lines.extend(
                f"- {case.symbol}: findings={_join_or_none(case.findings)}"
                for case in result.cases
            )
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_flat_context_implementation_symbols(
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
    config: FlatContextHandlingImplementationConfig,
    proposal_payload: dict[str, Any],
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> tuple[str, ...]:
    errors: list[str] = []
    if proposal_payload.get("service") != SERVICE_NAME:
        errors.append("Proposal JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if proposal_payload.get("report_type") != "flat_context_handling_proposal":
        errors.append("Proposal JSON report_type must be flat_context_handling_proposal.")
    if _nested_dict(proposal_payload, "request").get("interval") != config.interval:
        errors.append("Proposal JSON interval does not match implementation interval.")
    if l1_payload.get("service") != "BOOK_L1_MARKET_READER":
        errors.append("L1 timeline JSON service must be BOOK_L1_MARKET_READER.")
    if l1_payload.get("report_type") != "timeline_preview":
        errors.append("L1 timeline JSON report_type must be timeline_preview.")
    if _nested_dict(l1_payload, "request").get("interval") != config.interval:
        errors.append("L1 timeline JSON interval does not match implementation interval.")
    if l2_payload.get("service") != SERVICE_NAME:
        errors.append("L2 context JSON service must be BOOK_L2_MARKET_INTERPRETER.")
    if l2_payload.get("report_type") != "timeline_context":
        errors.append("L2 context JSON report_type must be timeline_context.")
    if not _list_of_dicts(_nested_dict(l1_payload, "result").get("rows")):
        errors.append("L1 timeline JSON must contain result.rows.")
    if not _list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")):
        errors.append("L2 context JSON must contain result.symbols.")
    return tuple(errors)


def validate_fail_closed_safety(*payloads: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for source_name, payload in (("L1", payloads[0] if payloads else {}), ("L2", payloads[1] if len(payloads) > 1 else {})):
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


def build_implementation_case(
    symbol: str,
    *,
    threshold: float,
    l1_payload: dict[str, Any],
    l2_payload: dict[str, Any],
) -> FlatContextHandlingImplementationCase:
    l1_row = find_symbol_row(_list_of_dicts(_nested_dict(l1_payload, "result").get("rows")), symbol)
    l2_row = find_symbol_row(_list_of_dicts(_nested_dict(_nested_dict(l2_payload, "result"), "symbols")), symbol)
    if l2_row is None:
        l2_row = find_symbol_row(_list_of_dicts(_nested_dict(l2_payload, "result").get("symbols")), symbol)
    l1_current = extract_current_window(l1_row)
    l1_regime = _token(l1_current.get("market_regime") or (l1_row or {}).get("current_regime"), "UNKNOWN") if l1_row else None
    l1_confidence = _optional_float(l1_current.get("confidence") if l1_current else None)
    if l1_confidence is None and l1_row:
        l1_confidence = _optional_float(l1_row.get("current_confidence"))

    actual_l2_bucket = _text(l2_row.get("bucket") if l2_row else None)
    actual_skip_candidate = _optional_bool(l2_row.get("skip_candidate") if l2_row else None)
    actual_observation_candidate = _actual_observation_candidate(symbol, l2_payload=l2_payload, l2_row=l2_row)
    actual_safe = _optional_bool(l2_row.get("safe_for_runtime_trading") if l2_row else None)
    if actual_safe is None:
        actual_safe = _optional_bool(_nested_dict(l2_payload, "safety").get("safe_for_runtime_trading"))

    high_confidence_flat = l1_regime == "FLAT" and l1_confidence is not None and l1_confidence >= threshold
    unknown_case = l1_regime == "UNKNOWN"
    if high_confidence_flat:
        expected_bucket = "FLAT_CONTEXT"
        expected_observation = False
        expected_skip = True
    elif unknown_case:
        expected_bucket = "UNKNOWN"
        expected_observation = False
        expected_skip = True
    else:
        expected_bucket = actual_l2_bucket
        expected_observation = actual_observation_candidate
        expected_skip = actual_skip_candidate

    findings = classify_case_findings(
        high_confidence_flat=high_confidence_flat,
        unknown_case=unknown_case,
        l2_row=l2_row,
        actual_l2_bucket=actual_l2_bucket,
        actual_observation_candidate=actual_observation_candidate,
        actual_skip_candidate=actual_skip_candidate,
        actual_safe_for_runtime_trading=actual_safe,
    )
    return FlatContextHandlingImplementationCase(
        symbol=symbol,
        l1_market_regime=l1_regime,
        l1_confidence=l1_confidence,
        actual_l2_bucket=actual_l2_bucket,
        actual_observation_candidate=actual_observation_candidate,
        actual_skip_candidate=actual_skip_candidate,
        actual_safe_for_runtime_trading=actual_safe,
        expected_l2_bucket=expected_bucket,
        expected_observation_candidate=expected_observation,
        expected_skip_candidate=expected_skip,
        passed=not any(finding.startswith("FAIL_") for finding in findings),
        findings=findings,
    )


def classify_case_findings(
    *,
    high_confidence_flat: bool,
    unknown_case: bool,
    l2_row: dict[str, Any] | None,
    actual_l2_bucket: str | None,
    actual_observation_candidate: bool | None,
    actual_skip_candidate: bool | None,
    actual_safe_for_runtime_trading: bool | None,
) -> tuple[str, ...]:
    findings: list[str] = []
    reason_codes = tuple(str(item) for item in _list((l2_row or {}).get("context_reason_codes")))
    trade_signal = _text((l2_row or {}).get("trade_signal"))
    if high_confidence_flat:
        if actual_l2_bucket == "FLAT_CONTEXT":
            findings.extend(("FLAT_CONTEXT_IMPLEMENTED", "FLAT_CONTEXT_PRESERVED"))
        else:
            findings.append("FAIL_HIGH_CONFIDENCE_FLAT_NOT_FLAT_CONTEXT")
        if actual_observation_candidate is False:
            findings.append("NON_DIRECTIONAL_CONTEXT")
        else:
            findings.append("FAIL_FLAT_CONTEXT_OBSERVATION_CANDIDATE")
        if actual_skip_candidate is True:
            findings.append("FLAT_CONTEXT_SKIP_CANDIDATE")
        else:
            findings.append("FAIL_FLAT_CONTEXT_NOT_SKIP_CANDIDATE")
        if actual_safe_for_runtime_trading is False:
            findings.append("NOT_TRADING_SIGNAL")
        else:
            findings.append("FAIL_FLAT_CONTEXT_RUNTIME_SAFETY_TRUE")
        for reason_code in FLAT_CONTEXT_REASON_CODES:
            if reason_code not in reason_codes:
                findings.append(f"FAIL_MISSING_REASON_CODE_{reason_code}")
        if trade_signal not in {None, "NOT_EVALUATED"}:
            findings.append("FAIL_FLAT_CONTEXT_TRADE_SIGNAL_CHANGED")
    elif unknown_case:
        if actual_l2_bucket == "UNKNOWN":
            findings.append("UNKNOWN_REMAINS_DISTINCT_FROM_FLAT")
        else:
            findings.append("FAIL_UNKNOWN_DID_NOT_REMAIN_UNKNOWN")
        if actual_l2_bucket == "FLAT_CONTEXT":
            findings.append("FAIL_UNKNOWN_BECAME_FLAT_CONTEXT")
    else:
        findings.append("NO_HIGH_CONFIDENCE_FLAT_RULE_APPLIED")
        if actual_l2_bucket == "FLAT_CONTEXT":
            findings.append("FAIL_NON_QUALIFYING_CASE_BECAME_FLAT_CONTEXT")
    return tuple(dict.fromkeys(findings))


def classify_global_findings(cases: tuple[FlatContextHandlingImplementationCase, ...]) -> tuple[str, ...]:
    findings: list[str] = []
    if any(case.actual_l2_bucket == "FLAT_CONTEXT" for case in cases):
        findings.append("HIGH_CONFIDENCE_FLAT_MAPS_TO_FLAT_CONTEXT")
    if any(case.l1_market_regime == "UNKNOWN" and case.actual_l2_bucket == "UNKNOWN" for case in cases):
        findings.append("UNKNOWN_REMAINS_DISTINCT_FROM_FLAT")
    if all(case.actual_observation_candidate is not True for case in cases if case.actual_l2_bucket == "FLAT_CONTEXT"):
        findings.append("FLAT_CONTEXT_NOT_OBSERVATION_CANDIDATE")
    if all(case.actual_safe_for_runtime_trading is not True for case in cases if case.actual_l2_bucket == "FLAT_CONTEXT"):
        findings.append("FLAT_CONTEXT_NOT_TRADING_SIGNAL")
    return tuple(findings)


def build_json_payload(
    config: FlatContextHandlingImplementationConfig,
    result: FlatContextHandlingImplementationResult,
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
        "implemented_behavior": {
            "high_confidence_flat_maps_to": "FLAT_CONTEXT",
            "observation_candidate_default": False,
            "skip_candidate_default": True,
            "safe_for_runtime_trading": False,
            "unknown_remains_unknown": True,
        },
        "cases": [case_to_dict(case) for case in result.cases],
        "global_findings": list(result.global_findings),
        "safety": {
            "runtime_behavior_changed": True,
            "l1_logic_changed": False,
            "l2_flat_context_rule_changed": True,
            "trading_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
            "live_trading_connected": False,
        },
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def build_markdown(
    config: FlatContextHandlingImplementationConfig,
    result: FlatContextHandlingImplementationResult,
) -> str:
    lines = [
        "# BOOK-L2-09 - Implement FLAT Context Handling",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage implements BOOK-L2 handling for high-confidence L1 `FLAT`.",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Interval | {_md(config.interval)} |",
        f"| High confidence threshold | {config.high_confidence_threshold:.2f} |",
        "",
        "## Implemented Behavior",
        "",
        "| Rule | Value |",
        "|---|---|",
        "| High-confidence FLAT maps to | FLAT_CONTEXT |",
        "| Observation candidate default | false |",
        "| Skip candidate default | true |",
        "| Safe for runtime trading | false |",
        "| UNKNOWN remains distinct from FLAT | true |",
        "",
        "## Case Results",
        "",
        "| Symbol | L1 Regime | Confidence | Actual L2 Bucket | Observation | Skip | Passed |",
        "|---|---|---:|---|---|---|---|",
        *[case_markdown_row(case) for case in result.cases],
        "",
        "## What Changed",
        "",
        "BOOK-L2 now preserves high-confidence L1 `FLAT` as `FLAT_CONTEXT`.",
        "",
        "`FLAT_CONTEXT` is still non-directional and observe-only.",
        "",
        "It does not create a trading signal.",
        "",
        "## Safety",
        "",
        "- runtime_behavior_changed: `true`",
        "- l1_logic_changed: `false`",
        "- l2_flat_context_rule_changed: `true`",
        "- trading_signal: `NOT_EVALUATED`",
        "- safe_for_runtime_trading: `false`",
        "- live_trading_connected: `false`",
        "",
        "## Conclusion",
        "",
        "High-confidence L1 `FLAT` no longer becomes L2 `UNKNOWN`.",
        "",
        "L2 now preserves it as `FLAT_CONTEXT` while keeping the system fail-closed and non-trading.",
        "",
    ]
    if result.warnings:
        lines.extend(["## Warnings", "", *[f"- {_md(warning)}" for warning in result.warnings], ""])
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    return "\n".join(lines)


def write_flat_context_handling_implementation_json(
    config: FlatContextHandlingImplementationConfig,
    result: FlatContextHandlingImplementationResult,
) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def write_flat_context_handling_implementation_markdown(
    config: FlatContextHandlingImplementationConfig,
    result: FlatContextHandlingImplementationResult,
) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def source_artifacts(config: FlatContextHandlingImplementationConfig) -> dict[str, str]:
    return {
        "proposal_json": config.proposal_json.as_posix(),
        "l1_timeline_json": config.l1_timeline_json.as_posix(),
        "l2_context_json": config.l2_context_json.as_posix(),
    }


def case_to_dict(case: FlatContextHandlingImplementationCase) -> dict[str, Any]:
    payload = asdict(case)
    payload["findings"] = list(payload["findings"])
    return payload


def format_case_table(cases: tuple[FlatContextHandlingImplementationCase, ...]) -> str:
    headers = ("Symbol", "L1 Regime", "Confidence", "L2 Bucket", "Observation", "Skip", "Passed")
    rows = tuple(
        (
            case.symbol,
            case.l1_market_regime or "N/A",
            _confidence_text(case.l1_confidence),
            case.actual_l2_bucket or "N/A",
            _format_value(case.actual_observation_candidate),
            _format_value(case.actual_skip_candidate),
            _format_value(case.passed),
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


def case_markdown_row(case: FlatContextHandlingImplementationCase) -> str:
    return (
        f"| {_md(case.symbol)} | {_md(case.l1_market_regime or 'N/A')} | {_confidence_text(case.l1_confidence)} | "
        f"{_md(case.actual_l2_bucket or 'N/A')} | {_format_value(case.actual_observation_candidate)} | "
        f"{_format_value(case.actual_skip_candidate)} | {_format_value(case.passed)} |"
    )


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


def _actual_observation_candidate(
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


def read_json(path: Path, *, missing_hint: str) -> JsonReadResult:
    if not path.is_file():
        return JsonReadResult(error=missing_hint)
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
    "PASS_WITH_IMPLEMENTATION_WARNINGS",
    "FLAT_CONTEXT_REASON_CODES",
    "FlatContextHandlingImplementationCase",
    "FlatContextHandlingImplementationConfig",
    "FlatContextHandlingImplementationFormatter",
    "FlatContextHandlingImplementationResult",
    "FlatContextHandlingImplementationRunner",
    "build_implementation_case",
    "build_json_payload",
    "build_markdown",
    "parse_flat_context_implementation_symbols",
    "write_flat_context_handling_implementation_json",
    "write_flat_context_handling_implementation_markdown",
]
