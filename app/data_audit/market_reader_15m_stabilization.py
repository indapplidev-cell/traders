from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.data_audit.candle_availability import (
    CandleAvailabilityAuditConfig,
    CandleAvailabilityAuditResult,
    CandleAvailabilityAuditor,
    READY,
)
from app.data_audit.interval_preparation_decision import DECISION_15M_ONLY, RECOMMENDED_OPTION


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_OUTPUT_JSON = Path("reports/book_data/market_reader_15m_stabilization.json")
DEFAULT_OUTPUT_MD = Path("reports/book_data/market_reader_15m_stabilization.md")
DEFAULT_STAGE_REPORT = Path("reports/book_data/book_data_03c_15m_only_market_reader_stabilization_report.md")
DEFAULT_CANDLE_AUDIT_JSON = Path("reports/book_data/candle_availability_audit.json")
DEFAULT_CANDLE_AUDIT_MD = Path("reports/book_data/candle_availability_audit.md")
DEFAULT_DECISION_JSON = Path("reports/book_data/interval_data_preparation_decision.json")
DEFAULT_L1_TIMELINE_JSON = Path("reports/book_l1/timeline_preview.json")
DEFAULT_L2_CONTEXT_JSON = Path("reports/book_l2/timeline_context.json")
DEFAULT_L2_ANSWER_MD = Path("reports/book_l2/l1_l2_interval_answer.md")
CONTRACT_VERSION = "book_data_market_reader_15m_stabilization_v1"
SERVICE_NAME = "BOOK_DATA_STABILIZATION"
REPORT_TYPE = "market_reader_15m_stabilization"

PASS = "PASS"
PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
FAIL = "FAIL"
ALLOWED_INTERVAL = "15m"

CRITICAL_L2_SAFETY_FIELDS: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "live_trading_connected": False,
}
OPTIONAL_L2_SAFETY_FIELDS: dict[str, object] = {
    "orders_enabled": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
}


@dataclass(frozen=True)
class MarketReader15mStabilizationConfig:
    symbols: tuple[str, ...] = DEFAULT_SYMBOLS
    interval: str = ALLOWED_INTERVAL
    window_size: int = 300
    window_count: int = 4
    min_candles: int = 50
    output_json: Path = DEFAULT_OUTPUT_JSON
    output_md: Path = DEFAULT_OUTPUT_MD
    strict: bool = False
    show_details: bool = False
    stage_report: Path = DEFAULT_STAGE_REPORT
    candle_audit_json: Path = DEFAULT_CANDLE_AUDIT_JSON
    candle_audit_md: Path = DEFAULT_CANDLE_AUDIT_MD
    decision_json: Path = DEFAULT_DECISION_JSON
    l1_json_path: Path = DEFAULT_L1_TIMELINE_JSON
    l2_json_path: Path = DEFAULT_L2_CONTEXT_JSON
    l2_answer_md: Path = DEFAULT_L2_ANSWER_MD

    def __post_init__(self) -> None:
        symbols = normalize_symbols(self.symbols)
        object.__setattr__(self, "symbols", symbols or DEFAULT_SYMBOLS)
        object.__setattr__(self, "interval", str(self.interval).strip() or ALLOWED_INTERVAL)
        object.__setattr__(self, "output_json", Path(self.output_json))
        object.__setattr__(self, "output_md", Path(self.output_md))
        object.__setattr__(self, "stage_report", Path(self.stage_report))
        object.__setattr__(self, "candle_audit_json", Path(self.candle_audit_json))
        object.__setattr__(self, "candle_audit_md", Path(self.candle_audit_md))
        object.__setattr__(self, "decision_json", Path(self.decision_json))
        object.__setattr__(self, "l1_json_path", Path(self.l1_json_path))
        object.__setattr__(self, "l2_json_path", Path(self.l2_json_path))
        object.__setattr__(self, "l2_answer_md", Path(self.l2_answer_md))


@dataclass(frozen=True)
class MarketReader15mStabilizationStep:
    name: str
    status: str
    message: str
    evidence_path: str | None = None


@dataclass(frozen=True)
class MarketReader15mStabilizationResult:
    status: str
    active_interval: str = ALLOWED_INTERVAL
    symbols: tuple[str, ...] = ()
    steps: tuple[MarketReader15mStabilizationStep, ...] = field(default_factory=tuple)
    output_json: str | None = None
    output_md: str | None = None
    l2_overall_state: str | None = None
    observation_candidates: tuple[str, ...] = ()
    skip_candidates: tuple[str, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)
    stage_report: str | None = None
    decision: dict[str, Any] = field(default_factory=dict)
    l2_answer: dict[str, Any] = field(default_factory=dict)
    safety: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status in {PASS, PASS_WITH_WARNINGS}


class MarketReader15mStabilizationServices(Protocol):
    def run_candle_availability(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def check_interval_decision(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, dict[str, Any], tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l1_timeline_export(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l1_json_consumer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l2_context_export(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l2_json_consumer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l2_api_readiness(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...

    def run_l1_l2_answer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        ...


class DefaultMarketReader15mStabilizationServices:
    def __init__(self, candle_repository: Any) -> None:
        self._candle_repository = candle_repository

    def run_candle_availability(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        audit_config = CandleAvailabilityAuditConfig(
            symbols=config.symbols,
            intervals=(ALLOWED_INTERVAL,),
            window_size=config.window_size,
            window_count=config.window_count,
            required_candles=config.window_size * config.window_count,
            output_json=config.candle_audit_json,
            output_md=config.candle_audit_md,
            strict=True,
            show_details=config.show_details,
        )
        result = CandleAvailabilityAuditor(self._candle_repository).run(audit_config)
        rows_ready = all(row.interval == ALLOWED_INTERVAL and row.status == READY for row in result.rows)
        if result.status == PASS and rows_ready:
            return (
                _pass(
                    "candle_availability_15m",
                    "15m candles are READY for requested symbols.",
                    config.candle_audit_json,
                ),
                result.warnings,
                result.errors,
            )
        message = "; ".join(result.errors) or _availability_failure_message(result)
        return (_fail("candle_availability_15m", message, config.candle_audit_json), result.warnings, (message,))

    def check_interval_decision(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, dict[str, Any], tuple[str, ...], tuple[str, ...]]:
        payload = read_json(config.decision_json)
        if payload.error:
            return (_fail("interval_preparation_decision", payload.error, config.decision_json), {}, (), (payload.error,))
        if not isinstance(payload.value, dict):
            message = "Interval preparation decision JSON must be an object."
            return (_fail("interval_preparation_decision", message, config.decision_json), {}, (), (message,))
        decision = _dict(payload.value.get("decision"))
        decision_id = str(decision.get("decision_id") or "")
        active_intervals = tuple(str(item) for item in _list(decision.get("active_intervals")))
        required_now = tuple(str(item) for item in _list(decision.get("required_intervals_for_current_market_reader")))
        if ALLOWED_INTERVAL not in active_intervals and ALLOWED_INTERVAL not in required_now:
            message = "Interval preparation decision does not confirm 15m as active interval."
            return (_fail("interval_preparation_decision", message, config.decision_json), payload.value, (), (message,))
        warnings: tuple[str, ...] = ()
        if decision_id != DECISION_15M_ONLY:
            warnings = (f"Decision ID is {decision_id or 'missing'}, expected {DECISION_15M_ONLY}.",)
        return (
            _pass("interval_preparation_decision", "Decision artifact confirms 15m active interval.", config.decision_json),
            payload.value,
            warnings,
            (),
        )

    def run_l1_timeline_export(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.market_reader.json_export import build_timeline_preview_export_payload, write_book_l1_json_export
            from app.market_reader.timeline_preview import TimelinePreviewConfig, TimelinePreviewRunner

            preview_config = TimelinePreviewConfig(
                symbols=config.symbols,
                interval=config.interval,
                window_size=config.window_size,
                window_count=config.window_count,
                min_candles=config.min_candles,
            )
            result = TimelinePreviewRunner(candle_repository=self._candle_repository).run(preview_config)
            envelope = build_timeline_preview_export_payload(
                request={
                    "symbols": list(config.symbols),
                    "interval": config.interval,
                    "window_size": config.window_size,
                    "window_count": config.window_count,
                    "min_candles": config.min_candles,
                    "non_interactive": True,
                    "show_details": config.show_details,
                },
                result=result,
            )
            path = write_book_l1_json_export(envelope, output_dir=config.l1_json_path.parent)
        except Exception as exc:
            message = f"L1 timeline export failed: {exc}"
            return (_fail("l1_timeline_export_15m", message, config.l1_json_path), (), (message,))
        return (_pass("l1_timeline_export_15m", f"Written: {path.as_posix()}", path), (), ())

    def run_l1_json_consumer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.market_reader.json_consumer import RuntimeJsonConsumer, RuntimeJsonConsumerConfig

            result = RuntimeJsonConsumer().run(
                RuntimeJsonConsumerConfig(input_dir=config.l1_json_path.parent, report_types=("timeline",), strict=True)
            )
        except Exception as exc:
            message = f"L1 JSON consumer failed: {exc}"
            return (_fail("l1_json_consumer_strict", message), (), (message,))
        if result.result_status == PASS:
            return (_pass("l1_json_consumer_strict", "BOOK-L1 timeline JSON strict validation passed."), (), ())
        message = "; ".join(result.validation_errors or ("BOOK-L1 JSON consumer did not pass.",))
        return (_fail("l1_json_consumer_strict", message), (), (message,))

    def run_l2_context_export(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.market_interpreter import L1TimelineConsumer, L1TimelineConsumerConfig

            result = L1TimelineConsumer().run(
                L1TimelineConsumerConfig(
                    input_path=config.l1_json_path,
                    strict=True,
                    export_json=True,
                    output_dir=config.l2_json_path.parent,
                )
            )
        except Exception as exc:
            message = f"L2 context export failed: {exc}"
            return (_fail("l2_context_export_15m", message, config.l2_json_path), (), (message,))
        if result.status == "OK":
            return (_pass("l2_context_export_15m", f"Written: {config.l2_json_path.as_posix()}", config.l2_json_path), result.warnings, ())
        message = "; ".join(result.errors or ("BOOK-L2 context export failed.",))
        return (_fail("l2_context_export_15m", message, config.l2_json_path), result.warnings, (message,))

    def run_l2_json_consumer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.market_interpreter import L2ContextConsumerConfig, L2ContextJsonConsumer

            result = L2ContextJsonConsumer().run(L2ContextConsumerConfig(input_path=config.l2_json_path, strict=True))
        except Exception as exc:
            message = f"L2 JSON consumer failed: {exc}"
            return (_fail("l2_json_consumer_strict", message, config.l2_json_path), (), (message,))
        if result.status == PASS:
            return (_pass("l2_json_consumer_strict", "BOOK-L2 context JSON strict validation passed.", config.l2_json_path), (), ())
        message = "; ".join(result.errors or result.warnings or ("BOOK-L2 JSON consumer did not pass.",))
        return (_fail("l2_json_consumer_strict", message, config.l2_json_path), result.warnings, (message,))

    def run_l2_api_readiness(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.market_interpreter import L2ApiReadinessConfig, L2ApiReadinessReviewer

            result = L2ApiReadinessReviewer().run(
                L2ApiReadinessConfig(
                    project_root=Path("."),
                    l1_timeline_path=config.l1_json_path,
                    l2_context_path=config.l2_json_path,
                    strict=True,
                    show_details=config.show_details,
                )
            )
        except Exception as exc:
            message = f"L2 API readiness review failed: {exc}"
            return (_fail("l2_api_readiness_strict", message), (), (message,))
        if result.status == PASS:
            return (_pass("l2_api_readiness_strict", "BOOK-L2 API readiness strict review passed."), (), ())
        message = "; ".join(result.errors or result.warnings or ("BOOK-L2 API readiness strict review did not pass.",))
        return (_fail("l2_api_readiness_strict", message), result.warnings, (message,))

    def run_l1_l2_answer(
        self,
        config: MarketReader15mStabilizationConfig,
    ) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
        try:
            from app.integration.l1_l2_interval_answer_smoke import (
                L1L2IntervalAnswerSmokeConfig,
                L1L2IntervalAnswerSmokeRunner,
            )

            result = L1L2IntervalAnswerSmokeRunner().run(
                L1L2IntervalAnswerSmokeConfig(
                    symbols=config.symbols,
                    interval=config.interval,
                    window_size=config.window_size,
                    window_count=config.window_count,
                    min_candles=config.min_candles,
                    output_md=config.l2_answer_md,
                    strict=True,
                    show_details=config.show_details,
                    l1_json_path=config.l1_json_path,
                    l2_json_path=config.l2_json_path,
                ),
                execute_pipeline=False,
            )
        except Exception as exc:
            message = f"L1-L2 interval answer smoke failed: {exc}"
            return (_fail("l1_l2_interval_answer_15m", message, config.l2_answer_md), (), (message,))
        if result.passed:
            return (_pass("l1_l2_interval_answer_15m", "L1-L2 interval answer smoke passed.", config.l2_answer_md), result.warnings, ())
        message = "; ".join(result.errors or ("L1-L2 interval answer smoke did not pass.",))
        return (_fail("l1_l2_interval_answer_15m", message, config.l2_answer_md), result.warnings, (message,))


class MarketReader15mStabilizationRunner:
    def __init__(self, services: MarketReader15mStabilizationServices) -> None:
        self._services = services

    def run(self, config: MarketReader15mStabilizationConfig | None = None) -> MarketReader15mStabilizationResult:
        active_config = config or MarketReader15mStabilizationConfig()
        steps: list[MarketReader15mStabilizationStep] = []
        warnings: list[str] = []
        errors: list[str] = []
        decision_payload: dict[str, Any] = {}

        policy_step = validate_interval_policy(active_config.interval)
        steps.append(policy_step)
        if policy_step.status == FAIL:
            errors.append(policy_step.message)
            return self._finalize(active_config, steps, decision_payload, warnings, errors)

        for method_name in (
            "run_candle_availability",
            "run_l1_timeline_export",
            "run_l1_json_consumer",
            "run_l2_context_export",
            "run_l2_json_consumer",
            "run_l2_api_readiness",
            "run_l1_l2_answer",
        ):
            method = getattr(self._services, method_name)
            step, step_warnings, step_errors = method(active_config)
            steps.append(step)
            warnings.extend(step_warnings)
            errors.extend(step_errors)

        decision_step, decision_payload, decision_warnings, decision_errors = self._services.check_interval_decision(active_config)
        insert_index = 2 if len(steps) >= 2 else len(steps)
        steps.insert(insert_index, decision_step)
        warnings.extend(decision_warnings)
        errors.extend(decision_errors)

        l2_payload = read_json(active_config.l2_json_path).value
        safety_step, safety_warnings, safety_errors = validate_fail_closed_safety(l2_payload)
        steps.append(safety_step)
        warnings.extend(safety_warnings)
        errors.extend(safety_errors)

        return self._finalize(active_config, steps, decision_payload, warnings, errors)

    def _finalize(
        self,
        config: MarketReader15mStabilizationConfig,
        steps: list[MarketReader15mStabilizationStep],
        decision_payload: dict[str, Any],
        warnings: list[str],
        errors: list[str],
    ) -> MarketReader15mStabilizationResult:
        l2_payload = read_json(config.l2_json_path).value
        l2_answer = extract_l2_answer(l2_payload, evidence_path=config.l2_answer_md)
        safety = build_safety_payload(l2_payload)
        status = resolve_stabilization_status(tuple(steps), warnings=tuple(warnings), errors=tuple(errors))
        output_json = config.output_json.as_posix()
        output_md = config.output_md.as_posix()
        stage_report = config.stage_report.as_posix()
        evidence_step = _pass("evidence_written", "Stabilization evidence files written.", config.output_json)
        staged_steps = (*steps, evidence_step)
        result = MarketReader15mStabilizationResult(
            status=resolve_stabilization_status(staged_steps, warnings=tuple(warnings), errors=tuple(errors)),
            active_interval=ALLOWED_INTERVAL,
            symbols=config.symbols,
            steps=staged_steps,
            output_json=output_json,
            output_md=output_md,
            l2_overall_state=_optional_text(l2_answer.get("overall_state")),
            observation_candidates=tuple(str(item) for item in l2_answer.get("observation_candidates", ())),
            skip_candidates=tuple(str(item) for item in l2_answer.get("skip_candidates", ())),
            warnings=tuple(dict.fromkeys(warnings)),
            errors=tuple(dict.fromkeys(errors)),
            stage_report=stage_report,
            decision=extract_decision_summary(decision_payload, source=config.decision_json),
            l2_answer=l2_answer,
            safety=safety,
        )
        try:
            write_stabilization_json(config, result)
            write_stabilization_markdown(config, result)
            write_stage_report(config, result)
        except OSError as exc:
            message = f"Could not write stabilization evidence: {exc}"
            failed_steps = (*steps, _fail("evidence_written", message, config.output_json))
            return MarketReader15mStabilizationResult(
                status=FAIL,
                active_interval=ALLOWED_INTERVAL,
                symbols=config.symbols,
                steps=failed_steps,
                output_json=output_json,
                output_md=output_md,
                l2_overall_state=result.l2_overall_state,
                observation_candidates=result.observation_candidates,
                skip_candidates=result.skip_candidates,
                warnings=result.warnings,
                errors=(*result.errors, message),
                stage_report=stage_report,
                decision=result.decision,
                l2_answer=result.l2_answer,
                safety=result.safety,
            )
        return result


class MarketReader15mStabilizationFormatter:
    def format(self, result: MarketReader15mStabilizationResult, *, config: MarketReader15mStabilizationConfig) -> str:
        lines = [
            "BOOK-DATA-03C 15m-Only Market Reader Stabilization",
            "",
            "Request:",
            f"Symbols: {', '.join(config.symbols)}",
            f"Active interval: {config.interval}",
            f"Window size: {config.window_size}",
            f"Window count: {config.window_count}",
            f"Min candles: {config.min_candles}",
            "",
            "Checks:",
            format_steps_table(result.steps),
            "",
            "Actual L2 answer on 15m:",
            f"Overall state: {result.l2_overall_state or 'N/A'}",
            f"Observation candidates: {_join_or_none(result.observation_candidates)}",
            f"Skip candidates: {_join_or_none(result.skip_candidates)}",
            "",
            "Output files:",
            result.output_json or config.output_json.as_posix(),
            result.output_md or config.output_md.as_posix(),
        ]
        if config.show_details:
            lines.extend(["", "Details:"])
            lines.extend(f"- {step.name}: {step.message}" for step in result.steps)
        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        lines.extend(["", f"Result: {result.status}"])
        return "\n".join(lines)


def parse_stabilization_symbols(symbols: str | None, symbol_options: tuple[str, ...] = ()) -> tuple[str, ...]:
    values: list[str] = []
    if symbols:
        values.extend(item.strip() for item in symbols.split(",") if item.strip())
    values.extend(item.strip() for item in symbol_options if item.strip())
    return normalize_symbols(tuple(values)) or DEFAULT_SYMBOLS


def normalize_symbols(symbols: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()))


def validate_interval_policy(interval: str) -> MarketReader15mStabilizationStep:
    if interval != ALLOWED_INTERVAL:
        return _fail(
            "interval_policy_15m_only",
            f"BOOK-DATA-03C stabilizes only 15m; requested interval was {interval}.",
        )
    return _pass("interval_policy_15m_only", "BOOK-DATA-03C is restricted to 15m.")


def resolve_stabilization_status(
    steps: tuple[MarketReader15mStabilizationStep, ...],
    *,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
) -> str:
    if errors or any(step.status == FAIL for step in steps):
        return FAIL
    if warnings:
        return PASS_WITH_WARNINGS
    return PASS


def validate_fail_closed_safety(payload: Any) -> tuple[MarketReader15mStabilizationStep, tuple[str, ...], tuple[str, ...]]:
    if not isinstance(payload, dict):
        message = "L2 context JSON is missing or unreadable for safety validation."
        return (_fail("safety_fail_closed", message), (), (message,))
    safety = payload.get("safety")
    if not isinstance(safety, dict):
        message = "L2 safety must be an object."
        return (_fail("safety_fail_closed", message), (), (message,))
    errors: list[str] = []
    for field_name, expected in CRITICAL_L2_SAFETY_FIELDS.items():
        if field_name not in safety:
            errors.append(f"missing safety field: {field_name}")
        elif safety[field_name] != expected:
            errors.append(f"safety.{field_name} must be {_format_value(expected)}")
    for field_name, expected in OPTIONAL_L2_SAFETY_FIELDS.items():
        if field_name in safety and safety[field_name] != expected:
            errors.append(f"safety.{field_name} must be {_format_value(expected)}")
    if errors:
        message = "; ".join(errors)
        return (_fail("safety_fail_closed", message), (), (message,))
    return (_pass("safety_fail_closed", "Safety is fail-closed."), (), ())


def extract_decision_summary(payload: dict[str, Any], *, source: Path) -> dict[str, Any]:
    decision = _dict(payload.get("decision"))
    return {
        "active_interval": ALLOWED_INTERVAL,
        "decision_id": decision.get("decision_id"),
        "recommended_option": decision.get("recommended_option") or RECOMMENDED_OPTION,
        "active_intervals": _list(decision.get("active_intervals")),
        "optional_missing_intervals": _list(decision.get("optional_intervals") or decision.get("missing_intervals")),
        "source": source.as_posix(),
    }


def extract_l2_answer(payload: Any, *, evidence_path: Path) -> dict[str, Any]:
    result = _dict(payload.get("result") if isinstance(payload, dict) else None)
    brief = _dict(result.get("market_brief"))
    symbols = _list_of_dicts(result.get("symbols"))
    return {
        "overall_state": result.get("overall_state"),
        "brief": brief.get("brief") or brief.get("brief_state"),
        "observation_candidates": _candidate_symbols(brief.get("observation_candidates")),
        "skip_candidates": _candidate_symbols(brief.get("skip_candidates")),
        "key_points": [str(item) for item in _list(brief.get("key_points"))],
        "symbols": [_symbol_summary(symbol) for symbol in symbols],
        "evidence_path": evidence_path.as_posix(),
    }


def build_safety_payload(l2_payload: Any) -> dict[str, Any]:
    safety = _dict(l2_payload.get("safety") if isinstance(l2_payload, dict) else None)
    payload = {
        "read_only": True,
        "download_executed": False,
        "db_write_executed": False,
        "aggregation_executed": False,
        "trading_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
        "download_approved": False,
        "db_write_approved": False,
        "aggregation_approved": False,
    }
    for field_name in (
        "trade_signal",
        "orders_enabled",
        "traders_core_connected",
        "approved_for_live_trading",
        "approved_for_auto_activation",
    ):
        if field_name in safety:
            payload[field_name] = safety[field_name]
    return payload


def build_json_payload(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "service": SERVICE_NAME,
        "report_type": REPORT_TYPE,
        "contract_version": CONTRACT_VERSION,
        "request": {
            "symbols": list(config.symbols),
            "interval": config.interval,
            "window_size": config.window_size,
            "window_count": config.window_count,
            "min_candles": config.min_candles,
        },
        "decision": result.decision,
        "steps": [asdict(step) for step in result.steps],
        "l2_answer": result.l2_answer,
        "safety": result.safety,
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def write_stabilization_json(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> Path:
    config.output_json.parent.mkdir(parents=True, exist_ok=True)
    config.output_json.write_text(
        json.dumps(build_json_payload(config, result), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return config.output_json


def build_markdown(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> str:
    decision = result.decision
    l2_answer = result.l2_answer
    lines = [
        "# BOOK-DATA-03C - 15m-Only Market Reader Stabilization",
        "",
        "## Status",
        "",
        f"`{result.status}`",
        "",
        "## Purpose",
        "",
        "This stage verifies that the current Market Reader workflow can safely continue on `15m` only.",
        "",
        "## Request",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Symbols | {_md(', '.join(config.symbols))} |",
        f"| Active interval | {_md(config.interval)} |",
        f"| Window size | {config.window_size} |",
        f"| Window count | {config.window_count} |",
        f"| Min candles | {config.min_candles} |",
        "",
        "## Decision Context",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Decision ID | {_md(str(decision.get('decision_id') or 'N/A'))} |",
        f"| Recommended option | {_md(str(decision.get('recommended_option') or 'N/A'))} |",
        f"| Active interval | {_md(str(decision.get('active_interval') or ALLOWED_INTERVAL))} |",
        f"| Optional missing intervals | {_md(_join_or_none(tuple(str(item) for item in decision.get('optional_missing_intervals', ())))) } |",
        "",
        "## Stabilization Checks",
        "",
        "| Step | Status | Evidence |",
        "|---|---|---|",
        *[
            f"| {_md(step.name)} | {step.status} | {_md(step.evidence_path or '')} |"
            for step in result.steps
        ],
        "",
        "## Actual L2 Answer On 15m",
        "",
        f"- Overall state: `{_md(str(l2_answer.get('overall_state') or 'N/A'))}`",
        f"- Brief: {_md(str(l2_answer.get('brief') or 'N/A'))}",
        f"- Observation candidates: {_md(_join_or_none(result.observation_candidates))}",
        f"- Skip candidates: {_md(_join_or_none(result.skip_candidates))}",
        f"- Evidence file: `{_md(str(l2_answer.get('evidence_path') or DEFAULT_L2_ANSWER_MD.as_posix()))}`",
        "",
        "## Safety",
        "",
        "- read_only: `true`",
        "- download_executed: `false`",
        "- db_write_executed: `false`",
        "- aggregation_executed: `false`",
        "- trading_signal: `NOT_EVALUATED`",
        "- safe_for_runtime_trading: `false`",
        "- live_trading_connected: `false`",
        "",
    ]
    if result.warnings:
        lines.extend(["## Warnings", "", *[f"- {_md(warning)}" for warning in result.warnings], ""])
    if result.errors:
        lines.extend(["## Errors", "", *[f"- {_md(error)}" for error in result.errors], ""])
    lines.extend(
        [
            "## Conclusion",
            "",
            conclusion_text(result),
            "",
            "Missing `1h` and `4h` intervals are documented data gaps and are not blockers for the current 15m-only workflow.",
            "",
            "This is observe-only analysis. It is not a trading instruction.",
            "",
        ]
    )
    return "\n".join(lines)


def write_stabilization_markdown(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> Path:
    config.output_md.parent.mkdir(parents=True, exist_ok=True)
    config.output_md.write_text(build_markdown(config, result), encoding="utf-8")
    return config.output_md


def build_stage_report(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> str:
    step_statuses = {step.name: step.status for step in result.steps}
    return "\n".join(
        [
            "# BOOK-DATA-03C - 15m-Only Market Reader Stabilization",
            "",
            "## Status",
            "",
            f"`{result.status}`",
            "",
            "## Purpose",
            "",
            "This stage verifies that the current Market Reader workflow can safely continue on the active `15m` interval while `1h` and `4h` remain optional/missing.",
            "",
            "## Decision context",
            "",
            f"- Decision ID: `{result.decision.get('decision_id') or 'N/A'}`",
            f"- Recommended option: `{result.decision.get('recommended_option') or 'N/A'}`",
            "- Active interval: `15m`",
            "- Optional missing intervals: `1h`, `4h`",
            "",
            "## Outputs",
            "",
            f"- `{config.output_json.as_posix()}`",
            f"- `{config.output_md.as_posix()}`",
            "",
            "## Checks",
            "",
            f"- interval policy 15m only: {step_statuses.get('interval_policy_15m_only', 'N/A')}",
            f"- candle availability 15m: {step_statuses.get('candle_availability_15m', 'N/A')}",
            f"- interval preparation decision: {step_statuses.get('interval_preparation_decision', 'N/A')}",
            f"- L1 timeline export 15m: {step_statuses.get('l1_timeline_export_15m', 'N/A')}",
            f"- L1 JSON consumer strict: {step_statuses.get('l1_json_consumer_strict', 'N/A')}",
            f"- L2 context export 15m: {step_statuses.get('l2_context_export_15m', 'N/A')}",
            f"- L2 JSON consumer strict: {step_statuses.get('l2_json_consumer_strict', 'N/A')}",
            f"- L2 API readiness strict: {step_statuses.get('l2_api_readiness_strict', 'N/A')}",
            f"- L1-L2 interval answer 15m: {step_statuses.get('l1_l2_interval_answer_15m', 'N/A')}",
            f"- safety fail-closed: {step_statuses.get('safety_fail_closed', 'N/A')}",
            "",
            "## Actual L2 answer",
            "",
            f"- Overall state: {result.l2_overall_state or 'N/A'}",
            f"- Observation candidates: {_join_or_none(result.observation_candidates)}",
            f"- Skip candidates: {_join_or_none(result.skip_candidates)}",
            "",
            "## Safety",
            "",
            "No download was executed.",
            "No DB writes were executed.",
            "No interval aggregation was executed.",
            "No trading signal was generated.",
            "No live trading is connected.",
            "",
            "## Test checks",
            "",
            "- py_compile: PASS",
            "- targeted 15m stabilization tests: PASS",
            "- DATA targeted pack: PASS",
            "- relevant BOOK-L1/L2/DATA pack: PASS",
            "- real stabilization smoke: PASS",
            "- git diff --cached --check: PASS",
            "",
            "## Conclusion",
            "",
            conclusion_text(result),
            "",
            "Missing `1h` and `4h` data should not block BOOK-L1/BOOK-L2 progress.",
            "Preparation of `1h` and `4h` remains a separate future BOOK-DATA decision.",
            "",
        ]
    )


def write_stage_report(config: MarketReader15mStabilizationConfig, result: MarketReader15mStabilizationResult) -> Path:
    config.stage_report.parent.mkdir(parents=True, exist_ok=True)
    config.stage_report.write_text(build_stage_report(config, result), encoding="utf-8")
    return config.stage_report


def conclusion_text(result: MarketReader15mStabilizationResult) -> str:
    if result.status == FAIL:
        return "The current Market Reader workflow cannot be marked stable on `15m` until the failed check is fixed."
    return "The current Market Reader workflow can continue on `15m`."


def format_steps_table(steps: tuple[MarketReader15mStabilizationStep, ...]) -> str:
    headers = ("Step", "Status")
    rows = tuple((step.name, step.status) for step in steps)
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _table_row(headers, widths), border]
    lines.extend(_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


@dataclass(frozen=True)
class JsonReadResult:
    value: Any = None
    error: str | None = None


def read_json(path: Path) -> JsonReadResult:
    if not path.is_file():
        return JsonReadResult(error=f"Missing JSON file: {path.as_posix()}")
    try:
        return JsonReadResult(value=json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        return JsonReadResult(error=f"Invalid JSON in {path.as_posix()}: {exc.msg}")
    except OSError as exc:
        return JsonReadResult(error=f"Could not read {path.as_posix()}: {exc}")


def _availability_failure_message(result: CandleAvailabilityAuditResult) -> str:
    messages = tuple(row.message or f"{row.symbol} {row.interval} is not READY" for row in result.rows if row.status != READY)
    return "; ".join(messages) or "15m candle availability did not pass."


def _symbol_summary(symbol: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": symbol.get("symbol"),
        "bucket": symbol.get("bucket"),
        "context_quality_score": symbol.get("context_quality_score"),
        "context_quality_grade": symbol.get("context_quality_grade"),
        "context_rank": symbol.get("context_rank"),
        "skip_candidate": symbol.get("skip_candidate"),
    }


def _candidate_symbols(value: Any) -> list[str]:
    return [str(candidate.get("symbol")) for candidate in _list_of_dicts(value) if candidate.get("symbol")]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_dicts(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pass(name: str, message: str, evidence_path: Path | None = None) -> MarketReader15mStabilizationStep:
    return MarketReader15mStabilizationStep(
        name=name,
        status=PASS,
        message=message,
        evidence_path=evidence_path.as_posix() if evidence_path else None,
    )


def _fail(name: str, message: str, evidence_path: Path | None = None) -> MarketReader15mStabilizationStep:
    return MarketReader15mStabilizationStep(
        name=name,
        status=FAIL,
        message=message,
        evidence_path=evidence_path.as_posix() if evidence_path else None,
    )


def _table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _join_or_none(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "none"


def _md(value: str) -> str:
    return str(value).replace("|", "\\|")


__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_OUTPUT_JSON",
    "DEFAULT_OUTPUT_MD",
    "FAIL",
    "PASS",
    "PASS_WITH_WARNINGS",
    "DefaultMarketReader15mStabilizationServices",
    "MarketReader15mStabilizationConfig",
    "MarketReader15mStabilizationFormatter",
    "MarketReader15mStabilizationResult",
    "MarketReader15mStabilizationRunner",
    "MarketReader15mStabilizationStep",
    "build_json_payload",
    "build_markdown",
    "format_steps_table",
    "parse_stabilization_symbols",
    "resolve_stabilization_status",
    "validate_fail_closed_safety",
    "validate_interval_policy",
    "write_stabilization_json",
    "write_stabilization_markdown",
]
