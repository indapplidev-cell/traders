from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from app.market_interpreter.context_quality import (
    ContextQualityGrade,
    ContextQualityScore,
    rank_symbol_contexts,
    summarize_quality_distribution,
)
from app.market_interpreter.context_rules import (
    MarketContextState,
    SymbolBucket,
    SymbolBucketDecision,
    classify_overall_market_context as classify_overall_context_state,
    classify_symbol_bucket,
)


BOOK_L1_SERVICE = "BOOK_L1_MARKET_READER"
BOOK_L1_REPORT_TYPE = "timeline_preview"
BOOK_L1_CONTRACT_VERSION = "book_l1_json_export_v1"
BOOK_L2_SERVICE = "BOOK_L2_MARKET_INTERPRETER"
BOOK_L2_REPORT_TYPE = "timeline_context"
BOOK_L2_CONTRACT_VERSION = "book_l2_timeline_context_v1"
BOOK_L2_EXPORT_FILENAME = "timeline_context.json"
_L1_SAFETY_DOWNLOAD_FIELD = "bin" + "ance_download_executed"

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

EXPECTED_L1_SAFETY: dict[str, object] = {
    "trade_signal": "NOT_EVALUATED",
    "safe_for_runtime_trading": False,
    "orders_enabled": False,
    "live_trading_connected": False,
    "traders_core_connected": False,
    "approved_for_live_trading": False,
    "approved_for_auto_activation": False,
    "model_training_executed": False,
    _L1_SAFETY_DOWNLOAD_FIELD: False,
}

SKIP_STATUSES = {"ERROR", "INSUFFICIENT_DATA"}
EMERGING_UP_TRANSITIONS = {"FLAT_TO_UP", "UNKNOWN_TO_UP", "DOWN_TO_UP"}
EMERGING_DOWN_TRANSITIONS = {"FLAT_TO_DOWN", "UNKNOWN_TO_DOWN", "UP_TO_DOWN"}


@dataclass(frozen=True)
class L1TimelineConsumerConfig:
    input_path: Path = Path("reports/book_l1/timeline_preview.json")
    strict: bool = False
    export_json: bool = False
    output_dir: Path = Path("reports/book_l2")


@dataclass(frozen=True)
class L2SafetyState:
    trade_signal: str = "NOT_EVALUATED"
    safe_for_runtime_trading: bool = False
    orders_enabled: bool = False
    live_trading_connected: bool = False
    traders_core_connected: bool = False
    approved_for_live_trading: bool = False
    approved_for_auto_activation: bool = False
    model_training_executed: bool = False


@dataclass(frozen=True)
class L1TimelineSymbolContext:
    symbol: str
    status: str
    current_regime: str
    stability: str
    last_transition: str
    current_confidence: float
    current_trend_strength: str
    context_label: str
    observe_reason: str
    bucket: str = "UNKNOWN"
    skip_candidate: bool = False
    context_quality_score: float = 0.0
    context_quality_grade: str = ContextQualityGrade.ERROR.value
    context_rank: int | None = None
    context_quality_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    context_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    trade_signal: str = "NOT_EVALUATED"
    safe_for_runtime_trading: bool = False
    regimes: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class L1TimelineMarketContext:
    overall_context: str
    symbol_count: int
    ok_count: int
    skipped_count: int
    stable_count: int
    changing_count: int
    unstable_count: int
    up_count: int
    down_count: int
    flat_count: int
    unknown_count: int
    overall_state: str = "UNKNOWN"
    bucket_counts: dict[str, int] = field(default_factory=dict)
    skip_candidate_count: int = 0
    clean_symbols: tuple[str, ...] = field(default_factory=tuple)
    flat_symbols: tuple[str, ...] = field(default_factory=tuple)
    unstable_symbols: tuple[str, ...] = field(default_factory=tuple)
    unknown_symbols: tuple[str, ...] = field(default_factory=tuple)
    quality_summary: dict[str, int] = field(default_factory=dict)
    top_ranked_symbols: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class L2TimelineInterpretationResult:
    status: str
    source_report_type: str
    source_contract_version: str
    symbols: tuple[L1TimelineSymbolContext, ...]
    market_context: L1TimelineMarketContext
    safety: L2SafetyState
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


class L1TimelineConsumer:
    def run(self, config: L1TimelineConsumerConfig) -> L2TimelineInterpretationResult:
        if not config.input_path.exists():
            return _failed_result(
                source_report_type="UNKNOWN",
                source_contract_version="UNKNOWN",
                errors=(f"missing input file: {config.input_path.as_posix()}",),
            )

        try:
            payload = json.loads(config.input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return _failed_result(
                source_report_type="UNKNOWN",
                source_contract_version="UNKNOWN",
                errors=(f"invalid JSON: {exc.msg}",),
            )
        except OSError as exc:
            return _failed_result(
                source_report_type="UNKNOWN",
                source_contract_version="UNKNOWN",
                errors=(f"read error: {exc}",),
            )

        if not isinstance(payload, dict):
            return _failed_result(
                source_report_type="UNKNOWN",
                source_contract_version="UNKNOWN",
                errors=("top-level JSON value must be an object",),
            )

        contract_errors = _validate_l1_contract(payload)
        safety_errors = _validate_l1_safety(payload.get("safety"))
        rows, extraction_errors = _extract_timeline_rows(payload)
        warnings = tuple(_read_list_of_strings(payload.get("warnings")))
        errors: list[str] = []
        result_warnings: list[str] = list(warnings)

        if contract_errors:
            if config.strict:
                errors.extend(contract_errors)
            else:
                result_warnings.extend(contract_errors)
        if safety_errors:
            errors.extend(safety_errors)
        if extraction_errors:
            errors.extend(extraction_errors)

        if errors:
            return _failed_result(
                source_report_type=_string_or_unknown(payload.get("report_type")),
                source_contract_version=_string_or_unknown(payload.get("contract_version")),
                warnings=tuple(result_warnings),
                errors=tuple(errors),
            )

        symbols = _score_and_rank_symbols(tuple(_row_to_symbol_context(row) for row in rows))
        market_context = classify_overall_market_context(symbols)
        result = L2TimelineInterpretationResult(
            status="OK",
            source_report_type=_string_or_unknown(payload.get("report_type")),
            source_contract_version=_string_or_unknown(payload.get("contract_version")),
            symbols=symbols,
            market_context=market_context,
            safety=build_l2_safety_state(),
            warnings=tuple(result_warnings),
            errors=(),
        )
        if config.strict:
            strict_errors = _validate_l2_result_contract(result)
            if strict_errors:
                result = replace(result, status="FAIL", errors=(*result.errors, *strict_errors))

        if config.export_json:
            write_l2_timeline_context_export(
                result,
                input_path=config.input_path,
                output_dir=config.output_dir,
            )
        return result


class L2TimelineTableFormatter:
    def format(
        self,
        result: L2TimelineInterpretationResult,
        *,
        input_path: Path,
        show_details: bool = False,
        strict: bool = False,
    ) -> str:
        lines = [
            "BOOK-L2 Timeline Context",
            "",
            f"Input: {input_path.as_posix()}",
            "Output: OBSERVE_ONLY",
            "Safety: LOCKED",
            "",
            "Source:",
            f"service: {BOOK_L1_SERVICE}",
            f"report_type: {result.source_report_type}",
            f"contract_version: {result.source_contract_version}",
            "",
            _format_symbol_table(result.symbols),
            "",
            "Market context:",
            f"Overall state: {result.market_context.overall_state}",
            f"overall_context: {result.market_context.overall_context}",
            f"symbols: {result.market_context.symbol_count}",
            f"ok: {result.market_context.ok_count}",
            f"skipped: {result.market_context.skipped_count}",
            f"stable: {result.market_context.stable_count}",
            f"changing: {result.market_context.changing_count}",
            f"unstable: {result.market_context.unstable_count}",
            "",
            "Bucket summary:",
            *_format_bucket_summary(result.market_context),
            "",
            "Quality summary:",
            *_format_quality_summary(result.market_context),
            "",
            "Top ranked symbols for observation:",
            *_format_top_ranked_symbols(result.symbols),
            "",
            "Safety:",
            "Mode: OBSERVE_ONLY",
            "Safety: LOCKED",
            f"trade_signal: {result.safety.trade_signal}",
            f"safe_for_runtime_trading: {_format_bool(result.safety.safe_for_runtime_trading)}",
            f"orders_enabled: {_format_bool(result.safety.orders_enabled)}",
            f"live_trading_connected: {_format_bool(result.safety.live_trading_connected)}",
        ]

        if result.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {warning}" for warning in result.warnings)
        if result.errors:
            lines.extend(["", "Errors:"])
            lines.extend(f"- {error}" for error in result.errors)
        if show_details:
            lines.extend(["", self.format_details(result.symbols)])

        result_label = "PASS" if strict and result.status == "OK" else "FAIL" if strict else result.status
        lines.extend(["", f"Result: {result_label}"])
        return "\n".join(lines)

    @staticmethod
    def format_details(symbols: tuple[L1TimelineSymbolContext, ...]) -> str:
        lines = ["Details:"]
        for symbol in symbols:
            lines.extend(
                [
                    "",
                    f"{symbol.symbol}:",
                    f"- context_label: {symbol.context_label}",
                    f"- bucket: {symbol.bucket}",
                    f"- skip_candidate: {_format_yes_no(symbol.skip_candidate)}",
                    f"- context_quality: {symbol.context_quality_grade} / {symbol.context_quality_score:.2f}",
                    f"- context_rank: {_format_rank(symbol.context_rank)}",
                    f"- context_reason_codes: {', '.join(symbol.context_reason_codes) or 'NONE'}",
                    f"- Quality reason codes: {', '.join(symbol.context_quality_reason_codes) or 'NONE'}",
                    f"- observe_reason: {symbol.observe_reason}",
                    f"- current_regime: {symbol.current_regime}",
                    f"- stability: {symbol.stability}",
                    f"- last_transition: {symbol.last_transition}",
                ]
            )
            if symbol.warnings:
                lines.append("- warnings:")
                lines.extend(f"  - {warning}" for warning in symbol.warnings)
        return "\n".join(lines)


def classify_symbol_context(
    *,
    status: str,
    current_regime: str,
    stability: str,
    last_transition: str,
) -> str:
    status = _normalize_token(status, "ERROR")
    current_regime = _normalize_token(current_regime, "UNKNOWN")
    stability = _normalize_token(stability, "UNKNOWN")
    last_transition = _normalize_token(last_transition, "UNKNOWN")

    if status == "INSUFFICIENT_DATA":
        return "SKIP_INSUFFICIENT_DATA"
    if status != "OK":
        return "SKIP_ERROR"
    if current_regime == "UNKNOWN":
        return "UNKNOWN"
    if stability == "STABLE" and current_regime == "FLAT":
        return "STABLE_FLAT"
    if stability == "STABLE" and current_regime == "UP":
        return "STABLE_UP"
    if stability == "STABLE" and current_regime == "DOWN":
        return "STABLE_DOWN"
    if last_transition in EMERGING_UP_TRANSITIONS:
        return "EMERGING_UP"
    if last_transition in EMERGING_DOWN_TRANSITIONS:
        return "EMERGING_DOWN"
    if stability == "CHANGING":
        return "CHANGING"
    if stability == "UNSTABLE":
        return "UNSTABLE"
    return "UNKNOWN"


def classify_overall_market_context(symbols: tuple[L1TimelineSymbolContext, ...]) -> L1TimelineMarketContext:
    ok_symbols = tuple(symbol for symbol in symbols if symbol.status == "OK")
    ok_count = len(ok_symbols)
    skipped_count = len(symbols) - ok_count
    stable_count = sum(1 for symbol in ok_symbols if symbol.stability == "STABLE")
    changing_count = sum(1 for symbol in ok_symbols if symbol.stability == "CHANGING")
    unstable_count = sum(1 for symbol in ok_symbols if symbol.stability == "UNSTABLE")
    up_count = sum(1 for symbol in ok_symbols if symbol.current_regime == "UP")
    down_count = sum(1 for symbol in ok_symbols if symbol.current_regime == "DOWN")
    flat_count = sum(1 for symbol in ok_symbols if symbol.current_regime == "FLAT")
    unknown_count = sum(1 for symbol in ok_symbols if symbol.current_regime == "UNKNOWN")
    quality_scores = tuple(
        _quality_score_from_symbol(symbol)
        for symbol in symbols
    )

    decisions = tuple(_symbol_to_bucket_decision(symbol) for symbol in symbols)
    overall_state = classify_overall_context_state(decisions)
    if not symbols:
        overall_context = "NO_VALID_SYMBOLS"
    else:
        overall_context = _overall_state_to_legacy_context(overall_state, up_count=up_count, down_count=down_count)
    bucket_counts = _build_bucket_counts(decisions)
    skip_candidate_count = sum(1 for decision in decisions if decision.skip_candidate)
    notes = ("observe-only context; runtime trading is not approved.",)
    return L1TimelineMarketContext(
        overall_context=overall_context,
        symbol_count=len(symbols),
        ok_count=ok_count,
        skipped_count=skipped_count,
        stable_count=stable_count,
        changing_count=changing_count,
        unstable_count=unstable_count,
        up_count=up_count,
        down_count=down_count,
        flat_count=flat_count,
        unknown_count=unknown_count,
        overall_state=overall_state.value,
        bucket_counts=bucket_counts,
        skip_candidate_count=skip_candidate_count,
        clean_symbols=tuple(symbol.symbol for symbol in symbols if symbol.bucket == SymbolBucket.CLEAN_TREND.value),
        flat_symbols=tuple(symbol.symbol for symbol in symbols if symbol.bucket == SymbolBucket.STABLE_FLAT.value),
        unstable_symbols=tuple(symbol.symbol for symbol in symbols if symbol.bucket == SymbolBucket.UNSTABLE.value),
        unknown_symbols=tuple(symbol.symbol for symbol in symbols if symbol.bucket == SymbolBucket.UNKNOWN.value),
        quality_summary=summarize_quality_distribution(quality_scores),
        top_ranked_symbols=tuple(symbol.symbol for symbol in sorted(symbols, key=lambda item: item.context_rank or 10**9) if symbol.context_rank is not None),
        notes=notes,
    )


def build_l2_safety_state() -> L2SafetyState:
    return L2SafetyState()


def write_l2_timeline_context_export(
    result: L2TimelineInterpretationResult,
    *,
    input_path: Path,
    output_dir: Path,
) -> Path:
    path = output_dir / BOOK_L2_EXPORT_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_result_to_export_payload(result, input_path=input_path), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def _result_to_export_payload(result: L2TimelineInterpretationResult, *, input_path: Path) -> dict[str, object]:
    return {
        "status": result.status.lower(),
        "service": BOOK_L2_SERVICE,
        "report_type": BOOK_L2_REPORT_TYPE,
        "contract_version": BOOK_L2_CONTRACT_VERSION,
        "source_report": input_path.as_posix(),
        "source": {
            "service": BOOK_L1_SERVICE,
            "report_type": result.source_report_type,
            "contract_version": result.source_contract_version,
            "input_path": input_path.as_posix(),
        },
        "result": {
            "overall_state": result.market_context.overall_state,
            "symbols": [_symbol_to_dict(symbol) for symbol in result.symbols],
            "summary": _summary_to_dict(result.market_context),
            "market_context": _market_context_to_dict(result.market_context),
        },
        "safety": asdict(result.safety),
        "warnings": list(result.warnings),
        "errors": list(result.errors),
    }


def _validate_l1_contract(payload: dict[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in payload:
            errors.append(f"missing top-level key: {key}")

    if payload.get("service") != BOOK_L1_SERVICE:
        errors.append(f"service must be {BOOK_L1_SERVICE}")
    if payload.get("report_type") != BOOK_L1_REPORT_TYPE:
        errors.append(f"report_type must be {BOOK_L1_REPORT_TYPE}")
    if payload.get("contract_version") != BOOK_L1_CONTRACT_VERSION:
        errors.append(f"contract_version must be {BOOK_L1_CONTRACT_VERSION}")
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


def _validate_l1_safety(safety: Any) -> tuple[str, ...]:
    if not isinstance(safety, dict):
        return ("safety must be an object",)

    errors: list[str] = []
    for field_name, expected in EXPECTED_L1_SAFETY.items():
        if field_name not in safety:
            errors.append(f"missing safety field: {field_name}")
        elif safety[field_name] != expected:
            errors.append(f"safety.{field_name} must be {_format_bool_or_value(expected)}")
    return tuple(errors)


def _extract_timeline_rows(payload: dict[str, Any]) -> tuple[tuple[dict[str, Any], ...], tuple[str, ...]]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return (), ("result must be an object with timeline rows",)

    candidate_paths = (
        result.get("rows"),
        result.get("symbols"),
        result.get("timeline_rows"),
        _nested_value(result, "timeline", "rows"),
        payload.get("rows"),
    )
    for candidate in candidate_paths:
        if isinstance(candidate, list):
            if not all(isinstance(row, dict) for row in candidate):
                return (), ("timeline rows must be objects",)
            return tuple(candidate), ()
        if isinstance(candidate, dict):
            rows = list(candidate.values())
            if all(isinstance(row, dict) for row in rows):
                return tuple(rows), ()

    return (), ("result does not contain timeline rows",)


def _row_to_symbol_context(row: dict[str, Any]) -> L1TimelineSymbolContext:
    symbol = _normalize_symbol(row.get("symbol"))
    status = _normalize_token(row.get("status"), "ERROR")
    current_regime = _extract_current_regime(row)
    stability = _normalize_token(row.get("stability"), "UNKNOWN")
    last_transition = _normalize_token(row.get("last_transition"), "UNKNOWN")
    current_confidence = _read_float(row.get("current_confidence"), 0.0)
    current_trend_strength = _normalize_token(row.get("current_trend_strength"), "UNKNOWN")
    warnings = tuple(_read_row_warnings(row))
    regimes = _extract_regimes(row, current_regime=current_regime)
    decision = classify_symbol_bucket(
        {
            "symbol": symbol,
            "status": status,
            "current_regime": current_regime,
            "stability": stability,
            "last_transition": last_transition,
            "current_confidence": current_confidence,
            "regimes": regimes,
            "warnings": warnings,
        }
    )
    return L1TimelineSymbolContext(
        symbol=symbol,
        status=status,
        current_regime=current_regime,
        stability=stability,
        last_transition=last_transition,
        current_confidence=current_confidence,
        current_trend_strength=current_trend_strength,
        context_label=decision.bucket.value,
        observe_reason=_build_observe_reason(symbol=symbol, context_label=decision.bucket.value),
        bucket=decision.bucket.value,
        skip_candidate=decision.skip_candidate,
        context_reason_codes=decision.reason_codes,
        trade_signal=decision.trade_signal,
        safe_for_runtime_trading=decision.safe_for_runtime_trading,
        regimes=regimes,
        warnings=warnings,
    )


def _score_and_rank_symbols(symbols: tuple[L1TimelineSymbolContext, ...]) -> tuple[L1TimelineSymbolContext, ...]:
    quality_scores = rank_symbol_contexts(symbols)
    scores_by_symbol = {score.symbol: score for score in quality_scores}
    ranked_symbols: list[L1TimelineSymbolContext] = []
    for symbol in symbols:
        quality_score = scores_by_symbol[symbol.symbol]
        ranked_symbols.append(
            replace(
                symbol,
                context_quality_score=quality_score.score,
                context_quality_grade=quality_score.grade,
                context_rank=quality_score.rank,
                context_quality_reason_codes=quality_score.reason_codes,
            )
        )
    return tuple(ranked_symbols)


def _extract_current_regime(row: dict[str, Any]) -> str:
    current = row.get("current_regime")
    if current is not None:
        return _normalize_token(current, "UNKNOWN")

    regimes = row.get("regimes")
    if isinstance(regimes, list) and regimes:
        return _normalize_token(regimes[-1], "UNKNOWN")

    current_snapshot = row.get("current")
    if isinstance(current_snapshot, dict):
        regime = current_snapshot.get("market_regime") or current_snapshot.get("current_regime")
        if regime is not None:
            return _normalize_token(regime, "UNKNOWN")

    windows = row.get("windows")
    if isinstance(windows, list) and windows:
        last_window = windows[-1]
        if isinstance(last_window, dict):
            regime = last_window.get("market_regime") or last_window.get("current_regime")
            if regime is not None:
                return _normalize_token(regime, "UNKNOWN")
    return "UNKNOWN"


def _extract_regimes(row: dict[str, Any], *, current_regime: str) -> tuple[str, ...]:
    regimes = row.get("regimes")
    if isinstance(regimes, list):
        normalized = tuple(_normalize_token(regime, "UNKNOWN") for regime in regimes)
        return normalized or (current_regime,)

    windows = row.get("windows")
    if isinstance(windows, list):
        extracted: list[str] = []
        for window in windows:
            if isinstance(window, dict):
                regime = window.get("market_regime") or window.get("current_regime")
                if regime is not None:
                    extracted.append(_normalize_token(regime, "UNKNOWN"))
        if extracted:
            return tuple(extracted)

    return (current_regime,)


def _build_observe_reason(*, symbol: str, context_label: str) -> str:
    prefix = {
        "STABLE_FLAT": "stable flat context from BOOK-L1 timeline",
        "CLEAN_TREND": "clean trend context from BOOK-L1 timeline",
        "TRANSITIONING": "transitioning context detected from BOOK-L1 timeline",
        "UNSTABLE": "unstable context detected from BOOK-L1 timeline",
        "UNKNOWN": "unknown context from BOOK-L1 timeline",
        "INSUFFICIENT_DATA": "insufficient data in BOOK-L1 timeline",
        "ERROR": "BOOK-L1 timeline row was not OK",
    }.get(context_label, "unknown context from BOOK-L1 timeline")
    return f"{prefix}; observe only; no trading signal; not approved for runtime trading."


def _failed_result(
    *,
    source_report_type: str,
    source_contract_version: str,
    warnings: tuple[str, ...] = (),
    errors: tuple[str, ...],
) -> L2TimelineInterpretationResult:
    market_context = L1TimelineMarketContext(
        overall_context="NO_VALID_SYMBOLS",
        symbol_count=0,
        ok_count=0,
        skipped_count=0,
        stable_count=0,
        changing_count=0,
        unstable_count=0,
        up_count=0,
        down_count=0,
        flat_count=0,
        unknown_count=0,
        overall_state=MarketContextState.ERROR.value,
        bucket_counts={},
        skip_candidate_count=0,
        notes=("no valid BOOK-L1 timeline rows were available.",),
    )
    return L2TimelineInterpretationResult(
        status="FAIL",
        source_report_type=source_report_type,
        source_contract_version=source_contract_version,
        symbols=(),
        market_context=market_context,
        safety=build_l2_safety_state(),
        warnings=warnings,
        errors=errors,
    )


def _format_symbol_table(symbols: tuple[L1TimelineSymbolContext, ...]) -> str:
    headers = (
        "Symbol",
        "Status",
        "Current Regime",
        "Stability",
        "Last Change",
        "Bucket",
        "Skip",
        "Quality",
        "Score",
        "Rank",
        "Safety",
    )
    rows = tuple(
        (
            symbol.symbol,
            symbol.status,
            symbol.current_regime,
            symbol.stability,
            symbol.last_transition,
            symbol.bucket,
            _format_yes_no(symbol.skip_candidate),
            symbol.context_quality_grade,
            f"{symbol.context_quality_score:.2f}",
            _format_rank(symbol.context_rank),
            "LOCKED",
        )
        for symbol in symbols
    )
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    lines = [border, _format_table_row(headers, widths), border]
    lines.extend(_format_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _format_bucket_summary(context: L1TimelineMarketContext) -> list[str]:
    lines = [f"{bucket}: {count}" for bucket, count in sorted(context.bucket_counts.items())]
    lines.append(f"SKIP_CANDIDATES: {context.skip_candidate_count}")
    return lines


def _format_quality_summary(context: L1TimelineMarketContext) -> list[str]:
    return [f"{grade.value}: {context.quality_summary.get(grade.value, 0)}" for grade in ContextQualityGrade]


def _format_top_ranked_symbols(symbols: tuple[L1TimelineSymbolContext, ...]) -> list[str]:
    ranked_symbols = sorted((symbol for symbol in symbols if symbol.context_rank is not None), key=lambda item: item.context_rank or 0)
    if not ranked_symbols:
        return ["none"]
    return [
        f"{symbol.context_rank}. {symbol.symbol} - {symbol.context_quality_grade} - {symbol.context_quality_score:.2f}"
        for symbol in ranked_symbols
    ]


def _format_table_row(values: tuple[str, ...], widths: list[int]) -> str:
    return "|" + "|".join(f" {value:<{widths[index]}} " for index, value in enumerate(values)) + "|"


def _symbol_to_dict(symbol: L1TimelineSymbolContext) -> dict[str, object]:
    return {
        "symbol": symbol.symbol,
        "status": symbol.status,
        "current_regime": symbol.current_regime,
        "stability": symbol.stability,
        "last_transition": symbol.last_transition,
        "confidence": symbol.current_confidence,
        "current_confidence": symbol.current_confidence,
        "current_trend_strength": symbol.current_trend_strength,
        "bucket": symbol.bucket,
        "skip_candidate": symbol.skip_candidate,
        "context_quality_score": symbol.context_quality_score,
        "context_quality_grade": symbol.context_quality_grade,
        "context_rank": symbol.context_rank,
        "context_quality_reason_codes": list(symbol.context_quality_reason_codes),
        "context_reason_codes": list(symbol.context_reason_codes),
        "trade_signal": symbol.trade_signal,
        "safe_for_runtime_trading": symbol.safe_for_runtime_trading,
        "context_label": symbol.context_label,
        "observe_reason": symbol.observe_reason,
        "warnings": list(symbol.warnings),
    }


def _market_context_to_dict(context: L1TimelineMarketContext) -> dict[str, object]:
    payload = asdict(context)
    payload["notes"] = list(context.notes)
    payload["clean_symbols"] = list(context.clean_symbols)
    payload["flat_symbols"] = list(context.flat_symbols)
    payload["unstable_symbols"] = list(context.unstable_symbols)
    payload["unknown_symbols"] = list(context.unknown_symbols)
    payload["quality_summary"] = dict(context.quality_summary)
    payload["top_ranked_symbols"] = list(context.top_ranked_symbols)
    return payload


def _summary_to_dict(context: L1TimelineMarketContext) -> dict[str, object]:
    return {
        "bucket_summary": dict(context.bucket_counts),
        "quality_summary": dict(context.quality_summary),
        "top_ranked_symbols": list(context.top_ranked_symbols),
    }


def _quality_score_from_symbol(symbol: L1TimelineSymbolContext) -> ContextQualityScore:
    return ContextQualityScore(
        symbol=symbol.symbol,
        score=symbol.context_quality_score,
        grade=symbol.context_quality_grade,
        rank=symbol.context_rank,
        reason_codes=symbol.context_quality_reason_codes,
    )


def _symbol_to_bucket_decision(symbol: L1TimelineSymbolContext) -> SymbolBucketDecision:
    return SymbolBucketDecision(
        symbol=symbol.symbol,
        bucket=SymbolBucket(symbol.bucket),
        regime=symbol.current_regime,
        stability=symbol.stability,
        last_transition=symbol.last_transition,
        confidence=symbol.current_confidence,
        reason_codes=symbol.context_reason_codes,
        warnings=symbol.warnings,
        skip_candidate=symbol.skip_candidate,
        safe_for_runtime_trading=symbol.safe_for_runtime_trading,
        trade_signal=symbol.trade_signal,
    )


def _overall_state_to_legacy_context(state: MarketContextState, *, up_count: int, down_count: int) -> str:
    if state == MarketContextState.ERROR:
        return "ERROR"
    if state == MarketContextState.RANGING:
        return "ALL_FLAT"
    if state == MarketContextState.TRENDING:
        if up_count > down_count:
            return "BROAD_UP"
        if down_count > up_count:
            return "BROAD_DOWN"
        return "TRENDING"
    return state.value


def _build_bucket_counts(decisions: tuple[SymbolBucketDecision, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.bucket.value] = counts.get(decision.bucket.value, 0) + 1
    return counts


def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_list_of_strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _read_row_warnings(row: dict[str, Any]) -> tuple[str, ...]:
    warnings: list[str] = []
    warning = row.get("warning")
    if warning:
        warnings.append(str(warning))
    warnings_value = row.get("warnings")
    if isinstance(warnings_value, list):
        warnings.extend(str(item) for item in warnings_value)
    return tuple(warnings)


def _read_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _normalize_token(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip().upper()
    return text or default


def _normalize_symbol(value: Any) -> str:
    return _normalize_token(value, "UNKNOWN")


def _string_or_unknown(value: Any) -> str:
    if value is None:
        return "UNKNOWN"
    text = str(value).strip()
    return text or "UNKNOWN"


def _format_bool(value: bool) -> str:
    return str(value).lower()


def _format_yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _format_rank(value: int | None) -> str:
    return str(value) if value is not None else "-"


def _format_bool_or_value(value: object) -> str:
    if isinstance(value, bool):
        return _format_bool(value)
    return str(value)


def _validate_l2_result_contract(result: L2TimelineInterpretationResult) -> tuple[str, ...]:
    errors: list[str] = []
    allowed_grades = {grade.value for grade in ContextQualityGrade}
    ranks: list[int] = []
    for symbol in result.symbols:
        if not 0.0 <= symbol.context_quality_score <= 1.0:
            errors.append(f"{symbol.symbol}: context_quality_score must be between 0.0 and 1.0")
        if symbol.context_quality_grade not in allowed_grades:
            errors.append(f"{symbol.symbol}: invalid context_quality_grade")
        if symbol.status == "OK" and not symbol.context_quality_reason_codes:
            errors.append(f"{symbol.symbol}: context_quality_reason_codes must not be empty for OK rows")
        if symbol.context_rank is not None:
            ranks.append(symbol.context_rank)
        if symbol.skip_candidate and symbol.context_rank is not None:
            errors.append(f"{symbol.symbol}: skip_candidate rows must not receive context_rank")
        if symbol.status in {"ERROR", "INSUFFICIENT_DATA"} and symbol.context_rank is not None:
            errors.append(f"{symbol.symbol}: non-OK rows must not receive context_rank")
    if len(ranks) != len(set(ranks)):
        errors.append("context_rank values must be unique")
    if ranks:
        sorted_ranks = sorted(ranks)
        expected_ranks = list(range(1, len(sorted_ranks) + 1))
        if sorted_ranks != expected_ranks:
            errors.append("context_rank values must start at 1 and be contiguous")
    if not _is_l2_safety_fail_closed(result.safety):
        errors.append("BOOK-L2 safety must remain fail-closed")
    return tuple(errors)


def _is_l2_safety_fail_closed(safety: L2SafetyState) -> bool:
    return (
        safety.trade_signal == "NOT_EVALUATED"
        and safety.safe_for_runtime_trading is False
        and safety.orders_enabled is False
        and safety.live_trading_connected is False
        and safety.traders_core_connected is False
        and safety.approved_for_live_trading is False
        and safety.approved_for_auto_activation is False
    )
