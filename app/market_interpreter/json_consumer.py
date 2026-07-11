from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_L2_CONTEXT_PATH = Path("reports/book_l2/timeline_context.json")
EXPECTED_L2_CONTRACT_VERSION = "book_l2_timeline_context_v1"
EXPECTED_L2_SERVICE = "BOOK_L2_MARKET_INTERPRETER"
EXPECTED_L2_REPORT_TYPE = "timeline_context"
EXPECTED_L1_SOURCE_PATH = "reports/book_l1/timeline_preview.json"
EXPECTED_L1_SERVICE = "BOOK_L1_MARKET_READER"

FORBIDDEN_L2_CONSUMER_TERMS = (
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
    "SIGNAL",
    "TRADE CANDIDATE",
    "ENTRY CANDIDATE",
)

REQUIRED_TOP_LEVEL_KEYS = (
    "status",
    "service",
    "report_type",
    "contract_version",
    "source_report",
    "source",
    "result",
    "safety",
    "warnings",
    "errors",
)

REQUIRED_RESULT_KEYS = (
    "overall_state",
    "symbols",
    "summary",
    "market_context",
    "market_brief",
)

REQUIRED_SYMBOL_KEYS = (
    "symbol",
    "bucket",
    "skip_candidate",
    "context_reason_codes",
    "context_quality_score",
    "context_quality_grade",
    "context_rank",
    "context_quality_reason_codes",
)

REQUIRED_MARKET_BRIEF_KEYS = (
    "overall_state",
    "brief_state",
    "observation_candidates",
    "skip_candidates",
    "key_points",
    "safety_note",
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
class L2ContextConsumerConfig:
    input_path: Path = DEFAULT_L2_CONTEXT_PATH
    strict: bool = False
    show_details: bool = False


@dataclass(frozen=True)
class L2ContextConsumerCheck:
    name: str
    status: str
    message: str
    severity: str = "INFO"


@dataclass(frozen=True)
class L2ContextConsumerResult:
    status: str
    input_path: str
    contract_version: str | None
    service: str | None
    overall_state: str | None
    symbol_count: int
    observation_candidate_count: int
    skip_candidate_count: int
    checks: tuple[L2ContextConsumerCheck, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    symbols: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False)
    market_brief: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


class L2ContextJsonConsumer:
    def run(self, config: L2ContextConsumerConfig) -> L2ContextConsumerResult:
        input_path = config.input_path
        checks: list[L2ContextConsumerCheck] = []

        if not input_path.exists():
            checks.append(_check("file_exists", "FAIL", "L2 context JSON file not found."))
            return _build_result(input_path=input_path, checks=checks, errors=("L2 context JSON file not found",))

        checks.append(_check("file_exists", "PASS", "File exists."))

        try:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append(_check("valid_json", "FAIL", f"invalid JSON: {exc.msg}"))
            return _build_result(input_path=input_path, checks=checks, errors=(f"invalid JSON: {exc.msg}",))
        except OSError as exc:
            checks.append(_check("valid_json", "FAIL", f"read error: {exc}"))
            return _build_result(input_path=input_path, checks=checks, errors=(f"read error: {exc}",))

        if not isinstance(payload, dict):
            checks.append(_check("valid_json", "FAIL", "Top-level JSON value must be an object."))
            return _build_result(input_path=input_path, checks=checks, errors=("top-level JSON value must be an object",))

        checks.append(_check("valid_json", "PASS", "JSON is valid."))

        result_payload = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        symbols = result_payload.get("symbols") if isinstance(result_payload, dict) else None
        market_brief = result_payload.get("market_brief") if isinstance(result_payload, dict) else None
        symbol_rows = tuple(symbol for symbol in symbols if isinstance(symbol, dict)) if isinstance(symbols, list) else ()
        brief_payload = market_brief if isinstance(market_brief, dict) else None

        validators = (
            _validate_top_level(payload),
            _validate_contract_version(payload),
            _validate_l2_service(payload),
            _validate_source(payload),
            _validate_result_shape(payload),
            _validate_overall_state(result_payload),
            _validate_symbols(symbols),
            _validate_ranking(symbol_rows),
            _validate_market_brief(market_brief),
            _validate_forbidden_brief_terms(brief_payload),
            _validate_safety(payload.get("safety")),
            _validate_warnings_and_errors(payload, strict=config.strict),
        )
        for group in validators:
            checks.extend(group)

        warnings = tuple(
            check.message
            for check in checks
            if check.status == "WARN"
        )
        errors = tuple(
            check.message
            for check in checks
            if check.status == "FAIL"
        )
        if errors:
            status = "FAIL"
        elif warnings:
            status = "FAIL" if config.strict else "PASS_WITH_WARNINGS"
        else:
            status = "PASS"

        return L2ContextConsumerResult(
            status=status,
            input_path=input_path.as_posix(),
            contract_version=_optional_text(payload.get("contract_version")),
            service=_optional_text(payload.get("service") or payload.get("layer")),
            overall_state=_optional_text(result_payload.get("overall_state")) if isinstance(result_payload, dict) else None,
            symbol_count=len(symbol_rows),
            observation_candidate_count=_candidate_count(brief_payload, "observation_candidates"),
            skip_candidate_count=_candidate_count(brief_payload, "skip_candidates"),
            checks=tuple(checks),
            warnings=warnings,
            errors=errors,
            symbols=symbol_rows,
            market_brief=brief_payload,
        )


class L2ContextConsumerFormatter:
    def format(self, result: L2ContextConsumerResult, *, show_details: bool = False) -> str:
        lines = [
            "BOOK-L2 JSON Consumer Smoke",
            "",
            "Input:",
            result.input_path,
            "",
            "Contract:",
            f"Service: {result.service or 'n/a'}",
            f"Contract version: {result.contract_version or 'n/a'}",
            f"Overall state: {result.overall_state or 'n/a'}",
            f"Symbols: {result.symbol_count}",
            f"Observation candidates: {result.observation_candidate_count}",
            f"Skip candidates: {result.skip_candidate_count}",
            "",
            "Checks:",
            _format_checks_table(result.checks),
        ]

        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        if show_details:
            lines.extend(["", self._format_details(result)])

        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)

    def to_json_payload(self, result: L2ContextConsumerResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "input_path": result.input_path,
            "service": result.service,
            "contract_version": result.contract_version,
            "overall_state": result.overall_state,
            "symbol_count": result.symbol_count,
            "observation_candidate_count": result.observation_candidate_count,
            "skip_candidate_count": result.skip_candidate_count,
            "checks": [asdict(check) for check in result.checks],
            "warnings": list(result.warnings),
            "errors": list(result.errors),
        }

    @staticmethod
    def _format_details(result: L2ContextConsumerResult) -> str:
        lines = ["Details:", "", "Symbols:"]
        if result.symbols:
            for symbol in result.symbols:
                lines.append(
                    "- "
                    f"{symbol.get('symbol', 'n/a')}: "
                    f"bucket={symbol.get('bucket', 'n/a')}, "
                    f"grade={symbol.get('context_quality_grade', 'n/a')}, "
                    f"rank={_format_rank(symbol.get('context_rank'))}, "
                    f"skip={_format_bool_or_value(symbol.get('skip_candidate', 'n/a'))}"
                )
        else:
            lines.append("- none")

        brief = result.market_brief or {}
        lines.extend(
            [
                "",
                "Market brief:",
                f"Brief: {brief.get('brief', brief.get('brief_state', 'n/a'))}",
                f"Observation candidates: {_format_candidate_symbols(brief.get('observation_candidates'))}",
                f"Skip candidates: {_format_candidate_symbols(brief.get('skip_candidates'))}",
                "Key points:",
            ]
        )
        key_points = brief.get("key_points")
        if isinstance(key_points, list) and key_points:
            lines.extend(f"- {point}" for point in key_points)
        else:
            lines.append("- none")
        lines.extend(["Safety note:", str(brief.get("safety_note", "n/a"))])
        return "\n".join(lines)


def _validate_top_level(payload: dict[str, Any]) -> tuple[L2ContextConsumerCheck, ...]:
    errors = [f"missing top-level key: {key}" for key in REQUIRED_TOP_LEVEL_KEYS if key not in payload]
    if "source" in payload and not isinstance(payload.get("source"), dict):
        errors.append("source must be an object")
    if "result" in payload and not isinstance(payload.get("result"), dict):
        errors.append("result must be an object")
    if "safety" in payload and not isinstance(payload.get("safety"), dict):
        errors.append("safety must be an object")
    return (_check("top_level_keys", "FAIL", "; ".join(errors)),) if errors else (_check("top_level_keys", "PASS", "Required top-level keys are present."),)


def _validate_contract_version(payload: dict[str, Any]) -> tuple[L2ContextConsumerCheck, ...]:
    if payload.get("contract_version") != EXPECTED_L2_CONTRACT_VERSION:
        return (_check("contract_version", "FAIL", f"contract_version must be {EXPECTED_L2_CONTRACT_VERSION}"),)
    return (_check("contract_version", "PASS", "Contract version matches BOOK-L2 context contract."),)


def _validate_l2_service(payload: dict[str, Any]) -> tuple[L2ContextConsumerCheck, ...]:
    service = payload.get("service")
    layer = payload.get("layer")
    if service == "BOOK_L1_MARKET_READER" or layer == "BOOK_L1":
        return (_check("l2_service", "FAIL", "payload belongs to BOOK-L1, expected BOOK-L2"),)
    if service != EXPECTED_L2_SERVICE and layer != "BOOK_L2":
        return (_check("l2_service", "FAIL", f"service must be {EXPECTED_L2_SERVICE} or layer must be BOOK_L2"),)
    return (_check("l2_service", "PASS", "Payload belongs to BOOK-L2."),)


def _validate_source(payload: dict[str, Any]) -> tuple[L2ContextConsumerCheck, ...]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    source_report = _path_text(payload.get("source_report"))
    source_input = _path_text(source.get("input_path"))
    source_service = source.get("service")
    paths = {source_report, source_input}
    if EXPECTED_L1_SOURCE_PATH not in paths:
        return (_check("source_is_l1_timeline", "FAIL", f"source must be {EXPECTED_L1_SOURCE_PATH}"),)
    if source_service not in (None, EXPECTED_L1_SERVICE):
        return (_check("source_is_l1_timeline", "FAIL", f"source.service must be {EXPECTED_L1_SERVICE}"),)
    return (_check("source_is_l1_timeline", "PASS", "Source is BOOK-L1 timeline JSON."),)


def _validate_result_shape(payload: dict[str, Any]) -> tuple[L2ContextConsumerCheck, ...]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return (_check("result_shape", "FAIL", "result must be an object"),)
    errors = [f"missing result key: {key}" for key in REQUIRED_RESULT_KEYS if key not in result]
    if "summary" in result and not isinstance(result.get("summary"), dict):
        errors.append("result.summary must be an object")
    if "market_context" in result and not isinstance(result.get("market_context"), dict):
        errors.append("result.market_context must be an object")
    return (_check("result_shape", "FAIL", "; ".join(errors)),) if errors else (_check("result_shape", "PASS", "Result context keys are present."),)


def _validate_overall_state(result: Any) -> tuple[L2ContextConsumerCheck, ...]:
    if not isinstance(result, dict):
        return (_check("overall_state", "FAIL", "result must be an object"),)
    overall_state = result.get("overall_state")
    if not isinstance(overall_state, str) or not overall_state.strip():
        return (_check("overall_state", "FAIL", "overall_state must be a non-empty string"),)
    return (_check("overall_state", "PASS", "Overall state is present."),)


def _validate_symbols(symbols: Any) -> tuple[L2ContextConsumerCheck, ...]:
    if not isinstance(symbols, list):
        return (_check("symbols_schema", "FAIL", "symbols must be a list"),)
    errors: list[str] = []
    for index, symbol in enumerate(symbols):
        if not isinstance(symbol, dict):
            errors.append(f"symbols[{index}] must be an object")
            continue
        for key in REQUIRED_SYMBOL_KEYS:
            if key not in symbol:
                errors.append(f"{_symbol_label(symbol, index)}: missing {key}")
        _validate_symbol_value(symbol, index=index, errors=errors)
    return (_check("symbols_schema", "FAIL", "; ".join(errors)),) if errors else (_check("symbols_schema", "PASS", "Symbols schema is valid."),)


def _validate_symbol_value(symbol: dict[str, Any], *, index: int, errors: list[str]) -> None:
    label = _symbol_label(symbol, index)
    if "symbol" in symbol and (not isinstance(symbol.get("symbol"), str) or not symbol.get("symbol", "").strip()):
        errors.append(f"{label}: symbol must be a non-empty string")
    if "bucket" in symbol and (not isinstance(symbol.get("bucket"), str) or not symbol.get("bucket", "").strip()):
        errors.append(f"{label}: bucket must be a non-empty string")
    if "skip_candidate" in symbol and not isinstance(symbol.get("skip_candidate"), bool):
        errors.append(f"{label}: skip_candidate must be a bool")
    if "context_reason_codes" in symbol and not isinstance(symbol.get("context_reason_codes"), list):
        errors.append(f"{label}: context_reason_codes must be a list")
    if "context_quality_reason_codes" in symbol and not isinstance(symbol.get("context_quality_reason_codes"), list):
        errors.append(f"{label}: context_quality_reason_codes must be a list")
    score = symbol.get("context_quality_score")
    if "context_quality_score" in symbol and (not isinstance(score, int | float) or isinstance(score, bool) or not 0.0 <= float(score) <= 1.0):
        errors.append(f"{label}: context_quality_score must be a number from 0.0 to 1.0")
    if "context_quality_grade" in symbol and (not isinstance(symbol.get("context_quality_grade"), str) or not symbol.get("context_quality_grade", "").strip()):
        errors.append(f"{label}: context_quality_grade must be a non-empty string")
    if symbol.get("skip_candidate") is False:
        rank = symbol.get("context_rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank < 1:
            errors.append(f"{label}: context_rank must be an int >= 1 for non-skip symbols")


def _validate_ranking(symbols: tuple[dict[str, Any], ...]) -> tuple[L2ContextConsumerCheck, ...]:
    ranks: list[int] = []
    for index, symbol in enumerate(symbols):
        if symbol.get("skip_candidate") is True:
            continue
        rank = symbol.get("context_rank")
        if not isinstance(rank, int) or isinstance(rank, bool):
            return (_check("ranking_consistency", "FAIL", f"{_symbol_label(symbol, index)}: context_rank must be an int"),)
        if rank < 1:
            return (_check("ranking_consistency", "FAIL", f"{_symbol_label(symbol, index)}: context_rank must be >= 1"),)
        ranks.append(rank)
    if not ranks:
        return (_check("ranking_consistency", "PASS", "No rankable symbols; skip rows are unranked."),)
    expected = list(range(1, len(ranks) + 1))
    if sorted(ranks) != expected or len(set(ranks)) != len(ranks):
        return (_check("ranking_consistency", "FAIL", "context_rank values must cover 1..N without gaps or duplicates"),)
    return (_check("ranking_consistency", "PASS", "Ranking is contiguous and deterministic."),)


def _validate_market_brief(market_brief: Any) -> tuple[L2ContextConsumerCheck, ...]:
    if not isinstance(market_brief, dict):
        return (_check("market_brief_schema", "FAIL", "market_brief must be an object"),)
    errors = [f"missing market_brief key: {key}" for key in REQUIRED_MARKET_BRIEF_KEYS if key not in market_brief]
    if "brief" in market_brief and not isinstance(market_brief.get("brief"), str):
        errors.append("market_brief.brief must be a string")
    if "brief_state" in market_brief and (not isinstance(market_brief.get("brief_state"), str) or not market_brief.get("brief_state", "").strip()):
        errors.append("market_brief.brief_state must be a non-empty string")
    for key in ("observation_candidates", "skip_candidates", "key_points"):
        if key in market_brief and not isinstance(market_brief.get(key), list):
            errors.append(f"market_brief.{key} must be a list")
    if "safety_note" in market_brief and not isinstance(market_brief.get("safety_note"), str):
        errors.append("market_brief.safety_note must be a string")
    return (_check("market_brief_schema", "FAIL", "; ".join(errors)),) if errors else (_check("market_brief_schema", "PASS", "Market brief schema is valid."),)


def _validate_forbidden_brief_terms(market_brief: dict[str, Any] | None) -> tuple[L2ContextConsumerCheck, ...]:
    if market_brief is None:
        return (_check("forbidden_brief_terms", "FAIL", "market_brief is required", severity="SAFETY"),)
    text_parts = _brief_text_parts(market_brief)
    matches: list[str] = []
    for text in text_parts:
        matches.extend(_forbidden_terms_in_text(text))
    if matches:
        unique_matches = ", ".join(dict.fromkeys(matches))
        return (_check("forbidden_brief_terms", "FAIL", f"market_brief contains forbidden term(s): {unique_matches}", severity="SAFETY"),)
    return (_check("forbidden_brief_terms", "PASS", "Market brief has no forbidden trading terms.", severity="SAFETY"),)


def _validate_safety(safety: Any) -> tuple[L2ContextConsumerCheck, ...]:
    if not isinstance(safety, dict):
        return (_check("fail_closed_safety", "FAIL", "safety must be an object", severity="SAFETY"),)
    errors: list[str] = []
    for field_name, expected in EXPECTED_SAFETY_FIELDS.items():
        if field_name not in safety:
            errors.append(f"missing safety field: {field_name}")
        elif safety[field_name] != expected:
            errors.append(f"safety.{field_name} must be {_format_bool_or_value(expected)}")
    if "observe_only" in safety and safety.get("observe_only") is not True:
        errors.append("safety.observe_only must be true")
    return (_check("fail_closed_safety", "FAIL", "; ".join(errors), severity="SAFETY"),) if errors else (_check("fail_closed_safety", "PASS", "Safety is fail-closed.", severity="SAFETY"),)


def _validate_warnings_and_errors(payload: dict[str, Any], *, strict: bool) -> tuple[L2ContextConsumerCheck, ...]:
    warnings = payload.get("warnings")
    errors = payload.get("errors")
    messages: list[str] = []
    if not isinstance(warnings, list):
        messages.append("warnings must be a list")
    if not isinstance(errors, list):
        messages.append("errors must be a list")
    if messages:
        return (_check("warnings_errors", "FAIL", "; ".join(messages)),)
    if errors:
        return (_check("warnings_errors", "FAIL", "errors must be empty"),)
    if warnings:
        status = "FAIL" if strict else "WARN"
        return (_check("warnings_errors", status, "warnings are present"),)
    return (_check("warnings_errors", "PASS", "Warnings and errors are empty."),)


def _build_result(
    *,
    input_path: Path,
    checks: list[L2ContextConsumerCheck],
    errors: tuple[str, ...],
) -> L2ContextConsumerResult:
    return L2ContextConsumerResult(
        status="FAIL",
        input_path=input_path.as_posix(),
        contract_version=None,
        service=None,
        overall_state=None,
        symbol_count=0,
        observation_candidate_count=0,
        skip_candidate_count=0,
        checks=tuple(checks),
        errors=errors,
    )


def _check(name: str, status: str, message: str, *, severity: str = "INFO") -> L2ContextConsumerCheck:
    return L2ContextConsumerCheck(name=name, status=status, message=message, severity=severity)


def _candidate_count(brief: dict[str, Any] | None, key: str) -> int:
    if brief is None:
        return 0
    value = brief.get(key)
    return len(value) if isinstance(value, list) else 0


def _brief_text_parts(brief: dict[str, Any]) -> tuple[str, ...]:
    parts: list[str] = []
    for key in ("brief", "brief_state", "safety_note"):
        value = brief.get(key)
        if isinstance(value, str):
            parts.append(value)
    key_points = brief.get("key_points")
    if isinstance(key_points, list):
        parts.extend(str(point) for point in key_points)
    for key in ("observation_candidates", "skip_candidates"):
        candidates = brief.get(key)
        if isinstance(candidates, list):
            for candidate in candidates:
                if isinstance(candidate, dict):
                    reason = candidate.get("main_reason")
                    if isinstance(reason, str):
                        parts.append(reason)
    return tuple(parts)


def _forbidden_terms_in_text(text: str) -> tuple[str, ...]:
    matches: list[str] = []
    normalized = text.replace("_", " ")
    for term in FORBIDDEN_L2_CONSUMER_TERMS:
        pattern = r"(?<![A-Z0-9])" + re.escape(term).replace(r"\ ", r"[\s_]+") + r"(?![A-Z0-9])"
        if re.search(pattern, normalized.upper()):
            matches.append(term)
    return tuple(matches)


def _format_checks_table(checks: tuple[L2ContextConsumerCheck, ...]) -> str:
    headers = ("Check", "Status", "Severity")
    rows = tuple((check.name, check.status, check.severity) for check in checks)
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


def _format_candidate_symbols(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    symbols = [str(item.get("symbol", "n/a")) if isinstance(item, dict) else str(item) for item in value]
    return ", ".join(symbols)


def _format_rank(value: Any) -> str:
    return str(value) if value is not None else "-"


def _format_bool_or_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _path_text(value: Any) -> str:
    return str(value).replace("\\", "/") if value is not None else ""


def _symbol_label(symbol: dict[str, Any], index: int) -> str:
    value = symbol.get("symbol")
    if isinstance(value, str) and value.strip():
        return value
    return f"symbols[{index}]"


__all__ = [
    "DEFAULT_L2_CONTEXT_PATH",
    "EXPECTED_L2_CONTRACT_VERSION",
    "EXPECTED_L2_SERVICE",
    "FORBIDDEN_L2_CONSUMER_TERMS",
    "L2ContextConsumerConfig",
    "L2ContextConsumerCheck",
    "L2ContextConsumerResult",
    "L2ContextJsonConsumer",
    "L2ContextConsumerFormatter",
]
