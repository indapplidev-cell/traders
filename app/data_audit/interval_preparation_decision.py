from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_AUDIT_JSON = Path("reports/book_data/candle_availability_audit.json")
DEFAULT_OUTPUT_JSON = Path("reports/book_data/interval_data_preparation_decision.json")
DEFAULT_OUTPUT_MD = Path("reports/book_data/interval_data_preparation_decision.md")
CONTRACT_VERSION = "book_data_interval_preparation_decision_v1"
SERVICE_NAME = "BOOK_DATA_DECISION"
REPORT_TYPE = "interval_data_preparation_decision"

READY = "READY"
MISSING = "MISSING"
PASS = "PASS"
PASS_WITH_DATA_GAPS = "PASS_WITH_DATA_GAPS"
FAIL = "FAIL"

DECISION_15M_ONLY = "ACTIVE_INTERVAL_15M_ONLY_WITH_1H_4H_MISSING"
DECISION_ALL_READY = "ALL_REQUESTED_INTERVALS_READY"
DECISION_READY_WITH_GAPS = "ACTIVE_READY_INTERVALS_WITH_DATA_GAPS"
DECISION_NO_ACTIVE_INTERVAL = "NO_ACTIVE_INTERVAL_READY"
RECOMMENDED_OPTION = "OPTION_D_HYBRID_LATER"
NEXT_STAGE = "BOOK-DATA-03"
DEFAULT_INTERVALS = ("15m", "1h", "4h")
FUTURE_INTERVALS = ("1h", "4h")
NOT_APPROVED = (
    "binance_download",
    "db_write",
    "interval_aggregation",
    "trading_logic",
    "long_short_recommendations",
    "edge_validation",
)


@dataclass(frozen=True)
class IntervalPreparationDecisionConfig:
    audit_json_path: Path = DEFAULT_AUDIT_JSON
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "audit_json_path", Path(self.audit_json_path))
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))


@dataclass(frozen=True)
class IntervalPreparationOption:
    option_id: str
    title: str
    status: str
    recommendation: str
    pros: tuple[str, ...] = ()
    cons: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntervalAuditFinding:
    interval: str
    availability: str
    symbols: tuple[str, ...] = ()
    meaning: str = ""


@dataclass(frozen=True)
class IntervalPreparationDecisionResult:
    status: str
    decision_id: str
    recommended_option: str
    active_intervals: tuple[str, ...] = ()
    missing_intervals: tuple[str, ...] = ()
    optional_intervals: tuple[str, ...] = ()
    required_intervals_for_current_market_reader: tuple[str, ...] = ()
    not_approved: tuple[str, ...] = NOT_APPROVED
    next_stage: str | None = None
    options: tuple[IntervalPreparationOption, ...] = field(default_factory=tuple)
    audit_findings: tuple[IntervalAuditFinding, ...] = field(default_factory=tuple)
    source_audit: str | None = None
    output_json: str | None = None
    output_md: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_DATA_GAPS}


class IntervalPreparationDecisionBuilder:
    def run(self, config: IntervalPreparationDecisionConfig | None = None) -> IntervalPreparationDecisionResult:
        active_config = config or IntervalPreparationDecisionConfig()
        if not active_config.audit_json_path.is_file():
            return IntervalPreparationDecisionResult(
                status=FAIL,
                decision_id="AUDIT_ARTIFACT_MISSING",
                recommended_option="NONE",
                source_audit=active_config.audit_json_path.as_posix(),
                errors=("BOOK-DATA-01 audit artifact is missing. Run book-data-candle-availability-audit first.",),
            )

        try:
            payload = json.loads(active_config.audit_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return IntervalPreparationDecisionResult(
                status=FAIL,
                decision_id="AUDIT_ARTIFACT_INVALID_JSON",
                recommended_option="NONE",
                source_audit=active_config.audit_json_path.as_posix(),
                errors=(f"BOOK-DATA-01 audit artifact is invalid JSON: {exc}",),
            )

        result = build_decision_result(payload, config=active_config)
        if result.status == FAIL:
            return result

        output_json = write_interval_preparation_decision_json(active_config, result)
        output_md = write_interval_preparation_decision_markdown(active_config, result)
        return with_outputs(result, output_json=output_json, output_md=output_md)


class IntervalPreparationDecisionFormatter:
    def format(self, result: IntervalPreparationDecisionResult, *, config: IntervalPreparationDecisionConfig) -> str:
        lines = [
            "BOOK-DATA-02 Interval Data Preparation Decision",
            "",
            "Input:",
            config.audit_json_path.as_posix(),
        ]
        if result.audit_findings:
            lines.extend(["", "Audit summary:"])
            lines.extend(format_audit_finding_line(finding) for finding in result.audit_findings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(result.errors)
        else:
            lines.extend(
                [
                    "",
                    "Decision:",
                    result.decision_id,
                    "",
                    "Recommended option:",
                    result.recommended_option,
                    "",
                    "Immediate action:",
                    immediate_action_text(result),
                    "",
                    "Not approved in this stage:",
                    "- Binance download",
                    "- DB writes",
                    "- 15m to 1h/4h aggregation",
                    "- trading logic",
                    "",
                    "Output files:",
                    result.output_json or config.output_json.as_posix(),
                    result.output_md or config.output_md.as_posix(),
                ]
            )
            if config.show_details:
                lines.extend(["", "Options considered:"])
                lines.extend(f"{option.option_id}: {option.title} ({option.status})" for option in result.options)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def build_decision_result(
    audit_payload: dict[str, Any],
    *,
    config: IntervalPreparationDecisionConfig,
) -> IntervalPreparationDecisionResult:
    rows = tuple(row for row in audit_payload.get("rows", ()) if isinstance(row, dict))
    if not rows:
        return IntervalPreparationDecisionResult(
            status=FAIL,
            decision_id="AUDIT_ARTIFACT_HAS_NO_ROWS",
            recommended_option="NONE",
            source_audit=config.audit_json_path.as_posix(),
            errors=("BOOK-DATA-01 audit artifact has no availability rows.",),
        )

    request = audit_payload.get("request", {})
    requested_intervals = tuple(request.get("intervals", ())) if isinstance(request, dict) else ()
    intervals = tuple(str(interval) for interval in requested_intervals) or intervals_from_rows(rows) or DEFAULT_INTERVALS
    interval_statuses = resolve_interval_statuses(rows, intervals)
    findings = build_audit_findings(rows, intervals, interval_statuses)
    active_intervals = tuple(interval for interval in intervals if interval_statuses.get(interval) == READY)
    missing_intervals = tuple(interval for interval in intervals if interval_statuses.get(interval) != READY)
    optional_intervals = tuple(interval for interval in FUTURE_INTERVALS if interval in missing_intervals)
    status = resolve_decision_status(interval_statuses, strict=config.strict)
    decision_id = resolve_decision_id(active_intervals=active_intervals, missing_intervals=missing_intervals)
    required_now = ("15m",) if "15m" in active_intervals else active_intervals
    warnings = tuple(audit_payload.get("warnings", ())) if isinstance(audit_payload.get("warnings", ()), list) else ()
    errors = tuple(audit_payload.get("errors", ())) if isinstance(audit_payload.get("errors", ()), list) else ()
    if any(status_value == "ERROR" for status_value in interval_statuses.values()) or audit_payload.get("status") == FAIL:
        status = FAIL
    return IntervalPreparationDecisionResult(
        status=status,
        decision_id=decision_id,
        recommended_option=RECOMMENDED_OPTION,
        active_intervals=active_intervals,
        missing_intervals=missing_intervals,
        optional_intervals=optional_intervals,
        required_intervals_for_current_market_reader=required_now,
        next_stage=NEXT_STAGE,
        options=build_options(),
        audit_findings=findings,
        source_audit=config.audit_json_path.as_posix(),
        warnings=warnings,
        errors=errors,
    )


def resolve_interval_statuses(rows: tuple[dict[str, Any], ...], intervals: tuple[str, ...]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for interval in intervals:
        row_statuses = tuple(str(row.get("status", "")) for row in rows if str(row.get("interval", "")) == interval)
        if not row_statuses:
            statuses[interval] = MISSING
        elif all(status == READY for status in row_statuses):
            statuses[interval] = READY
        elif all(status == MISSING for status in row_statuses):
            statuses[interval] = MISSING
        elif any(status == "ERROR" for status in row_statuses):
            statuses[interval] = "ERROR"
        else:
            statuses[interval] = "NOT_READY"
    return statuses


def resolve_decision_status(interval_statuses: dict[str, str], *, strict: bool) -> str:
    if any(status == "ERROR" for status in interval_statuses.values()):
        return FAIL
    if all(status == READY for status in interval_statuses.values()):
        return PASS
    if strict:
        return FAIL
    return PASS_WITH_DATA_GAPS


def resolve_decision_id(*, active_intervals: tuple[str, ...], missing_intervals: tuple[str, ...]) -> str:
    if active_intervals == ("15m",) and set(missing_intervals) == {"1h", "4h"}:
        return DECISION_15M_ONLY
    if not missing_intervals and active_intervals:
        return DECISION_ALL_READY
    if active_intervals:
        return DECISION_READY_WITH_GAPS
    return DECISION_NO_ACTIVE_INTERVAL


def build_audit_findings(
    rows: tuple[dict[str, Any], ...],
    intervals: tuple[str, ...],
    interval_statuses: dict[str, str],
) -> tuple[IntervalAuditFinding, ...]:
    findings: list[IntervalAuditFinding] = []
    for interval in intervals:
        symbols = tuple(
            str(row.get("symbol"))
            for row in rows
            if str(row.get("interval", "")) == interval and row.get("symbol")
        )
        availability = interval_statuses.get(interval, MISSING)
        findings.append(
            IntervalAuditFinding(
                interval=interval,
                availability=availability,
                symbols=tuple(dict.fromkeys(symbols)),
                meaning=availability_meaning(interval, availability),
            )
        )
    return tuple(findings)


def build_options() -> tuple[IntervalPreparationOption, ...]:
    return (
        IntervalPreparationOption(
            option_id="OPTION_A_15M_ONLY_NOW",
            title="Use 15m only for now",
            status="AVAILABLE_NOW",
            recommendation="safe immediate path",
            pros=(
                "already has data",
                "L1-L2 pipeline already works",
                "can continue improving market reading",
                "no DB corruption risk",
                "no incorrect aggregation risk",
            ),
            cons=(
                "no multi-timeframe picture",
                "cannot compare 15m/1h/4h",
                "L2 multi-interval evidence will show gaps",
            ),
        ),
        IntervalPreparationOption(
            option_id="OPTION_B_NATIVE_1H_4H_LOADING_LATER",
            title="Load native 1h/4h later",
            status="FUTURE_STAGE_REQUIRED",
            recommendation="not approved in BOOK-DATA-02",
            pros=("clean native intervals", "simpler coverage checks", "does not depend on resampling quality"),
            cons=(
                "requires separate data loading stage",
                "may require Binance/source integration",
                "cannot be done in BOOK-DATA-02",
            ),
        ),
        IntervalPreparationOption(
            option_id="OPTION_C_AGGREGATE_FROM_15M_LATER",
            title="Build 1h/4h from 15m later",
            status="FUTURE_STAGE_REQUIRED",
            recommendation="requires separate resampling contract",
            pros=("does not require downloading additional intervals", "can derive multi-interval data from existing 15m"),
            cons=(
                "requires strict resampling contract",
                "must verify open/high/low/close/volume",
                "must verify time boundaries",
                "needs tests for incomplete candles",
                "cannot be done in BOOK-DATA-02",
            ),
        ),
        IntervalPreparationOption(
            option_id=RECOMMENDED_OPTION,
            title="Use 15m now, decide 1h/4h preparation later",
            status="RECOMMENDED",
            recommendation="recommended for current project state",
            pros=(
                "does not block current progress",
                "preserves safe architecture",
                "defers technical risk",
            ),
            cons=("decision for 1h/4h is deferred", "requires next data preparation plan"),
        ),
    )


def build_json_payload(result: IntervalPreparationDecisionResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "source_audit": result.source_audit,
        "decision": {
            "decision_id": result.decision_id,
            "recommended_option": result.recommended_option,
            "active_intervals": list(result.active_intervals),
            "missing_intervals": list(result.missing_intervals),
            "optional_intervals": list(result.optional_intervals),
            "required_intervals_for_current_market_reader": list(result.required_intervals_for_current_market_reader),
            "not_approved": list(result.not_approved),
            "next_stage": result.next_stage,
        },
        "audit_finding": [asdict(finding) for finding in result.audit_findings],
        "options": [asdict(option) for option in result.options],
        "safety": build_safety_payload(),
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def build_safety_payload() -> dict[str, Any]:
    return {
        "read_only": True,
        "download_approved": False,
        "db_write_approved": False,
        "aggregation_approved": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
    }


def write_interval_preparation_decision_json(
    config: IntervalPreparationDecisionConfig,
    result: IntervalPreparationDecisionResult,
) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def build_markdown(result: IntervalPreparationDecisionResult) -> str:
    lines = [
        "# BOOK-DATA-02 - Interval Data Preparation Decision",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Source",
        "",
        f"`{result.source_audit}`",
        "",
        "## Audit Finding",
        "",
        "| Interval | Availability | Meaning |",
        "|---|---|---|",
        *[
            f"| {_md(finding.interval)} | {_md(finding.availability)} | {_md(finding.meaning)} |"
            for finding in result.audit_findings
        ],
        "",
        "## Decision",
        "",
        f"`{result.decision_id}`",
        "",
        "## Recommended Option",
        "",
        f"`{result.recommended_option}`",
        "",
        "## Immediate Action",
        "",
        immediate_action_text(result),
        "",
        "## Required Intervals For Current Market Reader",
        "",
        "| Interval | Required Now | Status |",
        "|---|---|---|",
        *required_interval_rows(result),
        "",
        "## Options Considered",
        "",
    ]
    for option in result.options:
        lines.extend(format_option_markdown(option))
    lines.extend(
        [
            "## Not Approved In This Stage",
            "",
            "- Binance download",
            "- DB writes",
            "- 15m to 1h/4h aggregation",
            "- Trading logic",
            "- LONG/SHORT recommendations",
            "- Edge validation",
            "",
            "## Next Stage",
            "",
            f"`{result.next_stage}`",
            "",
            "Possible scope:",
            "",
            "- native 1h/4h loading plan;",
            "- or 15m to 1h/4h aggregation contract;",
            "- or explicitly keep 15m-only until Market Reader quality improves.",
            "",
            "## Safety",
            "",
            "- read_only: `true`",
            "- download_approved: `false`",
            "- db_write_approved: `false`",
            "- aggregation_approved: `false`",
            "- trading_signal: `NOT_EVALUATED`",
            "- safe_for_runtime_trading: `false`",
            "",
            "## Conclusion",
            "",
            conclusion_text(result),
            "",
        ]
    )
    return "\n".join(lines)


def write_interval_preparation_decision_markdown(
    config: IntervalPreparationDecisionConfig,
    result: IntervalPreparationDecisionResult,
) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(result), encoding="utf-8")
    return config.output_md


def with_outputs(
    result: IntervalPreparationDecisionResult,
    *,
    output_json: Path,
    output_md: Path,
) -> IntervalPreparationDecisionResult:
    return IntervalPreparationDecisionResult(
        status=result.status,
        decision_id=result.decision_id,
        recommended_option=result.recommended_option,
        active_intervals=result.active_intervals,
        missing_intervals=result.missing_intervals,
        optional_intervals=result.optional_intervals,
        required_intervals_for_current_market_reader=result.required_intervals_for_current_market_reader,
        not_approved=result.not_approved,
        next_stage=result.next_stage,
        options=result.options,
        audit_findings=result.audit_findings,
        source_audit=result.source_audit,
        output_json=output_json.as_posix(),
        output_md=output_md.as_posix(),
        warnings=result.warnings,
        errors=result.errors,
    )


def format_audit_finding_line(finding: IntervalAuditFinding) -> str:
    symbols = ", ".join(finding.symbols) if finding.symbols else "no audited symbols"
    return f"{finding.interval}: {finding.availability} for {symbols}"


def immediate_action_text(result: IntervalPreparationDecisionResult) -> str:
    if result.active_intervals == ("15m",):
        return "Use 15m as active working interval for BOOK-L1 Market Reader."
    if result.active_intervals:
        return f"Use {', '.join(result.active_intervals)} as active working intervals for BOOK-L1 Market Reader."
    return "Do not promote any interval to active working status until data is prepared."


def conclusion_text(result: IntervalPreparationDecisionResult) -> str:
    if result.decision_id == DECISION_15M_ONLY:
        return (
            "The current Market Reader workflow should continue on `15m`.\n"
            "Missing `1h` and `4h` data should not block BOOK-L1/BOOK-L2 progress.\n"
            "Preparation of `1h` and `4h` requires a separate explicit stage."
        )
    if result.status == PASS:
        return (
            "All audited intervals are ready in the current audit artifact.\n"
            "No download, DB write, aggregation, or trading logic is approved by this stage.\n"
            "Any change to interval requirements still requires a separate explicit BOOK-DATA stage."
        )
    return (
        "The current audit artifact still contains data gaps.\n"
        "Only ready intervals may be treated as active working intervals.\n"
        "Preparation of missing intervals requires a separate explicit BOOK-DATA stage."
    )


def required_interval_rows(result: IntervalPreparationDecisionResult) -> list[str]:
    statuses = {finding.interval: finding.availability for finding in result.audit_findings}
    intervals = tuple(statuses) or DEFAULT_INTERVALS
    required = set(result.required_intervals_for_current_market_reader)
    return [
        f"| {_md(interval)} | {'yes' if interval in required else 'no'} | {_md(statuses.get(interval, MISSING))} |"
        for interval in intervals
    ]


def format_option_markdown(option: IntervalPreparationOption) -> list[str]:
    lines = [
        f"### {_option_heading(option)}",
        "",
        f"- Status: `{option.status}`",
        f"- Recommendation: `{option.recommendation}`",
        "",
        "Pros:",
        "",
        *[f"- {_md(pro)}" for pro in option.pros],
        "",
        "Cons:",
        "",
        *[f"- {_md(con)}" for con in option.cons],
        "",
    ]
    return lines


def availability_meaning(interval: str, availability: str) -> str:
    if availability == READY and interval == "15m":
        return "Can be used now for BOOK-L1 Market Reader"
    if availability == READY:
        return "Available in local audit artifact"
    if availability == MISSING:
        return "Not available in local DB"
    return "Not ready for current Market Reader workflow"


def intervals_from_rows(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(row.get("interval")) for row in rows if row.get("interval")))


def _option_heading(option: IntervalPreparationOption) -> str:
    labels = {
        "OPTION_A_15M_ONLY_NOW": "Option A - 15m only for now",
        "OPTION_B_NATIVE_1H_4H_LOADING_LATER": "Option B - Native 1h/4h loading later",
        "OPTION_C_AGGREGATE_FROM_15M_LATER": "Option C - Build 1h/4h from 15m later",
        "OPTION_D_HYBRID_LATER": "Option D - Hybrid later",
    }
    return labels.get(option.option_id, option.title)


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "CONTRACT_VERSION",
    "DECISION_15M_ONLY",
    "FAIL",
    "NOT_APPROVED",
    "PASS",
    "PASS_WITH_DATA_GAPS",
    "RECOMMENDED_OPTION",
    "IntervalPreparationDecisionBuilder",
    "IntervalPreparationDecisionConfig",
    "IntervalPreparationDecisionFormatter",
    "IntervalPreparationDecisionResult",
    "IntervalPreparationOption",
    "build_decision_result",
    "build_json_payload",
    "build_markdown",
    "build_safety_payload",
    "write_interval_preparation_decision_json",
    "write_interval_preparation_decision_markdown",
]
