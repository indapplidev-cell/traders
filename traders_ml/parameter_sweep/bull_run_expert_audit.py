"""Independent causal audit of the project's verdicts on labelled bull runs.

This research-only contour deliberately does not reuse the project's final
direction or score as its expert answer.  It derives a compact, deterministic
price-action and indicator verdict directly from closed OHLCV, compares that
verdict with the persisted module payloads, and searches shared entry/exit
weights which produce a cost-adjusted analytical trade on labelled bull runs.

Future candles define labels only.  Every expert verdict is bound to a closed
decision boundary and every simulated fill is the following 1m open.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, model_validator

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .bull_run_observed_dataset import _load_candles
from .bull_run_weights import (
    BullRunEvent,
    CalibrationRequest,
    CausalObservation,
    Contract,
    EntryScoreWeights,
    ExitScoreWeights,
    ScoreThresholds,
    label_bull_runs,
    load_dataset,
)
from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .result_search import fingerprint

CONTRACT_VERSION = "bull-run-expert-audit/1"
EXPERT_RUBRIC_VERSION = "independent-ohlcv-rubric/1"
REGIMES = ("IMPULSE_BREAKOUT", "BREAKOUT_RETEST", "LOCAL_LOW_RECOVERY")

_ENTRY_VERDICT_CACHE: dict[tuple[str, int], IndependentExpertVerdict] = {}
_EXIT_VERDICT_CACHE: dict[tuple[str, int, str, float, float], IndependentExpertVerdict] = {}
_FUTURE_ROWS_CACHE: dict[tuple[str, int], tuple[Mapping[str, Any], ...]] = {}


class ExpertAuditRequest(Contract):
    version: Literal["bull-run-expert-audit/1"] = CONTRACT_VERSION
    calibration_request_path: str
    minimum_net_profit_bps: float = Field(default=8.0, ge=0)
    minimum_event_coverage: float = Field(default=0.60, gt=0, le=1)
    maximum_regime_calibrations: int = Field(default=3, ge=1, le=3)
    maximum_holding_minutes: int = Field(default=30, ge=5, le=30)
    search_trials: int = Field(default=4000, ge=100)
    seed: int = Field(default=20261102, ge=0)


class IndependentExpertVerdict(Contract):
    schema_version: Literal["independent-expert-verdict/1"] = "independent-expert-verdict/1"
    symbol: str
    boundary_ms: int
    timeframe: Literal["ENTRY", "EXIT"]
    regime: Literal["IMPULSE_BREAKOUT", "BREAKOUT_RETEST", "LOCAL_LOW_RECOVERY"]
    direction: Literal["BULLISH", "NEUTRAL", "BEARISH"]
    strength: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)
    graphical_score: float = Field(ge=0, le=100)
    technical_score: float = Field(ge=0, le=100)
    entry_components: dict[str, float] = Field(default_factory=dict)
    exit_components: dict[str, float] = Field(default_factory=dict)
    indicators: dict[str, float | None]
    reasons: tuple[str, ...]
    source_open_times_ms: tuple[int, ...]
    future_bars_used: bool = False


class ModuleCalibration(Contract):
    schema_version: Literal["module-calibration/1"] = "module-calibration/1"
    calibration_id: str
    regime: Literal["ALL", "IMPULSE_BREAKOUT", "BREAKOUT_RETEST", "LOCAL_LOW_RECOVERY"]
    entry_weights: EntryScoreWeights
    exit_weights: ExitScoreWeights
    thresholds: ScoreThresholds
    rubric_version: str = EXPERT_RUBRIC_VERSION
    minimum_net_profit_bps: float = Field(ge=0)
    profit_lock_buffer_bps: float = Field(default=5.0, ge=0, le=20)
    research_only: bool = True


class BullRunTradeEvaluation(Contract):
    schema_version: Literal["bull-run-trade-evaluation/1"] = "bull-run-trade-evaluation/1"
    event_id: str
    symbol: str
    regime: str
    calibration_id: str | None = None
    event_entry_open_time_ms: int
    event_peak_open_time_ms: int
    signal_boundary_ms: int | None = None
    entry_fill_ms: int | None = None
    exit_signal_ms: int | None = None
    exit_fill_ms: int | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    gross_pnl_bps: float | None = None
    fees_bps: float | None = None
    impact_bps: float | None = None
    net_pnl_bps: float | None = None
    successful: bool
    captured_excursion_ratio: float
    actual_project_verdict: dict[str, Any]
    independent_entry_verdict: IndependentExpertVerdict | None
    independent_exit_verdict: IndependentExpertVerdict | None
    discrepancy_codes: tuple[str, ...]
    failure_reason: str | None

    @model_validator(mode="after")
    def exact_cost_ledger(self) -> BullRunTradeEvaluation:
        values = (self.gross_pnl_bps, self.fees_bps, self.impact_bps, self.net_pnl_bps)
        if all(value is not None for value in values):
            expected = float(self.gross_pnl_bps) - float(self.fees_bps) - float(self.impact_bps)
            if abs(expected - float(self.net_pnl_bps)) > 1e-8:
                raise ValueError("gross - fees - impact must equal net PnL")
        return self


@dataclass(frozen=True, slots=True)
class _Indicators:
    ema9: float
    ema21: float
    sma20: float
    sma50: float
    macd: float
    macd_signal: float
    rsi14: float
    atr14: float
    adx14: float
    bollinger_mid: float
    bollinger_upper: float
    bollinger_lower: float
    vwap20: float
    volume_ratio: float

    def to_dict(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in self.__dataclass_fields__}


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, float(value)))


def _ema(values: Sequence[float], period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _rsi(values: Sequence[float], period: int = 14) -> float:
    changes = [right - left for left, right in itertools.pairwise(values)][-period:]
    if not changes:
        return 50.0
    gain = sum(max(0.0, value) for value in changes) / len(changes)
    loss = sum(max(0.0, -value) for value in changes) / len(changes)
    if loss == 0:
        return 100.0 if gain > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + gain / loss)


def _atr(rows: Sequence[Mapping[str, Any]], period: int = 14) -> float:
    selected = rows[-(period + 1):]
    ranges: list[float] = []
    previous: float | None = None
    for row in selected:
        high, low, close = (float(row[name]) for name in ("high", "low", "close"))
        ranges.append(high - low if previous is None else max(high - low, abs(high - previous), abs(low - previous)))
        previous = close
    return sum(ranges[-period:]) / max(1, min(period, len(ranges)))


def _adx(rows: Sequence[Mapping[str, Any]], period: int = 14) -> float:
    selected = rows[-(period + 1):]
    plus = minus = true_range = 0.0
    for left, right in itertools.pairwise(selected):
        up = float(right["high"]) - float(left["high"])
        down = float(left["low"]) - float(right["low"])
        plus += up if up > down and up > 0 else 0.0
        minus += down if down > up and down > 0 else 0.0
        true_range += max(
            float(right["high"]) - float(right["low"]),
            abs(float(right["high"]) - float(left["close"])),
            abs(float(right["low"]) - float(left["close"])),
        )
    if true_range <= 0:
        return 0.0
    plus_di, minus_di = 100.0 * plus / true_range, 100.0 * minus / true_range
    return 100.0 * abs(plus_di - minus_di) / max(1e-12, plus_di + minus_di)


def _indicators(rows: Sequence[Mapping[str, Any]]) -> _Indicators:
    if len(rows) < 20:
        raise ValueError("EXPERT_MINIMUM_20_CLOSED_CANDLES")
    closes = [float(row["close"]) for row in rows]
    volumes = [float(row.get("volume") or 0.0) for row in rows]
    ema12, ema26 = _ema(closes, 12), _ema(closes, 26)
    macd_series: list[float] = []
    for index in range(max(2, len(closes) - 20), len(closes) + 1):
        prefix = closes[:index]
        macd_series.append(_ema(prefix, 12) - _ema(prefix, 26))
    sample = closes[-20:]
    middle = sum(sample) / len(sample)
    deviation = statistics.pstdev(sample)
    recent = rows[-20:]
    volume_total = sum(float(row.get("volume") or 0.0) for row in recent)
    vwap = (
        sum(float(row["close"]) * float(row.get("volume") or 0.0) for row in recent) / volume_total
        if volume_total > 0 else middle
    )
    baseline_volume = sum(volumes[-20:-5]) / max(1, len(volumes[-20:-5]))
    recent_volume = sum(volumes[-5:]) / max(1, len(volumes[-5:]))
    return _Indicators(
        ema9=_ema(closes, 9), ema21=_ema(closes, 21),
        sma20=middle, sma50=sum(closes[-50:]) / min(50, len(closes)),
        macd=ema12 - ema26, macd_signal=_ema(macd_series, 9),
        rsi14=_rsi(closes), atr14=_atr(rows), adx14=_adx(rows),
        bollinger_mid=middle, bollinger_upper=middle + 2 * deviation,
        bollinger_lower=middle - 2 * deviation, vwap20=vwap,
        volume_ratio=recent_volume / baseline_volume if baseline_volume > 0 else 1.0,
    )


def _classify_regime(rows: Sequence[Mapping[str, Any]], indicators: _Indicators) -> str:
    current = rows[-1]
    prior = rows[-11:-1]
    close, low = float(current["close"]), float(current["low"])
    resistance = max(float(row["high"]) for row in prior)
    tolerance = max(indicators.atr14 * 0.25, close * 0.0005)
    if close > resistance and indicators.volume_ratio >= 1.05:
        return "IMPULSE_BREAKOUT"
    crossed = any(float(row["close"]) > max(float(item["high"]) for item in rows[max(0, index - 10):index])
                  for index, row in enumerate(rows[-6:], start=len(rows) - 6) if index >= 10)
    if crossed and low <= resistance + tolerance and close >= resistance - tolerance:
        return "BREAKOUT_RETEST"
    return "LOCAL_LOW_RECOVERY"


def independent_entry_verdict(symbol: str, boundary_ms: int,
                              rows_1m: Sequence[Mapping[str, Any]],
                              rows_5m: Sequence[Mapping[str, Any]]) -> IndependentExpertVerdict:
    one = [row for row in rows_1m if int(row["close_time_ms"]) + 1 <= boundary_ms][-60:]
    five = [row for row in rows_5m if int(row["close_time_ms"]) + 1 <= boundary_ms][-60:]
    i1, i5 = _indicators(one), _indicators(five)
    current, previous = five[-1], five[-2]
    close = float(current["close"])
    recent = five[-7:-1]
    higher_high = float(current["high"]) >= max(float(row["high"]) for row in recent)
    higher_low = float(current["low"]) >= min(float(row["low"]) for row in recent[-3:])
    structure = 50.0 + 25.0 * higher_high + 25.0 * higher_low
    resistance = max(float(row["high"]) for row in five[-11:-1])
    breakout = close > resistance
    near_retest = abs(close - resistance) <= max(i5.atr14 * 0.35, close * 0.001)
    breakout_score = 100.0 if breakout else (75.0 if near_retest and close > float(previous["close"]) else 35.0)
    candle_range = max(1e-12, float(current["high"]) - float(current["low"]))
    body = (float(current["close"]) - float(current["open"])) / candle_range
    candle_score = _clip(50.0 + 50.0 * body)
    alignment = 100.0 if i1.ema9 > i1.ema21 and i5.ema9 > i5.ema21 else (
        65.0 if i1.ema9 > i1.ema21 or i5.ema9 > i5.ema21 else 20.0
    )
    invalidation = 100.0 if close > i5.vwap20 and close > i5.bollinger_lower else 35.0
    graphical = 0.35 * structure + 0.25 * breakout_score + 0.15 * candle_score + 0.15 * alignment + 0.10 * invalidation
    trend = 100.0 if i1.ema9 > i1.ema21 and i5.ema9 > i5.ema21 else alignment
    macd = 100.0 if i1.macd > i1.macd_signal and i5.macd >= i5.macd_signal else 40.0
    rsi = 100.0 if 52 <= i1.rsi14 <= 75 else (65.0 if 45 <= i1.rsi14 < 80 else 20.0)
    adx = _clip(i5.adx14 * 2.0)
    vwap = 100.0 if close >= i5.vwap20 else 25.0
    volume = _clip(50.0 + (i1.volume_ratio - 1.0) * 100.0)
    volatility = 100.0 if i5.bollinger_lower < close < i5.bollinger_upper * 1.01 else 45.0
    technical = 0.25 * trend + 0.15 * macd + 0.10 * rsi + 0.15 * adx + 0.15 * vwap + 0.10 * volume + 0.10 * volatility
    regime = _classify_regime(five, i5)
    components = {
        "structure": _clip(graphical),
        "context": _clip((alignment + trend) / 2),
        "momentum": _clip((macd + rsi + adx) / 3),
        "volume": volume,
        "entry_quality": _clip((breakout_score + candle_score + invalidation) / 3),
        "liquidity": 100.0,
        "confirmation": _clip((candle_score + alignment + macd) / 3),
    }
    strength = (graphical + technical) / 2
    direction = "BULLISH" if strength >= 60 else ("BEARISH" if strength < 35 else "NEUTRAL")
    reasons = tuple(name for name, passed in (
        ("HIGHER_HIGH", higher_high), ("HIGHER_LOW", higher_low),
        ("BREAKOUT", breakout), ("EMA_ALIGNMENT", alignment == 100),
        ("MACD_CONFIRMATION", macd == 100), ("ABOVE_VWAP", vwap == 100),
        ("VOLUME_EXPANSION", i1.volume_ratio >= 1.05),
    ) if passed) or ("NO_STRONG_BULLISH_CONFLUENCE",)
    return IndependentExpertVerdict(
        symbol=symbol, boundary_ms=boundary_ms, timeframe="ENTRY", regime=regime,
        direction=direction, strength=_clip(strength), confidence=_clip(abs(strength - 50) * 2),
        graphical_score=_clip(graphical), technical_score=_clip(technical),
        entry_components=components, indicators={"1m_" + k: v for k, v in i1.to_dict().items()} |
        {"5m_" + k: v for k, v in i5.to_dict().items()}, reasons=reasons,
        source_open_times_ms=tuple(int(row["open_time_ms"]) for row in one + five),
    )


def independent_exit_verdict(symbol: str, boundary_ms: int, regime: str,
                             rows_1m: Sequence[Mapping[str, Any]],
                             rows_5m: Sequence[Mapping[str, Any]],
                             entry_price: float, peak_close: float) -> IndependentExpertVerdict:
    one = [row for row in rows_1m if int(row["close_time_ms"]) + 1 <= boundary_ms][-60:]
    five = [row for row in rows_5m if int(row["close_time_ms"]) + 1 <= boundary_ms][-60:]
    i1, i5 = _indicators(one), _indicators(five)
    current, previous = one[-1], one[-2]
    close = float(current["close"])
    bearish_body = close < float(current["open"])
    lower_close = close < float(previous["close"])
    lost_fast_ema = close < i1.ema9
    below_vwap = close < i1.vwap20
    lower_high = float(current["high"]) < max(float(row["high"]) for row in one[-5:-1])
    graphical = _clip(15 + 25 * lower_high + 25 * bearish_body + 20 * lower_close + 15 * lost_fast_ema)
    macd_weak = i1.macd <= i1.macd_signal
    rsi_rollover = i1.rsi14 < 55 or i1.rsi14 > 78
    technical = _clip(10 + 30 * macd_weak + 20 * rsi_rollover + 25 * lost_fast_ema + 15 * below_vwap)
    volume_decay = i1.volume_ratio < 0.90
    distance_from_peak = max(0.0, (peak_close - close) / max(1e-12, peak_close) * 10_000.0)
    momentum = _clip(10 + 35 * volume_decay + 25 * lower_close + min(30.0, distance_from_peak * 2.0))
    gross = (close / entry_price - 1.0) * 10_000.0
    economics = 100.0 if gross > 8.0 else _clip(gross * 4.0)
    strength = 0.35 * graphical + 0.35 * technical + 0.20 * momentum + 0.10 * economics
    direction = "BEARISH" if strength >= 65 else ("NEUTRAL" if strength >= 40 else "BULLISH")
    reasons = tuple(name for name, passed in (
        ("LOWER_HIGH", lower_high), ("BEARISH_BODY", bearish_body),
        ("LOWER_CLOSE", lower_close), ("LOST_EMA9", lost_fast_ema),
        ("MACD_WEAKENING", macd_weak), ("RSI_EXHAUSTION", rsi_rollover),
        ("BELOW_VWAP", below_vwap), ("VOLUME_DECAY", volume_decay),
    ) if passed) or ("CONTINUATION_INTACT",)
    return IndependentExpertVerdict(
        symbol=symbol, boundary_ms=boundary_ms, timeframe="EXIT", regime=regime,
        direction=direction, strength=_clip(strength), confidence=_clip(abs(strength - 50) * 2),
        graphical_score=graphical, technical_score=technical,
        exit_components={
            "graphical_structure": graphical,
            "technical_indicators": technical,
            "momentum_volume": momentum,
            "holding_economics": economics,
        }, indicators={"1m_" + k: v for k, v in i1.to_dict().items()} |
        {"5m_" + k: v for k, v in i5.to_dict().items()}, reasons=reasons,
        source_open_times_ms=tuple(int(row["open_time_ms"]) for row in one + five),
    )


def _weighted(values: Mapping[str, float], weights: Any) -> float:
    return sum(float(getattr(weights, name)) * float(value) / 100.0 for name, value in values.items())


def _actual_verdict(observation: CausalObservation) -> dict[str, Any]:
    snapshot = observation.module_snapshot
    analysis = dict(snapshot.get("analysis") or {})
    strategy = dict(snapshot.get("strategy") or {})
    first_exit_modules = (
        observation.exit_path[0].module_verdicts if observation.exit_path else {}
    )
    return {
        "analysis_direction": analysis.get("direction"),
        "analysis_trend": analysis.get("trend"),
        "analysis_confidence": analysis.get("confidence"),
        "market_regime": analysis.get("market_regime"),
        "strategy_direction": strategy.get("direction_hint"),
        "strategy_score": strategy.get("strategy_score"),
        "strategy_failed_gate": strategy.get("strategy_failed_gate"),
        "strategy_failed_gate_reason": strategy.get("strategy_failed_gate_reason"),
        "module_reasons": snapshot.get("module_reasons"),
        "first_closed_1m_module_verdicts": first_exit_modules,
    }


def _discrepancies(actual: Mapping[str, Any], expert: IndependentExpertVerdict,
                   entry_delay_ms: int, successful: bool) -> tuple[str, ...]:
    codes: list[str] = []
    actual_direction = str(actual.get("analysis_direction") or actual.get("strategy_direction") or "UNKNOWN").upper()
    if expert.direction == "BULLISH" and "BULL" not in actual_direction:
        codes.append("WRONG_OR_MISSING_DIRECTION")
    if expert.strength >= 65 and float(actual.get("analysis_confidence") or 0) * 100 < 50:
        codes.append("UNDERSTATED_STRENGTH")
    if actual.get("strategy_failed_gate"):
        codes.append("FALSE_BLOCK_OR_DOWNSTREAM_GATE")
    if entry_delay_ms > 300_000:
        codes.append("LATE_ENTRY")
    if not successful:
        codes.append("NO_PROFITABLE_CAUSAL_EXIT")
    return tuple(codes)


def _next_open(rows: Sequence[Mapping[str, Any]], boundary_ms: int) -> Mapping[str, Any] | None:
    return next((row for row in rows if int(row["open_time_ms"]) >= boundary_ms), None)


def _evaluate_event(event: BullRunEvent, observations: Sequence[CausalObservation],
                    rows_1m: Sequence[Mapping[str, Any]], rows_5m: Sequence[Mapping[str, Any]],
                    calibration: ModuleCalibration) -> BullRunTradeEvaluation:
    eligible = sorted((item for item in observations if item.symbol == event.symbol and
                       event.entry_open_time_ms <= item.boundary_ms <= event.peak_open_time_ms + 300_000),
                      key=lambda item: item.boundary_ms)
    selected: tuple[CausalObservation, IndependentExpertVerdict] | None = None
    for observation in eligible:
        try:
            cache_key = (event.symbol, observation.boundary_ms)
            verdict = _ENTRY_VERDICT_CACHE.get(cache_key)
            if verdict is None:
                verdict = independent_entry_verdict(
                    event.symbol, observation.boundary_ms, rows_1m, rows_5m
                )
                _ENTRY_VERDICT_CACHE[cache_key] = verdict
            causal_liquidity_cost = (
                observation.entry_slippage_bps + observation.exit_slippage_bps
                + observation.spread_bps + observation.adverse_fill_reserve_bps
            )
            components = dict(verdict.entry_components)
            components["liquidity"] = _clip(100.0 - causal_liquidity_cost * 4.0)
            verdict = verdict.model_copy(update={"entry_components": components})
        except ValueError:
            continue
        if calibration.regime not in {"ALL", verdict.regime}:
            continue
        if verdict.direction != "BEARISH" and _weighted(verdict.entry_components, calibration.entry_weights) >= calibration.thresholds.entry:
            selected = observation, verdict
            break
    if selected is None:
        actual = _actual_verdict(eligible[0]) if eligible else {}
        return BullRunTradeEvaluation(
            event_id=event.event_id, symbol=event.symbol, regime="UNKNOWN",
            calibration_id=None, event_entry_open_time_ms=event.entry_open_time_ms,
            event_peak_open_time_ms=event.peak_open_time_ms, successful=False,
            captured_excursion_ratio=0, actual_project_verdict=actual,
            independent_entry_verdict=None, independent_exit_verdict=None,
            discrepancy_codes=("NO_EXPERT_ENTRY",), failure_reason="NO_CAUSAL_ENTRY_ABOVE_THRESHOLD",
        )
    observation, entry_verdict = selected
    fill = _next_open(rows_1m, observation.boundary_ms)
    if fill is None:
        return BullRunTradeEvaluation(
            event_id=event.event_id, symbol=event.symbol, regime=entry_verdict.regime,
            calibration_id=calibration.calibration_id,
            event_entry_open_time_ms=event.entry_open_time_ms,
            event_peak_open_time_ms=event.peak_open_time_ms, signal_boundary_ms=observation.boundary_ms,
            successful=False, captured_excursion_ratio=0,
            actual_project_verdict=_actual_verdict(observation), independent_entry_verdict=entry_verdict,
            independent_exit_verdict=None, discrepancy_codes=("ENTRY_FILL_UNAVAILABLE",),
            failure_reason="ENTRY_FILL_UNAVAILABLE",
        )
    raw_entry = float(fill["open"])
    entry_impact = observation.entry_slippage_bps + observation.spread_bps / 2 + observation.adverse_fill_reserve_bps / 2
    effective_entry = raw_entry * (1 + entry_impact / 10_000)
    tail_end = observation.boundary_ms + 30 * 60_000
    future_key = (observation.observation_id, tail_end)
    future = _FUTURE_ROWS_CACHE.get(future_key)
    if future is None:
        future = tuple(row for row in rows_1m if int(row["open_time_ms"]) >= observation.boundary_ms
                       and int(row["open_time_ms"]) < tail_end)
        _FUTURE_ROWS_CACHE[future_key] = future
    chosen_exit: tuple[Mapping[str, Any], IndependentExpertVerdict] | None = None
    peak_seen = raw_entry
    for index, row in enumerate(future[:-1]):
        peak_seen = max(peak_seen, float(row["close"]))
        boundary = int(row["close_time_ms"]) + 1
        exit_key = (event.symbol, boundary, entry_verdict.regime,
                    round(effective_entry, 12), round(peak_seen, 12))
        verdict = _EXIT_VERDICT_CACHE.get(exit_key)
        if verdict is None:
            verdict = independent_exit_verdict(event.symbol, boundary, entry_verdict.regime,
                                               rows_1m, rows_5m, effective_entry, peak_seen)
            _EXIT_VERDICT_CACHE[exit_key] = verdict
        current_gross = (float(row["close"]) / effective_entry - 1) * 10_000
        estimated_net = current_gross - observation.entry_fee_bps - observation.exit_fee_bps - (
            observation.exit_slippage_bps + observation.spread_bps / 2 + observation.adverse_fill_reserve_bps / 2
        )
        exit_components = dict(verdict.exit_components)
        exit_components["holding_economics"] = (
            100.0 if estimated_net >= calibration.minimum_net_profit_bps + calibration.profit_lock_buffer_bps
            else 0.0
        )
        score = _weighted(exit_components, calibration.exit_weights)
        reversal = score >= calibration.thresholds.exit
        protected = (
            estimated_net >= calibration.minimum_net_profit_bps + calibration.profit_lock_buffer_bps
            and score >= calibration.thresholds.at_risk
        )
        strong = verdict.direction == "BEARISH" and score >= calibration.thresholds.strong_reversal
        if reversal or protected or strong:
            chosen_exit = future[index + 1], verdict
            break
    if chosen_exit is None and future:
        final = future[-1]
        final_boundary = int(final["close_time_ms"]) + 1
        exit_key = (event.symbol, final_boundary, entry_verdict.regime,
                    round(effective_entry, 12), round(peak_seen, 12))
        verdict = _EXIT_VERDICT_CACHE.get(exit_key)
        if verdict is None:
            verdict = independent_exit_verdict(event.symbol, final_boundary,
                                               entry_verdict.regime, rows_1m, rows_5m,
                                               effective_entry, peak_seen)
            _EXIT_VERDICT_CACHE[exit_key] = verdict
        chosen_exit = final, verdict
    if chosen_exit is None:
        return BullRunTradeEvaluation(
            event_id=event.event_id, symbol=event.symbol, regime=entry_verdict.regime,
            calibration_id=calibration.calibration_id,
            event_entry_open_time_ms=event.entry_open_time_ms,
            event_peak_open_time_ms=event.peak_open_time_ms,
            signal_boundary_ms=observation.boundary_ms, entry_fill_ms=int(fill["open_time_ms"]),
            entry_price=effective_entry, successful=False, captured_excursion_ratio=0,
            actual_project_verdict=_actual_verdict(observation), independent_entry_verdict=entry_verdict,
            independent_exit_verdict=None, discrepancy_codes=("EXIT_FILL_UNAVAILABLE",),
            failure_reason="EXIT_FILL_UNAVAILABLE",
        )
    exit_row, exit_verdict = chosen_exit
    raw_exit = float(exit_row["open"])
    exit_impact = observation.exit_slippage_bps + observation.spread_bps / 2 + observation.adverse_fill_reserve_bps / 2
    effective_exit = raw_exit * (1 - exit_impact / 10_000)
    gross = (raw_exit / raw_entry - 1) * 10_000
    fees = observation.entry_fee_bps + observation.exit_fee_bps
    impacts = entry_impact + exit_impact
    net = gross - fees - impacts
    success = net >= calibration.minimum_net_profit_bps
    capture = max(0.0, min(1.0, net / max(1e-12, event.net_excursion_bps)))
    actual = _actual_verdict(observation)
    discrepancies = _discrepancies(actual, entry_verdict,
                                   observation.boundary_ms - event.entry_open_time_ms, success)
    return BullRunTradeEvaluation(
        event_id=event.event_id, symbol=event.symbol, regime=entry_verdict.regime,
        calibration_id=calibration.calibration_id,
        event_entry_open_time_ms=event.entry_open_time_ms,
        event_peak_open_time_ms=event.peak_open_time_ms,
        signal_boundary_ms=observation.boundary_ms, entry_fill_ms=int(fill["open_time_ms"]),
        exit_signal_ms=exit_verdict.boundary_ms, exit_fill_ms=int(exit_row["open_time_ms"]),
        entry_price=effective_entry, exit_price=effective_exit, gross_pnl_bps=gross,
        fees_bps=fees, impact_bps=impacts, net_pnl_bps=net, successful=success,
        captured_excursion_ratio=capture, actual_project_verdict=actual,
        independent_entry_verdict=entry_verdict, independent_exit_verdict=exit_verdict,
        discrepancy_codes=discrepancies,
        failure_reason=None if success else "NET_PROFIT_BELOW_8_BPS",
    )


def _sample_weights(rng: random.Random, names: Sequence[str]) -> dict[str, float]:
    raw = [rng.randint(1, 45) for _ in names]
    scaled = [round(value / sum(raw) * 100) for value in raw]
    scaled[scaled.index(max(scaled))] += 100 - sum(scaled)
    while max(scaled) > 45 or min(scaled) < 0:
        scaled = [round((value + 100 / len(scaled)) / 2) for value in scaled]
        scaled[scaled.index(max(scaled))] += 100 - sum(scaled)
    return dict(zip(names, scaled))


def _candidate_calibrations(request: ExpertAuditRequest, regime: str) -> Iterable[ModuleCalibration]:
    rng = random.Random(request.seed + sum(ord(char) for char in regime))
    baseline = ModuleCalibration(
        calibration_id=f"{regime.lower()}:baseline", regime=regime,
        entry_weights=EntryScoreWeights(), exit_weights=ExitScoreWeights(),
        thresholds=ScoreThresholds(entry=60, at_risk=45, exit=65, strong_reversal=80),
        minimum_net_profit_bps=request.minimum_net_profit_bps,
        profit_lock_buffer_bps=5.0,
    )
    yield baseline
    entry_names = tuple(EntryScoreWeights.model_fields)
    exit_names = tuple(ExitScoreWeights.model_fields)
    for index in range(request.search_trials - 1):
        entry = EntryScoreWeights(**_sample_weights(rng, entry_names))
        exit_weights = ExitScoreWeights(**_sample_weights(rng, exit_names))
        exit_threshold = rng.choice((50.0, 55.0, 60.0, 65.0, 70.0, 75.0))
        at_risk = rng.choice(tuple(value for value in (35.0, 40.0, 45.0, 50.0, 55.0) if value < exit_threshold))
        strong = rng.choice(tuple(value for value in (70.0, 75.0, 80.0, 85.0, 90.0) if value >= exit_threshold))
        thresholds = ScoreThresholds(entry=rng.choice((45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0)),
                                     at_risk=at_risk, exit=exit_threshold,
                                     strong_reversal=strong)
        buffer = rng.choice((3.0, 5.0, 8.0, 10.0, 12.0))
        identity = fingerprint({"regime": regime, "entry": entry.model_dump(),
                                "exit": exit_weights.model_dump(), "thresholds": thresholds.model_dump(),
                                "profit_lock_buffer_bps": buffer})
        yield ModuleCalibration(
            calibration_id=identity, regime=regime, entry_weights=entry,
            exit_weights=exit_weights, thresholds=thresholds,
            minimum_net_profit_bps=request.minimum_net_profit_bps,
            profit_lock_buffer_bps=buffer,
        )


def _rank(evaluations: Sequence[BullRunTradeEvaluation]) -> tuple[float, float, float, float]:
    successful = [item for item in evaluations if item.successful]
    coverage = len(successful) / len(evaluations) if evaluations else 0.0
    median = statistics.median(item.net_pnl_bps or 0 for item in successful) if successful else -math.inf
    delay = statistics.mean((item.signal_boundary_ms or item.event_peak_open_time_ms) -
                            item.event_entry_open_time_ms for item in successful) if successful else math.inf
    capture = statistics.mean(item.captured_excursion_ratio for item in successful) if successful else 0.0
    return coverage, median, -delay, capture


def _search(events: Sequence[BullRunEvent], observations: Sequence[CausalObservation],
            market: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
            request: ExpertAuditRequest, regime: str) -> tuple[ModuleCalibration, list[BullRunTradeEvaluation]]:
    best: tuple[ModuleCalibration, list[BullRunTradeEvaluation]] | None = None
    best_rank = (-1.0, -math.inf, -math.inf, -math.inf)
    for calibration in _candidate_calibrations(request, regime):
        evaluations = [
            _evaluate_event(event, observations, market[(event.symbol, "1m")],
                            market[(event.symbol, "5m")], calibration)
            for event in events
        ]
        rank = _rank(evaluations)
        if rank > best_rank:
            best, best_rank = (calibration, evaluations), rank
    assert best is not None
    return best


def _jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(path, b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False,
                   default=str).encode("utf-8") + b"\n" for row in rows
    ))


def _write_csv(path: Path, rows: Sequence[BullRunTradeEvaluation]) -> None:
    fields = ("event_id", "symbol", "regime", "calibration_id", "event_entry_open_time_ms",
              "event_peak_open_time_ms", "signal_boundary_ms", "entry_fill_ms", "exit_signal_ms",
              "exit_fill_ms", "entry_price", "exit_price", "gross_pnl_bps", "fees_bps",
              "impact_bps", "net_pnl_bps", "successful", "captured_excursion_ratio",
              "discrepancy_codes", "failure_reason")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in rows:
            value = item.model_dump(mode="json")
            value["discrepancy_codes"] = "|".join(value["discrepancy_codes"])
            writer.writerow({name: value.get(name) for name in fields})


def _event_svg(path: Path, event: BullRunEvent, rows: Sequence[Mapping[str, Any]],
               evaluation: BullRunTradeEvaluation) -> None:
    selected = [row for row in rows if event.entry_open_time_ms - 600_000 <= int(row["open_time_ms"]) <= event.confirmation_end_ms + 600_000]
    if not selected:
        return
    width, height, pad = 900, 300, 35
    lows, highs = [float(row["low"]) for row in selected], [float(row["high"]) for row in selected]
    low, high = min(lows), max(highs)
    span = max(1e-12, high - low)
    def x(index: int) -> float:
        return pad + index * (width - 2 * pad) / max(1, len(selected) - 1)
    def y(price: float) -> float:
        return height - pad - (price - low) / span * (height - 2 * pad)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#111827"/>']
    for index, row in enumerate(selected):
        color = "#22c55e" if float(row["close"]) >= float(row["open"]) else "#ef4444"
        lines.append(f'<line x1="{x(index):.1f}" y1="{y(float(row["high"])):.1f}" x2="{x(index):.1f}" y2="{y(float(row["low"])):.1f}" stroke="{color}"/>')
        body_y = min(y(float(row["open"])), y(float(row["close"])))
        body_h = max(2.0, abs(y(float(row["open"])) - y(float(row["close"]))))
        lines.append(f'<rect x="{x(index)-4:.1f}" y="{body_y:.1f}" width="8" height="{body_h:.1f}" fill="{color}"/>')
    for timestamp, color, label in ((evaluation.entry_fill_ms, "#38bdf8", "ENTRY"),
                                     (evaluation.exit_fill_ms, "#f59e0b", "EXIT")):
        if timestamp is None:
            continue
        nearest = min(range(len(selected)), key=lambda index: abs(int(selected[index]["open_time_ms"]) - timestamp))
        lines.append(f'<line x1="{x(nearest):.1f}" y1="10" x2="{x(nearest):.1f}" y2="{height-10}" stroke="{color}" stroke-dasharray="5 4"/>')
        lines.append(f'<text x="{x(nearest)+4:.1f}" y="20" fill="{color}" font-size="12">{label}</text>')
    lines.append(f'<text x="12" y="{height-10}" fill="#e5e7eb" font-size="13">{event.symbol} net {evaluation.net_pnl_bps if evaluation.net_pnl_bps is not None else 0:.2f} bps</text>')
    lines.append("</svg>")
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(path, "\n".join(lines).encode("utf-8"))


def _publish(output: Path, request: ExpertAuditRequest, dataset_manifest: Mapping[str, Any],
             events: Sequence[BullRunEvent], calibrations: Sequence[ModuleCalibration],
             evaluations: Sequence[BullRunTradeEvaluation], negative_window_summary: Mapping[str, Any],
             market: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=False)
    successful = [item for item in evaluations if item.successful]
    failed = [item for item in evaluations if not item.successful]
    coverage = len(successful) / len(events) if events else 0.0
    summary = {
        "schema": "bull-run-expert-audit-result/1", "event_count": len(events),
        "successful_events": len(successful), "failed_events": len(failed), "coverage": coverage,
        "coverage_gate": request.minimum_event_coverage,
        "outcome": "PASS" if coverage >= request.minimum_event_coverage else "BELOW_60_PERCENT",
        "median_net_pnl_bps": statistics.median(item.net_pnl_bps or 0 for item in successful) if successful else None,
        "mean_captured_excursion_ratio": statistics.mean(item.captured_excursion_ratio for item in successful) if successful else 0.0,
        "calibration_ids": [item.calibration_id for item in calibrations],
        "dataset_fingerprint": dataset_manifest["fingerprint"],
        "negative_window_diagnostic": dict(negative_window_summary),
        "production_mutations": 0, "paper_live_changed": False,
    }
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "SUMMARY.json", json.dumps(summary, indent=2, sort_keys=True).encode())
    _jsonl(output / "EVENT_AUDIT.jsonl", (item.model_dump(mode="json") for item in evaluations))
    _write_csv(output / "SUCCESSFUL_TRADES.csv", successful)
    _write_csv(output / "MISSED_OR_FAILED_EVENTS.csv", failed)
    corrections = {
        "schema": "module-corrections/1", "expert_rubric": EXPERT_RUBRIC_VERSION,
        "graphical_entry_rubric": {"structure": 35, "breakout_retest": 25, "candle_confirmation": 15,
                                    "multi_timeframe_alignment": 15, "invalidation_quality": 10},
        "technical_entry_rubric": {"moving_averages": 25, "macd": 15, "rsi": 10, "adx": 15,
                                    "vwap": 15, "volume": 10, "atr_bollinger": 10},
        "calibrations": [item.model_dump(mode="json") for item in calibrations],
    }
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "MODULE_CORRECTIONS.json", json.dumps(corrections, indent=2, sort_keys=True).encode())
    candidate = {"schema_version": 1, "active": False, "authority": "RESEARCH_ONLY_NOT_ACTIVATED",
                 "coverage": coverage, "minimum_net_profit_bps": request.minimum_net_profit_bps,
                 "calibrations": [item.model_dump(mode="json") for item in calibrations]}
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "RECOMMENDED_MODULE_CALIBRATION.yaml",
        yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True).encode("utf-8"))
    charts = output / "charts"
    charts.mkdir()
    by_symbol = {(event.event_id): event for event in events}
    for evaluation in evaluations:
        event = by_symbol[evaluation.event_id]
        _event_svg(charts / f"{event.event_id[:12]}_{event.symbol}.svg", event,
                   market.get((event.symbol, "5m"), ()), evaluation)
    report = [
        "# Independent bull-run module audit", "", f"Outcome: `{summary['outcome']}`", "",
        f"- Bull events: {len(events)}", f"- Successful causal trades: {len(successful)}",
        f"- Coverage: {coverage:.2%} (gate {request.minimum_event_coverage:.0%})",
        f"- Median successful net PnL: {summary['median_net_pnl_bps']} bps", "",
        "The recommendation is retrospective, research-only and inactive. Labels use future candles; verdicts and fills do not.", "",
        "## Recommended values", "", "```yaml",
        yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True).rstrip(), "```", "",
        "## Event audit", "",
    ]
    for item in evaluations:
        report.extend([
            f"### {item.symbol} — {item.event_id[:12]}", "",
            f"- Result: {'SUCCESS' if item.successful else 'FAILED'}; net `{item.net_pnl_bps}` bps; regime `{item.regime}`.",
            f"- Project: `{json.dumps(item.actual_project_verdict, sort_keys=True, default=str)}`.",
            f"- Expert entry: `{item.independent_entry_verdict.direction if item.independent_entry_verdict else 'NONE'}`; reasons `{', '.join(item.independent_entry_verdict.reasons) if item.independent_entry_verdict else 'none'}`.",
            f"- Discrepancies: `{', '.join(item.discrepancy_codes) or 'none'}`.",
            f"- Chart: `charts/{item.event_id[:12]}_{item.symbol}.svg`.", "",
        ])
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "REPORT.md", "\n".join(report).encode("utf-8"))
    integrity_files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "INTEGRITY.json":
            integrity_files[path.relative_to(output).as_posix()] = sha256(path.read_bytes()).hexdigest()
    integrity = {"schema": "bull-run-expert-audit-integrity/1", "files": integrity_files,
                 "production_mutations": 0, "active_candidate": False}
    integrity["fingerprint"] = fingerprint(integrity)
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "INTEGRITY.json", json.dumps(integrity, indent=2, sort_keys=True).encode())
    return summary


def run(request_path: Path, dataset: Path, output: Path) -> dict[str, Any]:
    _ENTRY_VERDICT_CACHE.clear()
    _EXIT_VERDICT_CACHE.clear()
    _FUTURE_ROWS_CACHE.clear()
    request = ExpertAuditRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    calibration_path = Path(request.calibration_request_path)
    calibration_request = CalibrationRequest.model_validate_json(calibration_path.read_text(encoding="utf-8"))
    manifest, candles, observations = load_dataset(dataset)
    events, diagnostics = label_bull_runs(
        candles, minimum_edge_bps=calibration_request.minimum_edge_bps,
        minimum_leg_candles=calibration_request.minimum_leg_candles,
        maximum_leg_candles=calibration_request.maximum_leg_candles,
    )
    if diagnostics["blocked_symbols"]:
        raise ValueError("BLOCKED_DATA:CANDLE_COVERAGE_INCOMPLETE")
    database = ReadOnlyResearchDatabase(resolve_database_binding())
    try:
        with database.connection() as connection:
            connection.exec_driver_sql("SET LOCAL statement_timeout='300000ms'")
            if connection.exec_driver_sql("SELECT current_setting('transaction_read_only')").scalar_one() != "on":
                raise ValueError("READONLY_SESSION_REQUIRED")
            start = calibration_request.period_start_ms - 6 * 60 * 60_000
            end = calibration_request.period_end_ms + request.maximum_holding_minutes * 60_000
            one = _load_candles(connection, calibration_request.symbols, "1m", start, end)
            five = _load_candles(connection, calibration_request.symbols, "5m", start, end)
    finally:
        database.dispose()
    market = (
        {(symbol, "1m"): tuple(one[symbol]) for symbol in calibration_request.symbols}
        | {(symbol, "5m"): tuple(five[symbol]) for symbol in calibration_request.symbols}
    )
    shared, shared_evaluations = _search(events, observations, market, request, "ALL")
    coverage = _rank(shared_evaluations)[0]
    if coverage >= request.minimum_event_coverage or request.maximum_regime_calibrations == 1:
        calibrations, evaluations = [shared], shared_evaluations
    else:
        entry_regime: dict[str, str] = {}
        for event in events:
            candidates = sorted((item for item in observations if item.symbol == event.symbol and
                                 event.entry_open_time_ms <= item.boundary_ms <= event.peak_open_time_ms + 300_000),
                                key=lambda item: item.boundary_ms)
            if candidates:
                verdict = independent_entry_verdict(event.symbol, candidates[0].boundary_ms,
                                                    market[(event.symbol, "1m")], market[(event.symbol, "5m")])
                entry_regime[event.event_id] = verdict.regime
        calibrations = []
        combined: dict[str, BullRunTradeEvaluation] = {}
        for regime in REGIMES[:request.maximum_regime_calibrations]:
            subset = [event for event in events if entry_regime.get(event.event_id) == regime]
            if not subset:
                continue
            calibration, result = _search(subset, observations, market, request, regime)
            calibrations.append(calibration)
            combined.update({item.event_id: item for item in result})
        evaluations = [combined.get(event.event_id) or next(
            item for item in shared_evaluations if item.event_id == event.event_id) for event in events]
    # Negative windows are deliberately diagnostic only for this event-conditioned study.
    outside_observations = [
        observation for observation in observations
        if not any(event.symbol == observation.symbol and
                   event.entry_open_time_ms <= observation.boundary_ms <= event.confirmation_end_ms
                   for event in events)
    ]
    negative_summary = {
        "selection_effect": "NONE",
        "reason": "OUTSIDE_LABELLED_BULL_RUN_SCOPE",
        "persisted_project_bullish_observations_outside_events": len(outside_observations),
        "warning": "REPORTED_FOR_FALSE_SIGNAL_CONTEXT_BUT_NOT_USED_TO_REJECT_EVENT_CALIBRATION",
    }
    return _publish(output, request, manifest, events, calibrations, evaluations,
                    negative_summary, market)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.request, args.dataset, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
