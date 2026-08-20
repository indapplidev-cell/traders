"""Research-only impulse phase and entry-quality diagnostics (ENGINE-ANALYSIS-32).

The component consumes finalized OHLCV bars and an already-produced market
decision.  It never changes that decision and never creates a setup or signal.
``cutoff`` identifies the open time of the last *closed* bar available to the
caller; rows with a later open time are ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from re import fullmatch
from typing import Any, Mapping, Sequence


STAGE = "ENGINE-ANALYSIS-32"
SCHEMA_VERSION = "1.0.0"
RESEARCH_ONLY = True
MIN_BARS = 20


class ImpulsePhase(str, Enum):
    NO_IMPULSE = "NO_IMPULSE"
    EARLY_IMPULSE = "EARLY_IMPULSE"
    IMPULSE_DETECTED = "IMPULSE_DETECTED"
    IMPULSE_EXTENSION = "IMPULSE_EXTENSION"
    IMPULSE_EXHAUSTION_RISK = "IMPULSE_EXHAUSTION_RISK"
    POST_SPIKE_PULLBACK = "POST_SPIKE_PULLBACK"
    RANGE_REENTRY = "RANGE_REENTRY"
    LATE_CONFIRMATION_RISK = "LATE_CONFIRMATION_RISK"
    CONFLICTED_IMPULSE = "CONFLICTED_IMPULSE"
    UNKNOWN_IMPULSE_PHASE = "UNKNOWN_IMPULSE_PHASE"


class EntryQuality(str, Enum):
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    POOR = "POOR"
    INVALID = "INVALID"
    NOT_EVALUATED = "NOT_EVALUATED"


class EntryReason(str, Enum):
    ENTRY_DIRECTLY_INTO_RESISTANCE = "ENTRY_DIRECTLY_INTO_RESISTANCE"
    ENTRY_DIRECTLY_INTO_SUPPORT = "ENTRY_DIRECTLY_INTO_SUPPORT"
    LATE_AFTER_LARGE_INTRADAY_MOVE = "LATE_AFTER_LARGE_INTRADAY_MOVE"
    WEAK_FRESH_VOLUME = "WEAK_FRESH_VOLUME"
    POST_SPIKE_PULLBACK_ACTIVE = "POST_SPIKE_PULLBACK_ACTIVE"
    RANGE_REENTRY_ACTIVE = "RANGE_REENTRY_ACTIVE"
    NO_CONFIRMED_BREAKOUT = "NO_CONFIRMED_BREAKOUT"
    NO_SUCCESSFUL_RETEST = "NO_SUCCESSFUL_RETEST"
    CONFLICTING_EVIDENCE_MATRIX = "CONFLICTING_EVIDENCE_MATRIX"
    CONFIRMED_HYPOTHESIS_ABSENT = "CONFIRMED_HYPOTHESIS_ABSENT"
    CONFIRMED_HYPOTHESIS_LATE = "CONFIRMED_HYPOTHESIS_LATE"
    RANGE_STRUCTURE_DOMINATES_INDICATORS = "RANGE_STRUCTURE_DOMINATES_INDICATORS"
    WEAK_DIRECTIONAL_FOLLOW_THROUGH = "WEAK_DIRECTIONAL_FOLLOW_THROUGH"
    HIGH_OVERLAP_CHOP = "HIGH_OVERLAP_CHOP"
    MID_RANGE_RETURN = "MID_RANGE_RETURN"
    BOUNDARY_REJECTION_WITHOUT_BREAKOUT = "BOUNDARY_REJECTION_WITHOUT_BREAKOUT"
    DISTRIBUTION_REJECTION_CLUSTER = "DISTRIBUTION_REJECTION_CLUSTER"
    UPPER_WICK_SUPPLY_PRESSURE = "UPPER_WICK_SUPPLY_PRESSURE"
    FAILED_HIGH_CONTINUATION = "FAILED_HIGH_CONTINUATION"
    BEARISH_VOLUME_REJECTION = "BEARISH_VOLUME_REJECTION"
    MOMENTUM_DIVERGENCE_AT_HIGH = "MOMENTUM_DIVERGENCE_AT_HIGH"
    POST_SPIKE_COUNTER_CANDLE = "POST_SPIKE_COUNTER_CANDLE"
    IMPULSE_HIGH_REJECTION = "IMPULSE_HIGH_REJECTION"
    PULLBACK_AFTER_VERTICAL_MOVE = "PULLBACK_AFTER_VERTICAL_MOVE"
    NO_CONTINUATION_AFTER_SPIKE = "NO_CONTINUATION_AFTER_SPIKE"
    MICRO_STRUCTURE_BROKEN_AFTER_SPIKE = "MICRO_STRUCTURE_BROKEN_AFTER_SPIKE"
    FAILED_BREAKOUT_RANGE_REENTRY = "FAILED_BREAKOUT_RANGE_REENTRY"
    BREAKOUT_HOLD_FAILED = "BREAKOUT_HOLD_FAILED"
    RETURNED_INSIDE_CONFIRMED_RANGE = "RETURNED_INSIDE_CONFIRMED_RANGE"
    DIRECTIONAL_BREAKOUT_INVALIDATED = "DIRECTIONAL_BREAKOUT_INVALIDATED"
    LATE_DIRECTIONAL_CONFIRMATION = "LATE_DIRECTIONAL_CONFIRMATION"
    MOVE_ALREADY_EXTENDED = "MOVE_ALREADY_EXTENDED"
    POOR_REWARD_SPACE_AFTER_CONFIRMATION = "POOR_REWARD_SPACE_AFTER_CONFIRMATION"
    CONFIRMATION_NEAR_LOCAL_EXTREME = "CONFIRMATION_NEAR_LOCAL_EXTREME"
    EXHAUSTION_SIGNS_AFTER_CONFIRMATION = "EXHAUSTION_SIGNS_AFTER_CONFIRMATION"
    CONTROLLED_PULLBACK_CONTINUATION = "CONTROLLED_PULLBACK_CONTINUATION"
    BREAKOUT_HELD_WITH_FOLLOW_THROUGH = "BREAKOUT_HELD_WITH_FOLLOW_THROUGH"
    EXTENDED_MOVE_EXHAUSTION_RISK = "EXTENDED_MOVE_EXHAUSTION_RISK"
    CLIMAX_VOLUME_WITHOUT_FOLLOW_THROUGH = "CLIMAX_VOLUME_WITHOUT_FOLLOW_THROUGH"
    WICK_REJECTION_AFTER_EXTENSION = "WICK_REJECTION_AFTER_EXTENSION"
    PHASE_CONFLICT_RESOLVED_TO_RANGE = "PHASE_CONFLICT_RESOLVED_TO_RANGE"
    PHASE_CONFLICT_RESOLVED_TO_PULLBACK = "PHASE_CONFLICT_RESOLVED_TO_PULLBACK"
    PHASE_CONFLICT_RESOLVED_TO_DISTRIBUTION = "PHASE_CONFLICT_RESOLVED_TO_DISTRIBUTION"
    PHASE_CONFLICT_RESOLVED_TO_LATE_RISK = "PHASE_CONFLICT_RESOLVED_TO_LATE_RISK"
    INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE = "INDICATOR_TREND_OVERRIDDEN_BY_STRUCTURE"


class PricePosition(str, Enum):
    UPPER_RANGE = "UPPER_RANGE"
    MID_RANGE = "MID_RANGE"
    LOWER_RANGE = "LOWER_RANGE"
    ABOVE_RANGE = "ABOVE_RANGE"
    BELOW_RANGE = "BELOW_RANGE"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"


@dataclass(frozen=True)
class ImpulseDiagnosticInput:
    symbol: str
    timeframe: str
    cutoff: str | datetime
    market_regime: str
    final_action: str
    candles: Sequence[Mapping[str, Any] | object]
    lookback_bars: int = 96
    minimum_required_bars: int = MIN_BARS
    confirmed_hypotheses: tuple[str, ...] = ()
    directional_confirmation_at: str | datetime | None = None
    breakout_status: str = "NO_BREAKOUT"
    successful_retest: bool = False
    range_lower: float | None = None
    range_upper: float | None = None
    resistance: float | None = None
    support: float | None = None
    evidence_conflicted: bool = False

    def __post_init__(self) -> None:
        if self.market_regime not in {"UP", "DOWN", "FLAT", "UNKNOWN"}:
            raise ValueError("unsupported market_regime")
        if self.final_action not in {"NO_ACTION", "NOT_EVALUATED"}:
            raise ValueError("diagnostics cannot accept or create a trading action")
        if self.minimum_required_bars < 8:
            raise ValueError("minimum_required_bars must be at least 8")
        if self.lookback_bars < self.minimum_required_bars:
            raise ValueError("lookback_bars must cover minimum_required_bars")
        if (self.range_lower is None) != (self.range_upper is None):
            raise ValueError("range_lower and range_upper must be provided together")
        if self.range_lower is not None and self.range_lower >= self.range_upper:
            raise ValueError("range_lower must be below range_upper")


@dataclass(frozen=True)
class _Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _field(row: Mapping[str, Any] | object, *names: str) -> Any:
    for name in names:
        if isinstance(row, Mapping) and name in row:
            return row[name]
        if hasattr(row, name):
            return getattr(row, name)
    raise ValueError(f"candle field is missing: {'/'.join(names)}")


def _datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed


def _timeframe_delta(value: str) -> timedelta:
    match = fullmatch(r"([1-9]\d*)([mhd])", value.strip().lower())
    if match is None:
        raise ValueError("timeframe must use Nm, Nh, or Nd form")
    return {
        "m": timedelta(minutes=int(match.group(1))),
        "h": timedelta(hours=int(match.group(1))),
        "d": timedelta(days=int(match.group(1))),
    }[match.group(2)]


def _normalise_bars(data: ImpulseDiagnosticInput) -> list[_Bar]:
    cutoff = _datetime(data.cutoff)
    bars: list[_Bar] = []
    for row in data.candles:
        timestamp = _datetime(_field(row, "timestamp", "open_time", "time"))
        if timestamp > cutoff:
            continue
        values = [float(_field(row, name)) for name in ("open", "high", "low", "close", "volume")]
        if not all(isfinite(value) for value in values):
            raise ValueError("OHLCV values must be finite")
        open_, high, low, close, volume = values
        if min(open_, high, low, close) <= 0 or volume < 0 or high < max(open_, close) or low > min(open_, close):
            raise ValueError("invalid OHLCV candle")
        bars.append(_Bar(timestamp, open_, high, low, close, volume))
    bars.sort(key=lambda bar: bar.timestamp)
    if len({bar.timestamp for bar in bars}) != len(bars):
        raise ValueError("duplicate candle timestamps")
    return bars[-data.lookback_bars :]


def _atr(bars: Sequence[_Bar], period: int = 14) -> float | None:
    if len(bars) < 2:
        return None
    true_ranges = []
    for previous, current in zip(bars, bars[1:]):
        true_ranges.append(max(current.high - current.low, abs(current.high - previous.close), abs(current.low - previous.close)))
    sample = true_ranges[-period:]
    return sum(sample) / len(sample) if sample else None


def _chronological_moves(bars: Sequence[_Bar]) -> tuple[dict[str, Any], dict[str, Any]]:
    min_price, min_index = bars[0].low, 0
    max_price, max_index = bars[0].high, 0
    up = {"pct": 0.0, "base_index": 0, "extreme_index": 0, "base": min_price, "extreme": min_price}
    down = {"pct": 0.0, "base_index": 0, "extreme_index": 0, "base": max_price, "extreme": max_price}
    for index, bar in enumerate(bars):
        candidate_up = (bar.high / min_price - 1.0) * 100.0
        if candidate_up > up["pct"]:
            up = {"pct": candidate_up, "base_index": min_index, "extreme_index": index, "base": min_price, "extreme": bar.high}
        candidate_down = (1.0 - bar.low / max_price) * 100.0
        if candidate_down > down["pct"]:
            down = {"pct": candidate_down, "base_index": max_index, "extreme_index": index, "base": max_price, "extreme": bar.low}
        if bar.low < min_price:
            min_price, min_index = bar.low, index
        if bar.high > max_price:
            max_price, max_index = bar.high, index
    return up, down


def _position(close: float, lower: float | None, upper: float | None, bars: Sequence[_Bar]) -> tuple[PricePosition, float, float]:
    if lower is None or upper is None:
        recent = bars[-min(32, len(bars)) :]
        lower, upper = min(bar.low for bar in recent), max(bar.high for bar in recent)
    if upper <= lower:
        return PricePosition.NOT_OBSERVABLE, lower, upper
    if close > upper:
        return PricePosition.ABOVE_RANGE, lower, upper
    if close < lower:
        return PricePosition.BELOW_RANGE, lower, upper
    fraction = (close - lower) / (upper - lower)
    return (PricePosition.LOWER_RANGE if fraction < 1 / 3 else PricePosition.UPPER_RANGE if fraction > 2 / 3 else PricePosition.MID_RANGE), lower, upper


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _explanation(phase: ImpulsePhase, quality: EntryQuality, regime: str, direction: str) -> str:
    direction_text = "выросла" if direction == "UP" else "снизилась"
    if phase is ImpulsePhase.RANGE_REENTRY:
        state = "после импульса вернулась в наблюдаемый диапазон"
    elif phase is ImpulsePhase.POST_SPIKE_PULLBACK:
        state = "находится после сильного импульса и встречного отката"
    elif phase is ImpulsePhase.LATE_CONFIRMATION_RISK:
        state = "получила направленное подтверждение только после значительной части движения"
    elif phase is ImpulsePhase.IMPULSE_EXHAUSTION_RISK:
        state = "находится в поздней фазе с риском исчерпания"
    elif phase in {ImpulsePhase.IMPULSE_DETECTED, ImpulsePhase.IMPULSE_EXTENSION}:
        state = "сохраняет диагностируемый импульс"
    elif phase is ImpulsePhase.NO_IMPULSE:
        return "Достаточного импульса в доступном окне не обнаружено. Качество потенциального входа не оценивалось."
    else:
        return "Данных или согласованности недостаточно для причинной оценки фазы импульса. Торговое действие не создаётся."
    hypothesis = "Подтверждённой продолжающейся гипотезы сейчас нет." if regime == "UNKNOWN" else "Факт направленного режима сам по себе не подтверждает качественную текущую точку."
    return f"Цена за доступное окно {direction_text}, но текущий срез {state}. Модель не отрицает факт движения: {hypothesis} Качество потенциального входа: {quality.value}."


def diagnose_impulse_phase(data: ImpulseDiagnosticInput) -> dict[str, Any]:
    """Return deterministic, causal, non-actionable diagnostics."""

    bars = _normalise_bars(data)
    cutoff = _datetime(data.cutoff)
    delta = _timeframe_delta(data.timeframe)
    if len(bars) < data.minimum_required_bars:
        phase = ImpulsePhase.UNKNOWN_IMPULSE_PHASE
        quality = EntryQuality.NOT_EVALUATED
        direction = "UNKNOWN"
        return {
            "stage": STAGE, "schema_version": SCHEMA_VERSION, "research_only": True,
            "symbol": data.symbol, "timeframe": data.timeframe, "cutoff": cutoff.isoformat(),
            "market_regime": data.market_regime, "final_action": data.final_action,
            "impulse_phase": phase.value, "impulse_direction": direction,
            "entry_quality": {"value": quality.value, "reason_codes": []},
            "impulse_context": {"lookback_bars": data.lookback_bars, "observed_closed_bars": len(bars), "data_sufficient": False},
            "human_explanation": _explanation(phase, quality, data.market_regime, direction),
            "safety": {"setup_created": False, "trade_signal_created": False, "decision_changed": False, "future_bars_used": False},
        }

    atr = _atr(bars)
    up, down = _chronological_moves(bars)
    move = up if up["pct"] >= down["pct"] else down
    direction = "UP" if move is up else "DOWN"
    last = bars[-1]
    atr_pct = (atr / last.close * 100.0) if atr else 0.0
    impulse_threshold = max(3.0, atr_pct * 2.5)
    has_impulse = move["pct"] >= impulse_threshold
    extreme = float(move["extreme"])
    distance_from_extreme = (last.close / extreme - 1.0) * 100.0
    if direction == "DOWN":
        distance_from_extreme = (extreme / last.close - 1.0) * 100.0
    pullback_pct = abs(distance_from_extreme)
    bars_since_extreme = len(bars) - 1 - int(move["extreme_index"])
    # A pullback is an active phase only while the extreme is still recent.
    # Older impulses remain visible in the context metrics but do not make an
    # unrelated current bar look like an active post-spike event.
    post_spike = has_impulse and 0 < bars_since_extreme <= 12 and pullback_pct >= max(2.0, atr_pct * 0.8)
    position, effective_lower, effective_upper = _position(last.close, data.range_lower, data.range_upper, bars)
    explicit_range = data.range_lower is not None and data.range_upper is not None
    crossed_range = (direction == "UP" and extreme > effective_upper) or (direction == "DOWN" and extreme < effective_lower)
    inside_range = effective_lower <= last.close <= effective_upper
    range_reentry = bool(has_impulse and explicit_range and crossed_range and inside_range and bars_since_extreme > 0)

    confirmation_index: int | None = None
    if data.directional_confirmation_at is not None:
        confirmation = _datetime(data.directional_confirmation_at)
        candidates = [index for index, bar in enumerate(bars) if bar.timestamp >= confirmation]
        confirmation_index = candidates[0] if candidates else None
    late_confirmation = False
    if confirmation_index is not None and has_impulse and confirmation_index >= int(move["base_index"]):
        confirmation_close = bars[confirmation_index].close
        base = float(move["base"])
        progressed = (confirmation_close - base) / max(abs(extreme - base), 1e-12) if direction == "UP" else (base - confirmation_close) / max(abs(base - extreme), 1e-12)
        late_confirmation = progressed >= 0.70 or move["pct"] >= max(8.0, atr_pct * 5.0)

    fresh = bars[-3:]
    reference = bars[-23:-3] or bars[:-3]
    fresh_volume_ratio = (sum(bar.volume for bar in fresh) / len(fresh)) / (sum(bar.volume for bar in reference) / len(reference)) if reference and sum(bar.volume for bar in reference) > 0 else None
    def session_date(value: datetime) -> object:
        if cutoff.tzinfo is not None and value.tzinfo is not None:
            return value.astimezone(cutoff.tzinfo).date()
        return value.date()

    session_start = next((index for index, bar in enumerate(bars) if session_date(bar.timestamp) == session_date(last.timestamp)), 0)
    session_return = (last.close / bars[session_start].open - 1.0) * 100.0
    move_from_local_low = (last.close / min(bar.low for bar in bars) - 1.0) * 100.0

    rejection = False
    recent = bars[-min(4, len(bars)) :]
    if direction == "UP":
        rejection = sum(bar.close < bar.open for bar in recent) >= 2 or last.close < last.open and (last.open - last.close) >= (atr or 0)
    else:
        rejection = sum(bar.close > bar.open for bar in recent) >= 2 or last.close > last.open and (last.close - last.open) >= (atr or 0)
    near_extreme = pullback_pct <= max(2.0, atr_pct)
    exhaustion = has_impulse and move["pct"] >= max(8.0, atr_pct * 5.0) and (near_extreme or rejection)

    if not has_impulse:
        phase = ImpulsePhase.NO_IMPULSE
    elif range_reentry:
        phase = ImpulsePhase.RANGE_REENTRY
    elif data.evidence_conflicted:
        phase = ImpulsePhase.CONFLICTED_IMPULSE
    elif post_spike:
        phase = ImpulsePhase.POST_SPIKE_PULLBACK
    elif late_confirmation:
        phase = ImpulsePhase.LATE_CONFIRMATION_RISK
    elif exhaustion:
        phase = ImpulsePhase.IMPULSE_EXHAUSTION_RISK
    elif move["pct"] >= max(6.0, atr_pct * 4.0):
        phase = ImpulsePhase.IMPULSE_EXTENSION
    else:
        phase = ImpulsePhase.IMPULSE_DETECTED

    reasons: list[str] = []
    def reason(value: EntryReason, condition: bool) -> None:
        if condition and value.value not in reasons:
            reasons.append(value.value)

    no_hypothesis = not data.confirmed_hypotheses
    breakout_confirmed = data.breakout_status in {"CONFIRMED", "RETEST_HELD"}
    large_move = has_impulse and move["pct"] >= max(8.0, atr_pct * 5.0)
    resistance_near = direction == "UP" and data.resistance is not None and 0 <= (data.resistance - last.close) / last.close * 100 <= max(1.0, atr_pct)
    support_near = direction == "DOWN" and data.support is not None and 0 <= (last.close - data.support) / last.close * 100 <= max(1.0, atr_pct)
    reason(EntryReason.ENTRY_DIRECTLY_INTO_RESISTANCE, resistance_near)
    reason(EntryReason.ENTRY_DIRECTLY_INTO_SUPPORT, support_near)
    reason(EntryReason.LATE_AFTER_LARGE_INTRADAY_MOVE, large_move)
    reason(EntryReason.WEAK_FRESH_VOLUME, fresh_volume_ratio is not None and fresh_volume_ratio < 0.65)
    reason(EntryReason.POST_SPIKE_PULLBACK_ACTIVE, post_spike)
    reason(EntryReason.RANGE_REENTRY_ACTIVE, range_reentry)
    reason(EntryReason.NO_CONFIRMED_BREAKOUT, not breakout_confirmed)
    reason(EntryReason.NO_SUCCESSFUL_RETEST, not data.successful_retest)
    reason(EntryReason.CONFLICTING_EVIDENCE_MATRIX, data.evidence_conflicted)
    reason(EntryReason.CONFIRMED_HYPOTHESIS_ABSENT, no_hypothesis)
    reason(EntryReason.CONFIRMED_HYPOTHESIS_LATE, late_confirmation)

    if phase in {ImpulsePhase.NO_IMPULSE, ImpulsePhase.UNKNOWN_IMPULSE_PHASE}:
        quality = EntryQuality.NOT_EVALUATED
        reasons = []
    elif range_reentry or (data.market_regime == "UNKNOWN" and no_hypothesis and not breakout_confirmed):
        quality = EntryQuality.INVALID
    elif post_spike or exhaustion or late_confirmation or data.evidence_conflicted or resistance_near or support_near:
        quality = EntryQuality.POOR
    elif breakout_confirmed and data.successful_retest and fresh_volume_ratio is not None and fresh_volume_ratio >= 0.8:
        quality = EntryQuality.GOOD
    else:
        quality = EntryQuality.ACCEPTABLE

    source_rows = [{"timestamp": bar.timestamp.isoformat(), "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close, "volume": bar.volume} for bar in bars]
    context = {
        "lookback_bars": data.lookback_bars,
        "observed_closed_bars": len(bars),
        "data_sufficient": True,
        "last_closed_bar_open_time": last.timestamp.isoformat(),
        "last_closed_bar_closed_at": (last.timestamp + delta).isoformat(),
        "session_return_pct": _round(session_return),
        "move_from_local_low_pct": _round(move_from_local_low),
        "impulse_move_pct": _round(float(move["pct"])),
        "distance_from_recent_high_pct": _round((last.close / max(bar.high for bar in bars) - 1.0) * 100.0),
        "fresh_volume_ratio": _round(fresh_volume_ratio),
        "atr_pct": _round(atr_pct),
        "price_position_in_range": position.value,
        "effective_range_lower": _round(effective_lower),
        "effective_range_upper": _round(effective_upper),
        "range_reentry": range_reentry,
        "post_spike_pullback": post_spike,
        "late_confirmation_risk": late_confirmation,
        "bars_since_impulse_extreme": bars_since_extreme,
    }
    return {
        "stage": STAGE,
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "symbol": data.symbol,
        "timeframe": data.timeframe,
        "cutoff": cutoff.isoformat(),
        "cutoff_semantics": "OPEN_TIME_OF_LAST_CLOSED_BAR",
        "market_regime": data.market_regime,
        "final_action": data.final_action,
        "impulse_phase": phase.value,
        "impulse_direction": direction,
        "entry_quality": {"value": quality.value, "reason_codes": reasons},
        "impulse_context": context,
        "human_explanation": _explanation(phase, quality, data.market_regime, direction),
        "causal_audit": {
            "future_bars_used": False,
            "latest_input_timestamp": last.timestamp.isoformat(),
            "input_digest": sha256(json.dumps(source_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        },
        "safety": {"setup_created": False, "trade_signal_created": False, "decision_changed": False, "future_bars_used": False},
    }


__all__ = [
    "EntryQuality", "EntryReason", "ImpulseDiagnosticInput", "ImpulsePhase",
    "PricePosition", "diagnose_impulse_phase",
]
