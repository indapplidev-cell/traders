from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SERVICE_NAME = "BOOK_L1_MARKET_READER"
CONTRACT_VERSION = "book_l1_json_export_v1"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

REQUIRED_MARKET_READER_MODULES = (
    "app/market_reader/schemas.py",
    "app/market_reader/candle_window.py",
    "app/market_reader/candle_morphology.py",
    "app/market_reader/swing_detector.py",
    "app/market_reader/trend_structure.py",
    "app/market_reader/range_structure.py",
    "app/market_reader/breakout_retest.py",
    "app/market_reader/technical_context.py",
    "app/market_reader/market_regime_composer.py",
    "app/market_reader/market_reader.py",
    "app/market_reader/cli_preview.py",
    "app/market_reader/api_response.py",
    "app/market_reader/interactive_preview.py",
    "app/market_reader/multi_symbol_preview.py",
    "app/market_reader/history_snapshot.py",
    "app/market_reader/timeline_preview.py",
    "app/market_reader/json_export.py",
    "app/market_reader/json_consumer.py",
    "app/market_reader/terminal_guide.py",
    "app/cli/commands.py",
)

REQUIRED_BOOK_L1_TESTS = (
    "tests/test_book_l1_market_reader_schemas.py",
    "tests/test_book_l1_candle_window.py",
    "tests/test_book_l1_candle_morphology.py",
    "tests/test_book_l1_swing_detector.py",
    "tests/test_book_l1_trend_structure.py",
    "tests/test_book_l1_range_structure.py",
    "tests/test_book_l1_breakout_retest.py",
    "tests/test_book_l1_technical_context.py",
    "tests/test_book_l1_market_regime_composer.py",
    "tests/test_book_l1_market_reader_orchestrator.py",
    "tests/test_book_l1_cli_preview.py",
    "tests/test_book_l1_api_response_contract.py",
    "tests/test_book_l1_interactive_preview.py",
    "tests/test_book_l1_multi_symbol_preview.py",
    "tests/test_book_l1_history_snapshot.py",
    "tests/test_book_l1_timeline_preview.py",
    "tests/test_book_l1_timeline_export.py",
    "tests/test_book_l1_json_export.py",
    "tests/test_book_l1_terminal_guide.py",
    "tests/test_book_l1_json_consumer.py",
)

REQUIRED_PLANNING_FILES = (
    "planning/README.md",
    "planning/01_CURRENT_STATE.md",
    "planning/02_CURRENT_TASK.md",
    "planning/03_REMAINING_WORK.md",
    "planning/04_BOOK_L1_MARKET_READER_PLAN.md",
)

STABLE_JSON_FILES = {
    "current_preview": "reports/book_l1/current_preview.json",
    "multi_preview": "reports/book_l1/multi_preview.json",
    "history_preview": "reports/book_l1/history_preview.json",
    "timeline_preview": "reports/book_l1/timeline_preview.json",
}

REQUIRED_CLI_COMMANDS = (
    "book-l1-guide",
    "book-l1-preview",
    "book-l1-interactive-preview",
    "book-l1-api-preview",
    "book-l1-multi-preview",
    "book-l1-history-preview",
    "book-l1-timeline-preview",
    "book-l1-json-consumer-smoke",
    "book-l1-api-readiness-review",
)

REQUIRED_TOP_LEVEL_KEYS = (
    "status",
    "service",
    "report_type",
    "contract_version",
    "request",
    "result",
    "summary",
    "safety",
    "warnings",
    "errors",
)

CORE_SAFETY_FIELDS: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "approved_for_live_trading": False,
}

EXTENDED_SAFETY_FIELDS: dict[str, object] = {
    "traders_core_connected": False,
    "approved_for_auto_activation": False,
    "model_training_executed": False,
    "binance_download_executed": False,
}


@dataclass(frozen=True)
class ApiReadinessCheck:
    name: str
    status: str
    message: str
    severity: str = "INFO"


@dataclass(frozen=True)
class ApiReadinessReviewResult:
    status: str
    freeze_candidate: bool
    checks: tuple[ApiReadinessCheck, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_checks(cls, checks: tuple[ApiReadinessCheck, ...]) -> ApiReadinessReviewResult:
        errors = tuple(check.message for check in checks if check.status == FAIL)
        warnings = tuple(check.message for check in checks if check.status == WARN)
        if errors:
            status = FAIL
        elif warnings:
            status = WARN
        else:
            status = PASS
        return cls(
            status=status,
            freeze_candidate=not errors,
            checks=checks,
            warnings=warnings,
            errors=errors,
        )


class ApiReadinessReviewer:
    def __init__(self, *, project_root: Path | None = None) -> None:
        self.project_root = Path.cwd() if project_root is None else Path(project_root)

    def run(self) -> ApiReadinessReviewResult:
        checks = (
            self._check_required_paths("market_reader_modules", REQUIRED_MARKET_READER_MODULES, "Required modules are present."),
            self._check_required_paths("book_l1_tests", REQUIRED_BOOK_L1_TESTS, "Required test files are present."),
            self._check_required_paths("planning_files", REQUIRED_PLANNING_FILES, "Planning files are present."),
            self._check_cli_commands(),
            *self._check_json_exports(),
        )
        return ApiReadinessReviewResult.from_checks(checks)

    def _check_required_paths(
        self,
        name: str,
        relative_paths: tuple[str, ...],
        pass_message: str,
    ) -> ApiReadinessCheck:
        missing = tuple(path for path in relative_paths if not (self.project_root / path).is_file())
        if missing:
            return ApiReadinessCheck(
                name=name,
                status=FAIL,
                severity="ERROR",
                message=f"Missing required file(s): {', '.join(missing)}",
            )
        return ApiReadinessCheck(name=name, status=PASS, message=pass_message)

    def _check_cli_commands(self) -> ApiReadinessCheck:
        commands_path = self.project_root / "app/cli/commands.py"
        if not commands_path.is_file():
            return ApiReadinessCheck(
                name="cli_commands",
                status=FAIL,
                severity="ERROR",
                message="Missing app/cli/commands.py.",
            )
        try:
            source = commands_path.read_text(encoding="utf-8")
        except OSError as exc:
            return ApiReadinessCheck(
                name="cli_commands",
                status=FAIL,
                severity="ERROR",
                message=f"Could not read app/cli/commands.py: {exc}",
            )
        missing = tuple(command for command in REQUIRED_CLI_COMMANDS if f'@cli.command("{command}")' not in source)
        if missing:
            return ApiReadinessCheck(
                name="cli_commands",
                status=FAIL,
                severity="ERROR",
                message=f"Missing BOOK-L1 CLI command(s): {', '.join(missing)}",
            )
        return ApiReadinessCheck(
            name="cli_commands",
            status=PASS,
            message="Required BOOK-L1 CLI commands are registered.",
        )

    def _check_json_exports(self) -> tuple[ApiReadinessCheck, ApiReadinessCheck, ApiReadinessCheck]:
        missing: list[str] = []
        unreadable: list[str] = []
        contract_errors: list[str] = []
        safety_errors: list[str] = []
        safety_warnings: list[str] = []

        for report_type, relative_path in STABLE_JSON_FILES.items():
            path = self.project_root / relative_path
            if not path.exists():
                missing.append(relative_path)
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                unreadable.append(f"{relative_path}: invalid JSON ({exc.msg})")
                continue
            except OSError as exc:
                unreadable.append(f"{relative_path}: read error ({exc})")
                continue

            contract_errors.extend(
                f"{relative_path}: {error}" for error in _validate_contract(payload, expected_report_type=report_type)
            )
            if isinstance(payload, dict):
                safety_result = _validate_safety(payload.get("safety"))
                safety_errors.extend(f"{relative_path}: {error}" for error in safety_result.errors)
                safety_warnings.extend(f"{relative_path}: {warning}" for warning in safety_result.warnings)

        json_export_check = self._json_export_files_check(missing=tuple(missing), unreadable=tuple(unreadable))
        json_contract_check = self._json_contract_check(contract_errors=tuple(contract_errors), unreadable=tuple(unreadable))
        safety_check = self._safety_contract_check(
            safety_errors=tuple(safety_errors),
            safety_warnings=tuple(safety_warnings),
            unreadable=tuple(unreadable),
            contract_errors=tuple(contract_errors),
        )
        return (json_export_check, json_contract_check, safety_check)

    @staticmethod
    def _json_export_files_check(*, missing: tuple[str, ...], unreadable: tuple[str, ...]) -> ApiReadinessCheck:
        if unreadable:
            return ApiReadinessCheck(
                name="json_export_files",
                status=FAIL,
                severity="ERROR",
                message=f"Runtime JSON file(s) are invalid or unreadable: {'; '.join(unreadable)}",
            )
        if missing:
            return ApiReadinessCheck(
                name="json_export_files",
                status=WARN,
                severity="WARN",
                message=f"Stable runtime JSON file(s) are missing after clean checkout/export not run: {', '.join(missing)}",
            )
        return ApiReadinessCheck(
            name="json_export_files",
            status=PASS,
            message="Stable JSON files are present and readable.",
        )

    @staticmethod
    def _json_contract_check(*, contract_errors: tuple[str, ...], unreadable: tuple[str, ...]) -> ApiReadinessCheck:
        if unreadable:
            return ApiReadinessCheck(
                name="json_contract",
                status=FAIL,
                severity="ERROR",
                message="JSON contract cannot be validated because at least one runtime JSON file is unreadable.",
            )
        if contract_errors:
            return ApiReadinessCheck(
                name="json_contract",
                status=FAIL,
                severity="ERROR",
                message=f"JSON contract violation(s): {'; '.join(contract_errors)}",
            )
        return ApiReadinessCheck(
            name="json_contract",
            status=PASS,
            message="contract_version and JSON envelope are valid for existing runtime JSON files.",
        )

    @staticmethod
    def _safety_contract_check(
        *,
        safety_errors: tuple[str, ...],
        safety_warnings: tuple[str, ...],
        unreadable: tuple[str, ...],
        contract_errors: tuple[str, ...],
    ) -> ApiReadinessCheck:
        if unreadable or contract_errors:
            return ApiReadinessCheck(
                name="safety_contract",
                status=FAIL,
                severity="ERROR",
                message="Safety contract cannot be validated because JSON files or envelope contract failed.",
            )
        if safety_errors:
            return ApiReadinessCheck(
                name="safety_contract",
                status=FAIL,
                severity="ERROR",
                message=f"Fail-closed safety violation(s): {'; '.join(safety_errors)}",
            )
        if safety_warnings:
            return ApiReadinessCheck(
                name="safety_contract",
                status=WARN,
                severity="WARN",
                message=f"Fail-closed core safety is valid; extended safety field warning(s): {'; '.join(safety_warnings)}",
            )
        return ApiReadinessCheck(
            name="safety_contract",
            status=PASS,
            message="Fail-closed safety is preserved for existing runtime JSON files.",
        )


class ApiReadinessReviewFormatter:
    def format(
        self,
        result: ApiReadinessReviewResult,
        *,
        strict: bool = False,
        show_details: bool = False,
    ) -> str:
        display_status = FAIL if strict and result.status == WARN else result.status
        lines = [
            "BOOK-L1 API Readiness Final Review",
            "",
            f"Result: {display_status}",
            f"Freeze candidate: {'YES' if result.freeze_candidate else 'NO'}",
            "",
            _format_table(result.checks),
            "",
            "Conclusion:",
            self._conclusion(result),
        ]
        if show_details:
            lines.extend(["", self._details(result)])
        return "\n".join(lines)

    @staticmethod
    def _conclusion(result: ApiReadinessReviewResult) -> str:
        if result.freeze_candidate:
            return "BOOK-L1 is a Layer 1 freeze candidate."
        return "BOOK-L1 is not a Layer 1 freeze candidate until FAIL checks are fixed."

    @staticmethod
    def _details(result: ApiReadinessReviewResult) -> str:
        lines = [
            "Details:",
            f"Warnings: {len(result.warnings)}",
            f"Errors: {len(result.errors)}",
        ]
        for check in result.checks:
            lines.extend(
                [
                    f"- {check.name}",
                    f"  status: {check.status}",
                    f"  severity: {check.severity}",
                    f"  message: {check.message}",
                ]
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class _SafetyValidationResult:
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _validate_contract(payload: Any, *, expected_report_type: str) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ("top-level JSON value must be an object",)

    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    if payload.get("service") != SERVICE_NAME:
        errors.append(f"service must be {SERVICE_NAME}")
    if payload.get("contract_version") != CONTRACT_VERSION:
        errors.append(f"contract_version must be {CONTRACT_VERSION}")
    if payload.get("report_type") != expected_report_type:
        errors.append(f"report_type must be {expected_report_type}")
    if "request" in payload and not isinstance(payload.get("request"), dict):
        errors.append("request must be an object")
    if "result" in payload and not isinstance(payload.get("result"), dict):
        errors.append("result must be an object")
    if "summary" in payload and not isinstance(payload.get("summary"), dict):
        errors.append("summary must be an object")
    if "safety" in payload and not isinstance(payload.get("safety"), dict):
        errors.append("safety must be an object")
    if "warnings" in payload and not isinstance(payload.get("warnings"), list):
        errors.append("warnings must be a list")
    if "errors" in payload and not isinstance(payload.get("errors"), list):
        errors.append("errors must be a list")

    return tuple(errors)


def _validate_safety(safety: Any) -> _SafetyValidationResult:
    if not isinstance(safety, dict):
        return _SafetyValidationResult(errors=("safety must be an object",))

    errors: list[str] = []
    warnings: list[str] = []
    for field_name, expected_value in CORE_SAFETY_FIELDS.items():
        if field_name not in safety:
            errors.append(f"missing core safety field: {field_name}")
            continue
        if safety[field_name] != expected_value:
            errors.append(f"safety.{field_name} must be {_format_value(expected_value)}")

    for field_name, expected_value in EXTENDED_SAFETY_FIELDS.items():
        if field_name not in safety:
            warnings.append(f"missing extended safety field: {field_name}")
            continue
        if safety[field_name] != expected_value:
            errors.append(f"safety.{field_name} must be {_format_value(expected_value)}")

    return _SafetyValidationResult(errors=tuple(errors), warnings=tuple(warnings))


def _format_table(checks: tuple[ApiReadinessCheck, ...]) -> str:
    headers = ("Check", "Status", "Severity", "Message")
    rows = tuple((check.name, check.status, check.severity, check.message) for check in checks)
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], min(len(value), 80))

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _format_row(headers, widths), border]
    lines.extend(_format_row(tuple(_truncate(value, widths[index]) for index, value in enumerate(row)), widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _format_row(values: tuple[str, ...], widths: list[int]) -> str:
    cells = [f" {value:<{widths[index]}} " for index, value in enumerate(values)]
    return "|" + "|".join(cells) + "|"


def _truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return f"{value[: width - 3]}..."


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


__all__ = [
    "ApiReadinessCheck",
    "ApiReadinessReviewFormatter",
    "ApiReadinessReviewResult",
    "ApiReadinessReviewer",
]
