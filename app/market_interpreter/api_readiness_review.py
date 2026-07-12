from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.market_interpreter.json_consumer import (
    L2ContextConsumerConfig,
    L2ContextJsonConsumer,
)


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
LAYER_NAME = "BOOK_L2_MARKET_INTERPRETER"

REQUIRED_L2_MODULES = (
    "app/market_interpreter/__init__.py",
    "app/market_interpreter/context_rules.py",
    "app/market_interpreter/context_quality.py",
    "app/market_interpreter/context_summary.py",
    "app/market_interpreter/flat_context_handling.py",
    "app/market_interpreter/json_consumer.py",
    "app/market_interpreter/l1_timeline_consumer.py",
)

REQUIRED_L2_TESTS = (
    "tests/test_book_l2_timeline_context.py",
    "tests/test_book_l2_context_rules.py",
    "tests/test_book_l2_context_quality.py",
    "tests/test_book_l2_context_summary.py",
    "tests/test_book_l2_flat_context_handling.py",
    "tests/test_book_l2_json_consumer.py",
    "tests/test_book_l2_api_readiness_review.py",
)

REQUIRED_CLI_COMMANDS = (
    "book-l2-timeline-context",
    "book-l2-flat-context-handling-implementation",
    "book-l2-json-consumer-smoke",
    "book-l2-api-readiness-review",
)

REQUIRED_GUIDE_COMMANDS = (
    "book-l2-timeline-context",
    "book-l2-flat-context-handling-implementation",
    "book-l2-json-consumer-smoke",
    "book-l2-api-readiness-review",
)

REQUIRED_PLANNING_FILES = (
    "planning/01_CURRENT_STATE.md",
    "planning/02_CURRENT_TASK.md",
    "planning/03_REMAINING_WORK.md",
    "planning/07_BOOK_L2_MARKET_INTERPRETER_PLAN.md",
)

REQUIRED_STAGE_REPORT_PREFIXES = (
    "book_l2_00_",
    "book_l2_01_",
    "book_l2_02_",
    "book_l2_03_",
    "book_l2_04_",
)

REQUIRED_TOP_LEVEL_KEYS = (
    "contract_version",
    "service",
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
    "market_brief",
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

FORBIDDEN_RUNTIME_TERMS = (
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

FORBIDDEN_L2_SOURCE_TERMS = (
    "Candle" + "Repository",
    "Market" + "Reader" + "Orchestrator",
    "Market" + "Candles",
    "Bin" + "ance",
    "down" + "load",
    "create" + "_order",
    "place" + "_order",
)

PLANNING_FREEZE_MARKERS = (
    "BOOK-L2-05 completed API readiness final review",
    "BOOK-L2 is now Layer 2 Freeze Candidate",
    "consume-only",
    "observe-only",
    "fail-closed",
)


@dataclass(frozen=True)
class L2ApiReadinessConfig:
    project_root: Path = Path(".")
    l1_timeline_path: Path = Path("reports/book_l1/timeline_preview.json")
    l2_context_path: Path = Path("reports/book_l2/timeline_context.json")
    strict: bool = False
    show_details: bool = False


@dataclass(frozen=True)
class L2ApiReadinessCheck:
    name: str
    status: str
    severity: str
    message: str


@dataclass(frozen=True)
class L2ApiReadinessResult:
    status: str
    freeze_candidate: bool
    checks: tuple[L2ApiReadinessCheck, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    layer: str = LAYER_NAME
    input_path: str = "reports/book_l1/timeline_preview.json"
    output_path: str = "reports/book_l2/timeline_context.json"
    details: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def passed(self) -> bool:
        return self.status == PASS


class L2ApiReadinessReviewer:
    def run(self, config: L2ApiReadinessConfig) -> L2ApiReadinessResult:
        project_root = config.project_root
        l1_path = _resolve(project_root, config.l1_timeline_path)
        l2_path = _resolve(project_root, config.l2_context_path)
        payload = _read_json(l2_path)

        checks = (
            self._check_l2_modules(project_root),
            self._check_l2_tests(project_root, strict=config.strict),
            self._check_cli_commands(project_root),
            self._check_l1_timeline_input(l1_path, config=config),
            self._check_l2_context_export(l2_path, config=config),
            self._check_l2_json_consumer(l2_path),
            self._check_contract(payload),
            self._check_fail_closed_safety(payload),
            self._check_observe_only_constraints(payload),
            self._check_forbidden_l2_source_terms(project_root),
            self._check_stable_output_file_policy(project_root, config=config),
            self._check_guide_updated(project_root),
            self._check_planning_updated(project_root, strict=config.strict),
            self._check_stage_reports_exist(project_root, strict=config.strict),
        )

        errors = tuple(check.message for check in checks if check.status == FAIL)
        warnings = tuple(check.message for check in checks if check.status == WARN)
        if errors:
            status = FAIL
        elif warnings:
            status = FAIL if config.strict else PASS_WITH_WARNINGS
        else:
            status = PASS

        safety_pass = _check_status(checks, "fail_closed_safety", PASS) and _check_status(checks, "observe_only_constraints", PASS)
        source_pass = _check_status(checks, "forbidden_imports", PASS)
        consumer_pass = _check_status(checks, "l2_json_consumer_strict", PASS)
        freeze_candidate = status == PASS and not errors and safety_pass and source_pass and consumer_pass

        details = self._build_details(project_root=project_root, payload=payload.value, checks=checks)
        return L2ApiReadinessResult(
            status=status,
            freeze_candidate=freeze_candidate,
            checks=checks,
            warnings=warnings,
            errors=errors,
            input_path=config.l1_timeline_path.as_posix(),
            output_path=config.l2_context_path.as_posix(),
            details=details,
        )

    @staticmethod
    def _check_l2_modules(project_root: Path) -> L2ApiReadinessCheck:
        missing = _missing_files(project_root, REQUIRED_L2_MODULES)
        if missing:
            return _check("l2_modules_exist", FAIL, "API", f"Missing required L2 module(s): {', '.join(missing)}")
        return _check("l2_modules_exist", PASS, "INFO", "Required L2 modules exist.")

    @staticmethod
    def _check_l2_tests(project_root: Path, *, strict: bool) -> L2ApiReadinessCheck:
        missing = _missing_files(project_root, REQUIRED_L2_TESTS)
        if missing:
            status = FAIL if strict else WARN
            return _check("l2_tests_exist", status, "TESTS", f"Missing required L2 test file(s): {', '.join(missing)}")
        return _check("l2_tests_exist", PASS, "INFO", "Required L2 tests exist.")

    @staticmethod
    def _check_cli_commands(project_root: Path) -> L2ApiReadinessCheck:
        path = project_root / "app/cli/commands.py"
        if not path.is_file():
            return _check("cli_commands", FAIL, "API", "Missing app/cli/commands.py.")
        source = _read_text(path)
        if source.error:
            return _check("cli_commands", FAIL, "API", source.error)
        missing = tuple(command for command in REQUIRED_CLI_COMMANDS if f'@cli.command("{command}")' not in source.value)
        if missing:
            return _check("cli_commands", FAIL, "API", f"Missing L2 CLI command(s): {', '.join(missing)}")
        return _check("cli_commands", PASS, "API", "Required L2 CLI commands are registered.")

    @staticmethod
    def _check_l1_timeline_input(path: Path, *, config: L2ApiReadinessConfig) -> L2ApiReadinessCheck:
        if not path.is_file():
            return _check("l1_timeline_input_exists", FAIL, "API", f"Missing L1 timeline input: {config.l1_timeline_path.as_posix()}")
        return _check("l1_timeline_input_exists", PASS, "INFO", "L1 timeline input exists.")

    @staticmethod
    def _check_l2_context_export(path: Path, *, config: L2ApiReadinessConfig) -> L2ApiReadinessCheck:
        if not path.is_file():
            return _check("l2_context_export_exists", FAIL, "API", f"Missing L2 context export: {config.l2_context_path.as_posix()}")
        return _check("l2_context_export_exists", PASS, "INFO", "L2 context export exists.")

    @staticmethod
    def _check_l2_json_consumer(path: Path) -> L2ApiReadinessCheck:
        result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=path, strict=True))
        if not result.passed:
            message = "; ".join(result.errors or result.warnings or ("L2 JSON consumer did not pass.",))
            return _check("l2_json_consumer_strict", FAIL, "API", message)
        return _check("l2_json_consumer_strict", PASS, "API", "L2 JSON consumer strict validation passed.")

    @staticmethod
    def _check_contract(payload: _JsonReadResult) -> L2ApiReadinessCheck:
        if payload.error:
            return _check("contract_version", FAIL, "API", payload.error)
        if not isinstance(payload.value, dict):
            return _check("contract_version", FAIL, "API", "L2 context JSON top-level value must be an object.")
        errors: list[str] = []
        for key in REQUIRED_TOP_LEVEL_KEYS:
            if key not in payload.value:
                errors.append(f"missing top-level key: {key}")
        result = payload.value.get("result")
        if not isinstance(result, dict):
            errors.append("result must be an object")
        else:
            for key in REQUIRED_RESULT_KEYS:
                if key not in result:
                    errors.append(f"missing result key: {key}")
        if payload.value.get("service") != LAYER_NAME and payload.value.get("layer") != "BOOK_L2":
            errors.append(f"service must be {LAYER_NAME}")
        if not payload.value.get("contract_version"):
            errors.append("contract_version is required")
        if "source" in payload.value and not isinstance(payload.value.get("source"), dict):
            errors.append("source must be an object")
        if isinstance(result, dict) and "symbols" in result and not isinstance(result.get("symbols"), list):
            errors.append("symbols must be a list")
        if errors:
            return _check("contract_version", FAIL, "API", "; ".join(errors))
        return _check("contract_version", PASS, "API", "Contract, service, source, and result keys are present.")

    @staticmethod
    def _check_fail_closed_safety(payload: _JsonReadResult) -> L2ApiReadinessCheck:
        if payload.error:
            return _check("fail_closed_safety", FAIL, "SAFETY", payload.error)
        safety = payload.value.get("safety") if isinstance(payload.value, dict) else None
        if not isinstance(safety, dict):
            return _check("fail_closed_safety", FAIL, "SAFETY", "safety must be an object")
        errors: list[str] = []
        for field_name, expected in EXPECTED_SAFETY_FIELDS.items():
            if field_name not in safety:
                errors.append(f"missing safety field: {field_name}")
            elif safety[field_name] != expected:
                errors.append(f"safety.{field_name} must be {_format_value(expected)}")
        if "observe_only" in safety and safety.get("observe_only") is not True:
            errors.append("safety.observe_only must be true")
        if errors:
            return _check("fail_closed_safety", FAIL, "SAFETY", "; ".join(errors))
        return _check("fail_closed_safety", PASS, "SAFETY", "Safety is fail-closed.")

    @staticmethod
    def _check_observe_only_constraints(payload: _JsonReadResult) -> L2ApiReadinessCheck:
        if payload.error:
            return _check("observe_only_constraints", FAIL, "SAFETY", payload.error)
        text_parts = _runtime_text_parts(payload.value)
        matches: list[str] = []
        for text in text_parts:
            matches.extend(_forbidden_terms_in_text(text))
        if matches:
            return _check(
                "observe_only_constraints",
                FAIL,
                "SAFETY",
                f"Runtime human fields contain forbidden term(s): {', '.join(dict.fromkeys(matches))}",
            )
        return _check("observe_only_constraints", PASS, "SAFETY", "Runtime human fields contain no trading decision terms.")

    @staticmethod
    def _check_forbidden_l2_source_terms(project_root: Path) -> L2ApiReadinessCheck:
        source_dir = project_root / "app/market_interpreter"
        if not source_dir.is_dir():
            return _check("forbidden_imports", FAIL, "SAFETY", "Missing app/market_interpreter directory.")
        matches: list[str] = []
        for path in sorted(source_dir.glob("*.py")):
            text = _read_text(path)
            if text.error:
                return _check("forbidden_imports", FAIL, "SAFETY", text.error)
            for line_number, line in enumerate(text.value.splitlines(), start=1):
                for term in FORBIDDEN_L2_SOURCE_TERMS:
                    if term in line:
                        matches.append(f"{path.as_posix()}:{line_number}:{term}")
        if matches:
            return _check("forbidden_imports", FAIL, "SAFETY", f"Forbidden L2 source reference(s): {'; '.join(matches)}")
        return _check("forbidden_imports", PASS, "SAFETY", "No forbidden L2 source references found.")

    @staticmethod
    def _check_stable_output_file_policy(project_root: Path, *, config: L2ApiReadinessConfig) -> L2ApiReadinessCheck:
        output_path = config.l2_context_path.as_posix()
        if output_path != "reports/book_l2/timeline_context.json":
            return _check("stable_output_file_policy", FAIL, "API", "L2 context output path must be reports/book_l2/timeline_context.json")
        output_dir = _resolve(project_root, config.l2_context_path).parent
        if not output_dir.exists():
            return _check("stable_output_file_policy", FAIL, "API", "L2 output directory is missing.")
        unstable = tuple(
            path.name
            for path in sorted(output_dir.glob("timeline_context*.json"))
            if path.name != "timeline_context.json"
        )
        if unstable:
            return _check("stable_output_file_policy", FAIL, "API", f"Unstable runtime output file(s): {', '.join(unstable)}")
        return _check("stable_output_file_policy", PASS, "API", "L2 runtime output filename is stable.")

    @staticmethod
    def _check_guide_updated(project_root: Path) -> L2ApiReadinessCheck:
        path = project_root / "app/market_reader/terminal_guide.py"
        if not path.is_file():
            return _check("guide_updated", FAIL, "DOCS", "Missing terminal guide file.")
        source = _read_text(path)
        if source.error:
            return _check("guide_updated", FAIL, "DOCS", source.error)
        missing = tuple(command for command in REQUIRED_GUIDE_COMMANDS if command not in source.value)
        if "BOOK-L2 freeze candidate review" not in source.value:
            missing = (*missing, "BOOK-L2 freeze candidate review")
        if missing:
            return _check("guide_updated", FAIL, "DOCS", f"Terminal guide missing L2 workflow item(s): {', '.join(missing)}")
        return _check("guide_updated", PASS, "DOCS", "Terminal guide includes L2 freeze workflow.")

    @staticmethod
    def _check_planning_updated(project_root: Path, *, strict: bool) -> L2ApiReadinessCheck:
        missing = _missing_files(project_root, REQUIRED_PLANNING_FILES)
        if missing:
            return _check("planning_updated", FAIL, "DOCS", f"Missing planning file(s): {', '.join(missing)}")
        joined = "\n".join(_read_text(project_root / path).value for path in REQUIRED_PLANNING_FILES)
        missing_markers = tuple(marker for marker in PLANNING_FREEZE_MARKERS if marker not in joined)
        if missing_markers:
            status = FAIL if strict else WARN
            return _check("planning_updated", status, "DOCS", f"Planning is missing L2 freeze marker(s): {', '.join(missing_markers)}")
        return _check("planning_updated", PASS, "DOCS", "Planning records BOOK-L2 freeze candidate status.")

    @staticmethod
    def _check_stage_reports_exist(project_root: Path, *, strict: bool) -> L2ApiReadinessCheck:
        reports_dir = project_root / "reports/book_l2"
        if not reports_dir.is_dir():
            return _check("stage_reports_exist", FAIL, "DOCS", "Missing reports/book_l2 directory.")
        missing: list[str] = []
        for prefix in REQUIRED_STAGE_REPORT_PREFIXES:
            if not any(reports_dir.glob(f"{prefix}*.md")):
                missing.append(f"{prefix}*.md")
        if not (reports_dir / "book_l2_05_api_readiness_review_report.md").is_file():
            missing.append("book_l2_05_api_readiness_review_report.md")
        if missing:
            status = FAIL if strict else WARN
            return _check("stage_reports_exist", status, "DOCS", f"Missing L2 stage report(s): {', '.join(missing)}")
        return _check("stage_reports_exist", PASS, "DOCS", "Required BOOK-L2 stage reports exist.")

    @staticmethod
    def _build_details(
        *,
        project_root: Path,
        payload: Any,
        checks: tuple[L2ApiReadinessCheck, ...],
    ) -> dict[str, Any]:
        result = payload.get("result") if isinstance(payload, dict) else {}
        safety = payload.get("safety") if isinstance(payload, dict) else {}
        market_brief = result.get("market_brief") if isinstance(result, dict) else {}
        symbols = result.get("symbols") if isinstance(result, dict) else []
        return {
            "modules": {path: (project_root / path).is_file() for path in REQUIRED_L2_MODULES},
            "json": {
                "contract_version": payload.get("contract_version") if isinstance(payload, dict) else None,
                "service": payload.get("service") if isinstance(payload, dict) else None,
                "symbol_count": len(symbols) if isinstance(symbols, list) else 0,
                "overall_state": result.get("overall_state") if isinstance(result, dict) else None,
                "market_brief": isinstance(market_brief, dict),
            },
            "safety": {
                field_name: safety.get(field_name) if isinstance(safety, dict) else None
                for field_name in EXPECTED_SAFETY_FIELDS
            },
            "forbidden_imports": "no matches" if _check_status(checks, "forbidden_imports", PASS) else "matches found",
        }


class L2ApiReadinessFormatter:
    def format(self, result: L2ApiReadinessResult, *, show_details: bool = False) -> str:
        lines = [
            "BOOK-L2 API Readiness Review",
            "",
            "Layer: BOOK-L2 Market Interpreter",
            f"Input: {result.input_path}",
            f"Output: {result.output_path}",
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
        lines.extend(["", f"Result: {result.status}", f"Freeze candidate: {'YES' if result.freeze_candidate else 'NO'}"])
        return "\n".join(lines)

    def to_json_payload(self, result: L2ApiReadinessResult) -> dict[str, Any]:
        return {
            "status": result.status,
            "freeze_candidate": result.freeze_candidate,
            "layer": result.layer,
            "input_path": result.input_path,
            "output_path": result.output_path,
            "checks": [asdict(check) for check in result.checks],
            "warnings": list(result.warnings),
            "errors": list(result.errors),
        }

    @staticmethod
    def _format_details(result: L2ApiReadinessResult) -> str:
        details = result.details
        lines = ["Details:", "", "Modules:"]
        modules = details.get("modules") if isinstance(details, dict) else {}
        if isinstance(modules, dict):
            for path, exists in modules.items():
                lines.append(f"- {path}: {'PASS' if exists else 'FAIL'}")
        json_details = details.get("json") if isinstance(details, dict) else {}
        if isinstance(json_details, dict):
            lines.extend(
                [
                    "",
                    "JSON:",
                    f"- contract_version: {json_details.get('contract_version') or 'n/a'}",
                    f"- service: {json_details.get('service') or 'n/a'}",
                    f"- symbol_count: {json_details.get('symbol_count')}",
                    f"- overall_state: {json_details.get('overall_state') or 'n/a'}",
                    f"- market_brief: {'present' if json_details.get('market_brief') else 'missing'}",
                ]
            )
        safety = details.get("safety") if isinstance(details, dict) else {}
        if isinstance(safety, dict):
            lines.extend(["", "Safety:"])
            for key, value in safety.items():
                lines.append(f"- {key}: {_format_value(value)}")
        lines.extend(
            [
                "",
                "Forbidden imports:",
                f"- {details.get('forbidden_imports', 'n/a') if isinstance(details, dict) else 'n/a'}",
                "",
                "Freeze candidate:",
                "YES" if result.freeze_candidate else "NO",
            ]
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class _JsonReadResult:
    value: Any = None
    error: str | None = None


@dataclass(frozen=True)
class _TextReadResult:
    value: str = ""
    error: str | None = None


def _resolve(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def _missing_files(project_root: Path, paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(path for path in paths if not (project_root / path).is_file())


def _read_text(path: Path) -> _TextReadResult:
    try:
        return _TextReadResult(value=path.read_text(encoding="utf-8"))
    except OSError as exc:
        return _TextReadResult(error=f"Could not read {path.as_posix()}: {exc}")


def _read_json(path: Path) -> _JsonReadResult:
    if not path.is_file():
        return _JsonReadResult(error=f"Missing JSON file: {path.as_posix()}")
    try:
        return _JsonReadResult(value=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return _JsonReadResult(error=f"Invalid JSON in {path.as_posix()}: {exc.msg}")
    except OSError as exc:
        return _JsonReadResult(error=f"Could not read {path.as_posix()}: {exc}")


def _runtime_text_parts(payload: Any) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ()
    result = payload.get("result")
    if not isinstance(result, dict):
        return ()
    market_brief = result.get("market_brief")
    if not isinstance(market_brief, dict):
        return ()

    parts: list[str] = []
    for key in ("brief", "safety_note"):
        value = market_brief.get(key)
        if isinstance(value, str):
            parts.append(value)
    key_points = market_brief.get("key_points")
    if isinstance(key_points, list):
        parts.extend(str(point) for point in key_points)
    for key in ("observation_candidates", "skip_candidates"):
        candidates = market_brief.get(key)
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
    for term in FORBIDDEN_RUNTIME_TERMS:
        pattern = r"(?<![A-Z0-9])" + re.escape(term).replace(r"\ ", r"[\s_]+") + r"(?![A-Z0-9])"
        if re.search(pattern, normalized.upper()):
            matches.append(term)
    return tuple(matches)


def _check(name: str, status: str, severity: str, message: str) -> L2ApiReadinessCheck:
    return L2ApiReadinessCheck(name=name, status=status, severity=severity, message=message)


def _check_status(checks: tuple[L2ApiReadinessCheck, ...], name: str, status: str) -> bool:
    return any(check.name == name and check.status == status for check in checks)


def _format_checks_table(checks: tuple[L2ApiReadinessCheck, ...]) -> str:
    headers = ("Check", "Status", "Severity")
    rows = tuple((check.name, check.status, check.severity) for check in checks)
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _format_row(headers, widths), border]
    lines.extend(_format_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _format_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "n/a"
    return str(value)


__all__ = [
    "L2ApiReadinessConfig",
    "L2ApiReadinessCheck",
    "L2ApiReadinessResult",
    "L2ApiReadinessReviewer",
    "L2ApiReadinessFormatter",
]
