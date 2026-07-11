from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXPECTED_SERVICE = "BOOK_L1_MARKET_READER"
EXPECTED_CONTRACT_VERSION = "book_l1_json_export_v1"

REPORT_TYPE_TO_FILENAME = {
    "current": "current_preview.json",
    "multi": "multi_preview.json",
    "history": "history_preview.json",
    "timeline": "timeline_preview.json",
}

REPORT_TYPE_TO_JSON_REPORT_TYPE = {
    "current": "current_preview",
    "multi": "multi_preview",
    "history": "history_preview",
    "timeline": "timeline_preview",
}

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

EXPECTED_SAFETY_FIELDS: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
    "model_training_executed": False,
    "binance_download_executed": False,
}

STATUS_OK = "OK"
STATUS_MISSING = "MISSING"
STATUS_INVALID_JSON = "INVALID_JSON"
STATUS_INVALID_CONTRACT = "INVALID_CONTRACT"
STATUS_INVALID_SAFETY = "INVALID_SAFETY"
STATUS_ERROR = "ERROR"


@dataclass(frozen=True)
class RuntimeJsonConsumerConfig:
    input_dir: Path = Path("reports/book_l1")
    report_types: tuple[str, ...] = ("current", "multi", "history", "timeline")
    strict: bool = False


@dataclass(frozen=True)
class RuntimeJsonReportCheck:
    report_type: str
    path: Path
    exists: bool
    json_ok: bool
    contract_ok: bool
    safety_ok: bool
    status: str
    api_readable: bool
    message: str | None = None
    envelope: dict[str, Any] | None = None
    validation_errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RuntimeJsonConsumerResult:
    config: RuntimeJsonConsumerConfig
    checks: tuple[RuntimeJsonReportCheck, ...]
    result_status: str
    summary: dict[str, int]
    validation_errors: tuple[str, ...] = field(default_factory=tuple)


class RuntimeJsonConsumer:
    def run(self, config: RuntimeJsonConsumerConfig) -> RuntimeJsonConsumerResult:
        checks = tuple(self._check_report(config.input_dir, report_type) for report_type in config.report_types)
        summary = self._build_summary(checks)
        validation_errors = tuple(error for check in checks for error in check.validation_errors)
        result_status = "PASS" if all(check.api_readable for check in checks) else "FAIL"
        return RuntimeJsonConsumerResult(
            config=config,
            checks=checks,
            result_status=result_status,
            summary=summary,
            validation_errors=validation_errors,
        )

    def _check_report(self, input_dir: Path, report_type: str) -> RuntimeJsonReportCheck:
        filename = REPORT_TYPE_TO_FILENAME.get(report_type)
        if filename is None:
            path = input_dir / f"{report_type}.json"
            message = f"unsupported report type: {report_type}"
            return RuntimeJsonReportCheck(
                report_type=report_type,
                path=path,
                exists=False,
                json_ok=False,
                contract_ok=False,
                safety_ok=False,
                status=STATUS_ERROR,
                api_readable=False,
                message=message,
                validation_errors=(message,),
            )

        path = input_dir / filename
        if not path.exists():
            message = f"missing file: {path.as_posix()}"
            return RuntimeJsonReportCheck(
                report_type=report_type,
                path=path,
                exists=False,
                json_ok=False,
                contract_ok=False,
                safety_ok=False,
                status=STATUS_MISSING,
                api_readable=False,
                message=message,
                validation_errors=(message,),
            )

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            message = f"invalid JSON: {exc.msg}"
            return RuntimeJsonReportCheck(
                report_type=report_type,
                path=path,
                exists=True,
                json_ok=False,
                contract_ok=False,
                safety_ok=False,
                status=STATUS_INVALID_JSON,
                api_readable=False,
                message=message,
                validation_errors=(message,),
            )
        except OSError as exc:
            message = f"read error: {exc}"
            return RuntimeJsonReportCheck(
                report_type=report_type,
                path=path,
                exists=True,
                json_ok=False,
                contract_ok=False,
                safety_ok=False,
                status=STATUS_ERROR,
                api_readable=False,
                message=message,
                validation_errors=(message,),
            )

        contract_errors = _validate_contract(payload, expected_report_type=REPORT_TYPE_TO_JSON_REPORT_TYPE[report_type])
        envelope = payload if isinstance(payload, dict) else None
        safety_errors = _validate_safety(envelope.get("safety") if envelope else None) if not contract_errors else ()
        contract_ok = not contract_errors
        safety_ok = contract_ok and not safety_errors

        if not contract_ok:
            status = STATUS_INVALID_CONTRACT
            errors = contract_errors
        elif not safety_ok:
            status = STATUS_INVALID_SAFETY
            errors = safety_errors
        else:
            status = STATUS_OK
            errors = ()

        message = "; ".join(errors) if errors else None
        return RuntimeJsonReportCheck(
            report_type=report_type,
            path=path,
            exists=True,
            json_ok=True,
            contract_ok=contract_ok,
            safety_ok=safety_ok,
            status=status,
            api_readable=contract_ok and safety_ok,
            message=message,
            envelope=envelope,
            validation_errors=tuple(errors),
        )

    @staticmethod
    def _build_summary(checks: tuple[RuntimeJsonReportCheck, ...]) -> dict[str, int]:
        return {
            "reports_checked": len(checks),
            "api_readable": sum(1 for check in checks if check.api_readable),
            "missing": sum(1 for check in checks if check.status == STATUS_MISSING),
            "invalid_json": sum(1 for check in checks if check.status == STATUS_INVALID_JSON),
            "invalid_contract": sum(1 for check in checks if check.status == STATUS_INVALID_CONTRACT),
            "invalid_safety": sum(1 for check in checks if check.status == STATUS_INVALID_SAFETY),
            "errors": sum(1 for check in checks if check.status == STATUS_ERROR),
        }


class RuntimeJsonConsumerFormatter:
    def format(self, result: RuntimeJsonConsumerResult, *, show_details: bool = False) -> str:
        lines = [
            "BOOK-L1 Runtime JSON Consumer / API Reader Smoke",
            "",
            f"Input dir: {result.config.input_dir.as_posix()}",
            f"Expected contract: {EXPECTED_CONTRACT_VERSION}",
            f"Expected service: {EXPECTED_SERVICE}",
            "",
            _format_table(result.checks),
            "",
            "Summary:",
            f"Reports checked: {result.summary['reports_checked']}",
            f"API-readable: {result.summary['api_readable']}",
            f"Missing: {result.summary['missing']}",
            f"Invalid JSON: {result.summary['invalid_json']}",
            f"Invalid contract: {result.summary['invalid_contract']}",
            f"Invalid safety: {result.summary['invalid_safety']}",
            "",
            "Safety:",
            "trade_signal: NOT_EVALUATED",
            "safe_for_runtime_trading: false",
            "orders_enabled: false",
            "live_trading_connected: false",
            "approved_for_live_trading: false",
        ]

        if show_details:
            lines.extend(["", self._format_details(result.checks)])

        lines.extend(["", f"Result: {result.result_status}"])
        return "\n".join(lines)

    @staticmethod
    def _format_details(checks: tuple[RuntimeJsonReportCheck, ...]) -> str:
        lines = ["Details:"]
        for check in checks:
            envelope = check.envelope or {}
            safety = envelope.get("safety") if isinstance(envelope.get("safety"), dict) else {}
            warnings = envelope.get("warnings")
            errors = envelope.get("errors")
            lines.extend(
                [
                    f"- {check.report_type}",
                    f"  path: {check.path.as_posix()}",
                    f"  report_type: {envelope.get('report_type', 'n/a')}",
                    f"  status: {check.status}",
                    f"  service: {envelope.get('service', 'n/a')}",
                    f"  contract_version: {envelope.get('contract_version', 'n/a')}",
                    f"  safety.trade_signal: {safety.get('trade_signal', 'n/a')}",
                    f"  safety.safe_for_runtime_trading: {_format_bool_or_value(safety.get('safe_for_runtime_trading', 'n/a'))}",
                    f"  safety.orders_enabled: {_format_bool_or_value(safety.get('orders_enabled', 'n/a'))}",
                    f"  safety.live_trading_connected: {_format_bool_or_value(safety.get('live_trading_connected', 'n/a'))}",
                    f"  warnings count: {len(warnings) if isinstance(warnings, list) else 'n/a'}",
                    f"  errors count: {len(errors) if isinstance(errors, list) else 'n/a'}",
                ]
            )
            if check.validation_errors:
                lines.append("  validation messages:")
                lines.extend(f"  - {error}" for error in check.validation_errors)
            else:
                lines.append("  validation messages: none")
        return "\n".join(lines)


def _validate_contract(payload: Any, *, expected_report_type: str) -> tuple[str, ...]:
    if not isinstance(payload, dict):
        return ("top-level JSON value must be an object",)

    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    if payload.get("service") != EXPECTED_SERVICE:
        errors.append(f"service must be {EXPECTED_SERVICE}")
    if payload.get("contract_version") != EXPECTED_CONTRACT_VERSION:
        errors.append(f"contract_version must be {EXPECTED_CONTRACT_VERSION}")
    if payload.get("report_type") != expected_report_type:
        errors.append(f"report_type must be {expected_report_type}")
    if "request" in payload and not isinstance(payload.get("request"), dict):
        errors.append("request must be an object")
    if "summary" in payload and not isinstance(payload.get("summary"), dict):
        errors.append("summary must be an object")
    if "safety" in payload and not isinstance(payload.get("safety"), dict):
        errors.append("safety must be an object")
    if "warnings" in payload and not isinstance(payload.get("warnings"), list):
        errors.append("warnings must be a list")
    if "errors" in payload and not isinstance(payload.get("errors"), list):
        errors.append("errors must be a list")

    return tuple(errors)


def _validate_safety(safety: Any) -> tuple[str, ...]:
    if not isinstance(safety, dict):
        return ("safety must be an object",)

    errors: list[str] = []
    for field_name, expected_value in EXPECTED_SAFETY_FIELDS.items():
        if field_name not in safety:
            errors.append(f"missing safety field: {field_name}")
            continue
        if safety[field_name] != expected_value:
            errors.append(f"safety.{field_name} must be {_format_bool_or_value(expected_value)}")
    return tuple(errors)


def _format_table(checks: tuple[RuntimeJsonReportCheck, ...]) -> str:
    headers = ("Type", "File", "Exists", "JSON", "Contract", "Safety", "Status", "API OK")
    rows = [
        (
            check.report_type,
            check.path.name,
            "yes" if check.exists else "no",
            _ok_fail_na(check.json_ok, check.exists),
            _ok_fail_na(check.contract_ok, check.json_ok),
            _ok_fail_na(check.safety_ok, check.contract_ok),
            check.status.lower(),
            "yes" if check.api_readable else "no",
        )
        for check in checks
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [
        border,
        _format_table_row(headers, widths),
        border,
    ]
    lines.extend(_format_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _format_table_row(values: tuple[str, ...], widths: list[int]) -> str:
    cells = [f" {value:<{widths[index]}} " for index, value in enumerate(values)]
    return "|" + "|".join(cells) + "|"


def _ok_fail_na(ok: bool, applicable: bool) -> str:
    if not applicable:
        return "n/a"
    return "ok" if ok else "fail"


def _format_bool_or_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


__all__ = [
    "EXPECTED_SERVICE",
    "EXPECTED_CONTRACT_VERSION",
    "REPORT_TYPE_TO_FILENAME",
    "REPORT_TYPE_TO_JSON_REPORT_TYPE",
    "RuntimeJsonConsumerConfig",
    "RuntimeJsonReportCheck",
    "RuntimeJsonConsumerResult",
    "RuntimeJsonConsumer",
    "RuntimeJsonConsumerFormatter",
]
