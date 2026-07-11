from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


FORBIDDEN_BRIEF_TERMS = (
    "LONG",
    "SHORT",
    "BUY",
    "SELL",
    "ENTRY",
    "ENTER",
    "EXIT",
    "TAKE_PROFIT",
    "STOP_LOSS",
    "LEVERAGE",
    "POSITION_SIZE",
    "ORDER",
    "TRADE_SIGNAL",
)


@dataclass(frozen=True)
class MarketBriefConfig:
    max_observation_candidates: int = 3
    max_skip_candidates: int = 5
    min_high_quality_score: float = 0.70
    min_medium_quality_score: float = 0.45


@dataclass(frozen=True)
class SymbolBrief:
    symbol: str
    bucket: str
    context_quality_score: float
    quality_grade: str
    context_rank: int | None
    skip_candidate: bool
    main_reason: str


@dataclass(frozen=True)
class MarketBrief:
    overall_state: str
    brief_state: str
    observation_candidates: tuple[SymbolBrief, ...]
    skip_candidates: tuple[SymbolBrief, ...]
    key_points: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    safety_note: str = "Observe-only context. Not a trading signal."


class ContextSummaryBuilder:
    def __init__(self, config: MarketBriefConfig | None = None) -> None:
        self.config = config or MarketBriefConfig()

    def build(self, symbols: Iterable[object], *, overall_state: str) -> MarketBrief:
        rows = tuple(_to_symbol_brief(symbol) for symbol in symbols)
        observation_candidates = select_best_observation_candidates(rows, config=self.config)
        skip_candidates = select_skip_candidates(rows, config=self.config)
        brief_state = _classify_brief_state(
            rows,
            overall_state=overall_state,
            observation_candidates=observation_candidates,
        )
        key_points = _build_key_points(
            overall_state=overall_state,
            brief_state=brief_state,
            observation_candidates=observation_candidates,
            skip_candidates=skip_candidates,
            rows=rows,
        )
        return MarketBrief(
            overall_state=overall_state,
            brief_state=brief_state,
            observation_candidates=observation_candidates,
            skip_candidates=skip_candidates,
            key_points=key_points,
            warnings=_build_warnings(rows=rows, brief_state=brief_state),
        )


def build_market_brief(
    symbols: Iterable[object],
    *,
    overall_state: str,
    config: MarketBriefConfig | None = None,
) -> MarketBrief:
    return ContextSummaryBuilder(config).build(symbols, overall_state=overall_state)


def select_best_observation_candidates(
    symbols: Iterable[object],
    *,
    config: MarketBriefConfig | None = None,
) -> tuple[SymbolBrief, ...]:
    active_config = config or MarketBriefConfig()
    briefs = tuple(_coerce_symbol_brief(symbol) for symbol in symbols)
    candidates = tuple(
        brief
        for brief in briefs
        if not brief.skip_candidate and brief.quality_grade in {"HIGH", "MEDIUM"}
    )
    return tuple(sorted(candidates, key=_observation_sort_key)[: active_config.max_observation_candidates])


def select_skip_candidates(
    symbols: Iterable[object],
    *,
    config: MarketBriefConfig | None = None,
) -> tuple[SymbolBrief, ...]:
    active_config = config or MarketBriefConfig()
    briefs = tuple(_coerce_symbol_brief(symbol) for symbol in symbols)
    candidates = tuple(brief for brief in briefs if _is_skip_brief(brief))
    return tuple(sorted(candidates, key=_skip_sort_key)[: active_config.max_skip_candidates])


def build_market_brief_lines(brief: MarketBrief) -> tuple[str, ...]:
    lines: list[str] = [
        "Context Summary / Human Market Brief",
        "",
        f"Overall: {brief.overall_state}",
        f"Brief: {brief.brief_state}",
        "",
        "Best observation candidates:",
    ]
    if brief.observation_candidates:
        lines.extend(
            (
                f"{index}. {candidate.symbol} | {candidate.quality_grade} | "
                f"score={candidate.context_quality_score:.2f} | bucket={candidate.bucket} | "
                f"rank={_format_rank(candidate.context_rank)}"
            )
            for index, candidate in enumerate(brief.observation_candidates, start=1)
        )
    else:
        lines.append("- none")

    lines.extend(["", "Skip candidates:"])
    if brief.skip_candidates:
        lines.extend(
            (
                f"- {candidate.symbol} | {candidate.quality_grade} | "
                f"score={candidate.context_quality_score:.2f} | bucket={candidate.bucket} | "
                f"reason={candidate.main_reason}"
            )
            for candidate in brief.skip_candidates
        )
    else:
        lines.append("- none")

    lines.extend(["", "Key points:"])
    lines.extend(f"- {point}" for point in brief.key_points)

    if brief.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in brief.warnings)

    lines.extend(["", "Safety note:", brief.safety_note])
    return tuple(lines)


def market_brief_to_dict(brief: MarketBrief) -> dict[str, object]:
    return {
        "overall_state": brief.overall_state,
        "brief_state": brief.brief_state,
        "observation_candidates": [_symbol_brief_to_dict(symbol) for symbol in brief.observation_candidates],
        "skip_candidates": [_symbol_brief_to_dict(symbol) for symbol in brief.skip_candidates],
        "key_points": list(brief.key_points),
        "warnings": list(brief.warnings),
        "safety_note": brief.safety_note,
    }


def validate_market_brief_safety(brief: MarketBrief | None) -> tuple[str, ...]:
    if brief is None:
        return ("market_brief is required",)

    errors: list[str] = []
    if not brief.overall_state:
        errors.append("market_brief.overall_state is required")
    if not brief.brief_state:
        errors.append("market_brief.brief_state is required")
    if not isinstance(brief.observation_candidates, tuple):
        errors.append("market_brief.observation_candidates must be a tuple")
    if not isinstance(brief.skip_candidates, tuple):
        errors.append("market_brief.skip_candidates must be a tuple")
    if not brief.key_points:
        errors.append("market_brief.key_points is required")
    if not brief.safety_note:
        errors.append("market_brief.safety_note is required")

    for candidate in brief.observation_candidates:
        if candidate.skip_candidate:
            errors.append(f"{candidate.symbol}: observation candidate must not be skip_candidate")

    text_fields = [brief.brief_state, brief.safety_note, *brief.key_points]
    text_fields.extend(candidate.main_reason for candidate in brief.observation_candidates)
    text_fields.extend(candidate.main_reason for candidate in brief.skip_candidates)
    for text in text_fields:
        matched = _forbidden_terms_in_text(text)
        if matched:
            errors.append(f"market_brief contains forbidden term: {matched[0]}")
    return tuple(errors)


def _classify_brief_state(
    rows: tuple[SymbolBrief, ...],
    *,
    overall_state: str,
    observation_candidates: tuple[SymbolBrief, ...],
) -> str:
    if not rows or all(_is_errorish(row) for row in rows):
        return "ERROR_CONTEXT"

    upper_overall_state = overall_state.upper()
    unknown_count = sum(1 for row in rows if row.bucket in {"UNKNOWN", "INSUFFICIENT_DATA"})
    if upper_overall_state in {"UNKNOWN", "UNKNOWN_HEAVY"} or unknown_count > len(rows) / 2:
        return "UNKNOWN_CONTEXT"

    unstable_or_skip_count = sum(1 for row in rows if row.skip_candidate or row.bucket in {"UNSTABLE", "SKIP_CANDIDATE"})
    if unstable_or_skip_count > len(rows) / 2:
        return "UNSTABLE_CONTEXT"

    flat_count = sum(1 for row in rows if row.bucket == "STABLE_FLAT")
    clean_or_transitioning_count = sum(1 for row in rows if row.bucket in {"CLEAN_TREND", "CLEAN", "TRANSITIONING"})
    if flat_count > len(rows) / 2 and clean_or_transitioning_count <= len(rows) / 2:
        return "FLAT_HEAVY_CONTEXT"

    if observation_candidates:
        return "CLEAN_CONTEXT_AVAILABLE"

    return "NO_OBSERVATION_CANDIDATES"


def _build_key_points(
    *,
    overall_state: str,
    brief_state: str,
    observation_candidates: tuple[SymbolBrief, ...],
    skip_candidates: tuple[SymbolBrief, ...],
    rows: tuple[SymbolBrief, ...],
) -> tuple[str, ...]:
    points = [f"Overall context is {overall_state}."]

    if observation_candidates:
        points.append(f"Best observation candidates: {_join_symbols(observation_candidates)}.")
    else:
        points.append("No clean observation candidates found.")

    if skip_candidates:
        points.append(f"Skip candidates: {_join_symbols(skip_candidates)}.")

    if rows and len(skip_candidates) > len(rows) / 2:
        points.append("Most symbols are skip candidates.")
    elif brief_state == "FLAT_HEAVY_CONTEXT":
        points.append("Market context is flat-heavy.")
    elif brief_state == "UNSTABLE_CONTEXT":
        points.append("Market context is unstable.")
    elif brief_state == "UNKNOWN_CONTEXT":
        points.append("Market context is unknown-heavy.")

    points.append("Safety remains fail-closed: no trading signal.")
    return tuple(points[:5])


def _build_warnings(*, rows: tuple[SymbolBrief, ...], brief_state: str) -> tuple[str, ...]:
    if brief_state == "ERROR_CONTEXT":
        return ("No valid market context rows are available.",)
    if rows and all(row.skip_candidate for row in rows):
        return ("All symbols are marked as skip candidates for clean observation.",)
    return ()


def _to_symbol_brief(symbol: object) -> SymbolBrief:
    return SymbolBrief(
        symbol=_read_token(symbol, "symbol", "UNKNOWN"),
        bucket=_read_token(symbol, "bucket", "UNKNOWN"),
        context_quality_score=_read_float(_read_field(symbol, "context_quality_score", 0.0), 0.0),
        quality_grade=_read_token(
            symbol,
            "quality_grade",
            _read_field(symbol, "context_quality_grade", "ERROR"),
        ),
        context_rank=_read_optional_int(_read_field(symbol, "context_rank", None)),
        skip_candidate=_read_bool(_read_field(symbol, "skip_candidate", False)),
        main_reason=_build_main_reason(symbol),
    )


def _coerce_symbol_brief(symbol: object) -> SymbolBrief:
    if isinstance(symbol, SymbolBrief):
        return symbol
    return _to_symbol_brief(symbol)


def _build_main_reason(symbol: object) -> str:
    bucket = _read_token(symbol, "bucket", "UNKNOWN")
    grade = _read_token(symbol, "quality_grade", _read_field(symbol, "context_quality_grade", "ERROR"))
    score = _read_float(_read_field(symbol, "context_quality_score", 0.0), 0.0)
    skip_candidate = _read_bool(_read_field(symbol, "skip_candidate", False))

    if bucket in {"ERROR", "INSUFFICIENT_DATA"} or grade == "ERROR":
        return "No valid context available."
    if bucket == "UNKNOWN":
        return "Unknown current regime."
    if skip_candidate or bucket in {"UNSTABLE", "SKIP_CANDIDATE"}:
        return "Unstable context; skip candidate."
    if grade == "SKIP" or score < 0.25:
        return "Low quality score."
    if bucket == "STABLE_FLAT":
        return "Stable flat context; observe only."
    if bucket == "TRANSITIONING":
        return "Transitioning context; requires observation."
    if grade == "HIGH" and bucket in {"CLEAN_TREND", "CLEAN"}:
        return "High quality clean context."
    if grade == "MEDIUM":
        return "Medium quality readable context."
    return "Context requires observation."


def _is_skip_brief(brief: SymbolBrief) -> bool:
    return (
        brief.skip_candidate
        or brief.quality_grade == "SKIP"
        or brief.bucket in {"UNKNOWN", "UNSTABLE", "SKIP_CANDIDATE", "INSUFFICIENT_DATA", "ERROR"}
    )


def _is_errorish(brief: SymbolBrief) -> bool:
    return brief.bucket == "ERROR" or brief.quality_grade == "ERROR"


def _observation_sort_key(brief: SymbolBrief) -> tuple[bool, float, int, str]:
    rank = brief.context_rank if brief.context_rank is not None else 10**9
    return (brief.skip_candidate, -brief.context_quality_score, rank, brief.symbol)


def _skip_sort_key(brief: SymbolBrief) -> tuple[bool, float, str]:
    return (not brief.skip_candidate, brief.context_quality_score, brief.symbol)


def _symbol_brief_to_dict(brief: SymbolBrief) -> dict[str, object]:
    return {
        "symbol": brief.symbol,
        "bucket": brief.bucket,
        "context_quality_score": brief.context_quality_score,
        "quality_grade": brief.quality_grade,
        "context_rank": brief.context_rank,
        "skip_candidate": brief.skip_candidate,
        "main_reason": brief.main_reason,
    }


def _join_symbols(symbols: tuple[SymbolBrief, ...]) -> str:
    return ", ".join(symbol.symbol for symbol in symbols)


def _forbidden_terms_in_text(text: str) -> tuple[str, ...]:
    upper_text = text.upper()
    return tuple(term for term in FORBIDDEN_BRIEF_TERMS if term in upper_text)


def _read_field(row: object, field_name: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(field_name, default)
    return getattr(row, field_name, default)


def _read_token(row: object, field_name: str, default: Any) -> str:
    value = _read_field(row, field_name, default)
    if value is None:
        value = default
    text = str(value).strip().upper()
    return text or str(default).strip().upper()


def _read_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


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


def _read_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_rank(value: int | None) -> str:
    return str(value) if value is not None else "-"
