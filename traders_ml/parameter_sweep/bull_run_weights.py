"""Read-only bullish-run weight calibration for Scalping v2.

The module deliberately operates on an immutable, precomputed causal observation
dataset.  Future candles are used only by :func:`label_bull_runs`; trading
observations must carry their own causal boundary and are rejected when marked as
future-derived.  No production configuration or database row is ever mutated.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import random
from typing import Any, Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from .artifact_writer import DEFAULT_ARTIFACT_WRITER
from .result_search import fingerprint


CONTRACT_VERSION = "bull-run-weight-calibration/1"
DATASET_SCHEMA = "bull-run-causal-observations/1"
ENGINE_VERSION = "bull-run-weight-engine/1"

ENTRY_COMPONENTS = (
    "structure", "context", "momentum", "volume", "entry_quality",
    "liquidity", "confirmation",
)
EXIT_COMPONENTS = (
    "graphical_structure", "technical_indicators", "momentum_volume",
    "holding_economics",
)
BASELINE_ENTRY_WEIGHTS = {
    "structure": 25.0, "context": 15.0, "momentum": 15.0,
    "volume": 15.0, "entry_quality": 10.0, "liquidity": 10.0,
    "confirmation": 10.0,
}
BASELINE_EXIT_WEIGHTS = {
    "graphical_structure": 35.0, "technical_indicators": 35.0,
    "momentum_volume": 20.0, "holding_economics": 10.0,
}


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


def _validate_weights(model: BaseModel, names: Sequence[str]) -> BaseModel:
    values = [float(getattr(model, name)) for name in names]
    if abs(sum(values) - 100.0) > 1e-9:
        raise ValueError("weights must sum to 100")
    if max(values) > 45.0:
        raise ValueError("a single component weight cannot exceed 45")
    return model


class EntryScoreWeights(Contract):
    structure: float = Field(default=25.0, ge=0, le=45)
    context: float = Field(default=15.0, ge=0, le=45)
    momentum: float = Field(default=15.0, ge=0, le=45)
    volume: float = Field(default=15.0, ge=0, le=45)
    entry_quality: float = Field(default=10.0, ge=0, le=45)
    liquidity: float = Field(default=10.0, ge=0, le=45)
    confirmation: float = Field(default=10.0, ge=0, le=45)

    @model_validator(mode="after")
    def normalized(self) -> "EntryScoreWeights":
        return _validate_weights(self, ENTRY_COMPONENTS)  # type: ignore[return-value]


class ExitScoreWeights(Contract):
    graphical_structure: float = Field(default=35.0, ge=0, le=45)
    technical_indicators: float = Field(default=35.0, ge=0, le=45)
    momentum_volume: float = Field(default=20.0, ge=0, le=45)
    holding_economics: float = Field(default=10.0, ge=0, le=45)

    @model_validator(mode="after")
    def normalized(self) -> "ExitScoreWeights":
        return _validate_weights(self, EXIT_COMPONENTS)  # type: ignore[return-value]


class ScoreThresholds(Contract):
    entry: float = Field(default=87.75, ge=0, le=100)
    at_risk: float = Field(default=55.0, ge=0, le=100)
    exit: float = Field(default=70.0, ge=0, le=100)
    strong_reversal: float = Field(default=80.0, ge=0, le=100)

    @model_validator(mode="after")
    def ordered(self) -> "ScoreThresholds":
        if not self.at_risk < self.exit <= self.strong_reversal:
            raise ValueError("thresholds require at_risk < exit <= strong_reversal")
        return self


class WeightConfiguration(Contract):
    entry: EntryScoreWeights = Field(default_factory=EntryScoreWeights)
    exit: ExitScoreWeights = Field(default_factory=ExitScoreWeights)
    thresholds: ScoreThresholds = Field(default_factory=ScoreThresholds)

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class SplitWindow(Contract):
    name: Literal["SEARCH", "VALIDATION", "HOLDOUT"]
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self) -> "SplitWindow":
        if self.start_ms >= self.end_ms:
            raise ValueError("split start must precede end")
        return self


class AcceptanceGates(Contract):
    minimum_closed_trades: int = Field(default=100, gt=0)
    minimum_independent_days: int = Field(default=5, gt=0)
    minimum_profit_factor: float = Field(default=1.2, gt=0)
    minimum_win_rate_exclusive: float = Field(default=0.5, ge=0, lt=1)
    maximum_symbol_profit_share: float = Field(default=0.25, gt=0, le=1)


class CalibrationRequest(Contract):
    version: Literal["bull-run-weight-calibration/1"] = CONTRACT_VERSION
    symbols: tuple[str, ...]
    period_start_ms: int
    period_end_ms: int
    splits: tuple[SplitWindow, SplitWindow, SplitWindow]
    seed: int = Field(default=20261001, ge=0)
    initial_capital: float = Field(default=1000.0, gt=0)
    risk_per_trade_bps: float = Field(default=5.0, gt=0)
    maximum_open_positions: int = Field(default=2, gt=0)
    minimum_edge_bps: float = Field(default=8.0, ge=0)
    minimum_leg_candles: int = Field(default=1, ge=1, le=6)
    maximum_leg_candles: int = Field(default=6, ge=1, le=6)
    confirmation_boundaries: int = Field(default=2, ge=2, le=5)
    maximum_holding_minutes: int = Field(default=30, ge=5, le=30)
    coarse_weight_step: int = Field(default=5, ge=1, le=10)
    refinement_weight_step: int = Field(default=1, ge=1, le=5)
    max_trials: int = Field(default=500, gt=0)
    finalist_count: int = Field(default=5, gt=0, le=50)
    gates: AcceptanceGates = Field(default_factory=AcceptanceGates)

    @model_validator(mode="after")
    def validate_request(self) -> "CalibrationRequest":
        if not self.symbols or len(set(self.symbols)) != len(self.symbols):
            raise ValueError("non-empty unique symbols required")
        if self.period_start_ms >= self.period_end_ms:
            raise ValueError("invalid calibration period")
        if self.minimum_leg_candles > self.maximum_leg_candles:
            raise ValueError("minimum leg exceeds maximum leg")
        expected = ("SEARCH", "VALIDATION", "HOLDOUT")
        ordered = tuple(sorted(self.splits, key=lambda item: item.start_ms))
        if tuple(item.name for item in ordered) != expected:
            raise ValueError("splits must be chronological SEARCH, VALIDATION, HOLDOUT")
        if ordered[0].start_ms != self.period_start_ms or ordered[-1].end_ms != self.period_end_ms:
            raise ValueError("splits must cover the complete period")
        if any(left.end_ms != right.start_ms for left, right in zip(ordered, ordered[1:])):
            raise ValueError("splits must be contiguous and non-overlapping")
        object.__setattr__(self, "symbols", tuple(sorted(str(s).upper() for s in self.symbols)))
        object.__setattr__(self, "splits", ordered)
        return self

    @property
    def identity(self) -> str:
        return fingerprint(self.model_dump(mode="json"))


class Candle5m(Contract):
    symbol: str
    open_time_ms: int
    close_time_ms: int
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    atr: float = Field(default=0, ge=0)
    round_trip_cost_bps: float | None = Field(default=None, ge=0)
    checksum: str | None = None

    @model_validator(mode="after")
    def valid_ohlc(self) -> "Candle5m":
        if self.close_time_ms != self.open_time_ms + 300_000 - 1:
            raise ValueError("invalid 5m candle boundary")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("invalid OHLC envelope")
        return self


class BullRunEvent(Contract):
    event_id: str
    symbol: str
    entry_open_time_ms: int
    peak_open_time_ms: int
    confirmation_end_ms: int
    duration_candles: int
    entry_price: float
    peak_price: float
    gross_move_bps: float
    round_trip_cost_bps: float
    net_excursion_bps: float
    atr_normalized_move: float | None
    maximum_entry_delay_ms: int = 300_000
    maximum_exit_delay_ms: int = 300_000
    source_checksums: tuple[str, ...] = ()


class ExitPathPoint(Contract):
    open_time_ms: int
    close_time_ms: int
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    graphical_structure: float = Field(ge=0, le=1)
    technical_indicators: float = Field(ge=0, le=1)
    momentum_volume: float = Field(ge=0, le=1)
    strong_reversal: bool = False
    future_bars_used: bool = False
    module_verdicts: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_causal_candle(self) -> "ExitPathPoint":
        if self.close_time_ms != self.open_time_ms + 60_000 - 1:
            raise ValueError("invalid 1m exit-path boundary")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("invalid exit-path OHLC envelope")
        return self


class CausalObservation(Contract):
    observation_id: str
    symbol: str
    boundary_ms: int
    direction: str
    future_bars_used: bool = False
    hard_invalid: bool = False
    entry_components: dict[str, float]
    entry_penalty: float = Field(default=0, ge=0)
    entry_cap: float = Field(default=100, ge=0, le=100)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    target_price: float = Field(gt=0)
    entry_fee_bps: float = Field(ge=0)
    exit_fee_bps: float = Field(ge=0)
    entry_slippage_bps: float = Field(ge=0)
    exit_slippage_bps: float = Field(ge=0)
    spread_bps: float = Field(ge=0)
    adverse_fill_reserve_bps: float = Field(ge=0)
    exit_path: tuple[ExitPathPoint, ...]
    module_snapshot: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_observation(self) -> "CausalObservation":
        if set(self.entry_components) != set(ENTRY_COMPONENTS):
            raise ValueError("entry component registry mismatch")
        if any(not math.isfinite(float(v)) or not 0 <= float(v) <= 100
               for v in self.entry_components.values()):
            raise ValueError("entry components must be finite 0..100 values")
        if not self.stop_price < self.entry_price < self.target_price:
            raise ValueError("LONG observation requires stop < entry < target")
        if any(point.close_time_ms >= later.close_time_ms
               for point, later in zip(self.exit_path, self.exit_path[1:])):
            raise ValueError("exit path must be strictly chronological")
        if any(point.open_time_ms < self.boundary_ms for point in self.exit_path):
            raise ValueError("exit path precedes causal entry boundary")
        return self


@dataclass(frozen=True, slots=True)
class Trade:
    observation_id: str
    symbol: str
    entry_boundary_ms: int
    exit_boundary_ms: int
    entry_price: float
    exit_price: float
    quantity: float
    exit_reason: str
    gross_pnl: float
    fees: float
    impact_cost: float
    net_pnl: float
    gross_pnl_bps: float
    fees_bps: float
    slippage_spread_reserve_bps: float
    net_pnl_bps: float
    matched_event_id: str | None
    entry_delay_ms: int | None
    exit_delay_ms: int | None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__) if hasattr(self, "__dict__") else {
            name: getattr(self, name) for name in self.__dataclass_fields__
        }


def _candle_checksum(candle: Candle5m) -> str:
    return candle.checksum or fingerprint(candle.model_dump(mode="json"))


def _weighted_interval_selection(events: Sequence[BullRunEvent]) -> list[BullRunEvent]:
    """Maximum-net-excursion non-overlapping interval selection."""
    ordered = sorted(events, key=lambda item: (item.peak_open_time_ms, item.entry_open_time_ms, item.event_id))
    previous: list[int] = []
    for index, event in enumerate(ordered):
        candidate = -1
        for prior in range(index - 1, -1, -1):
            if ordered[prior].peak_open_time_ms < event.entry_open_time_ms:
                candidate = prior
                break
        previous.append(candidate)
    best = [0.0] * (len(ordered) + 1)
    take = [False] * len(ordered)
    for index, event in enumerate(ordered, start=1):
        include = event.net_excursion_bps + best[previous[index - 1] + 1]
        exclude = best[index - 1]
        if include > exclude + 1e-12:
            best[index] = include
            take[index - 1] = True
        else:
            best[index] = exclude
    selected: list[BullRunEvent] = []
    index = len(ordered) - 1
    while index >= 0:
        include = ordered[index].net_excursion_bps + best[previous[index] + 1]
        if take[index] and abs(best[index + 1] - include) <= 1e-9:
            selected.append(ordered[index])
            index = previous[index]
        else:
            index -= 1
    return list(reversed(selected))


def label_bull_runs(
    candles: Iterable[Candle5m], *, minimum_edge_bps: float = 8.0,
    minimum_leg_candles: int = 1, maximum_leg_candles: int = 6,
) -> tuple[list[BullRunEvent], dict[str, Any]]:
    """Label executable close-to-close bullish legs; never emits cost-less labels."""
    groups: dict[str, list[Candle5m]] = {}
    for candle in candles:
        groups.setdefault(candle.symbol.upper(), []).append(candle)
    selected: list[BullRunEvent] = []
    diagnostics: dict[str, Any] = {"schema": "bull-run-labels/1", "symbols": {}}
    for symbol, values in sorted(groups.items()):
        values.sort(key=lambda item: item.open_time_ms)
        gaps = sum(b.open_time_ms - a.open_time_ms != 300_000 for a, b in zip(values, values[1:]))
        duplicate_count = len(values) - len({item.open_time_ms for item in values})
        candidates: list[BullRunEvent] = []
        missing_cost_starts = 0
        if gaps or duplicate_count:
            diagnostics["symbols"][symbol] = {
                "outcome": "BLOCKED_DATA", "gaps": gaps, "duplicates": duplicate_count,
                "candidate_count": 0, "selected_count": 0,
            }
            continue
        for start_index, start in enumerate(values[:-minimum_leg_candles]):
            if start.round_trip_cost_bps is None:
                missing_cost_starts += 1
                continue
            previous_close = values[start_index - 1].close if start_index else math.inf
            next_close = values[start_index + 1].close
            if start.close > min(previous_close, next_close):
                continue
            for distance in range(minimum_leg_candles, maximum_leg_candles + 1):
                end_index = start_index + distance
                if end_index >= len(values):
                    break
                peak = values[end_index]
                gross = (peak.close / start.close - 1.0) * 10_000.0
                required = float(start.round_trip_cost_bps) + minimum_edge_bps
                if gross + 1e-12 < required:
                    continue
                if peak.close < max(item.close for item in values[start_index + 1:end_index + 1]):
                    continue
                checksums = tuple(_candle_checksum(item) for item in values[start_index:end_index + 1])
                payload = {"symbol": symbol, "entry": start.open_time_ms, "peak": peak.open_time_ms,
                           "checksums": checksums, "cost": start.round_trip_cost_bps}
                candidates.append(BullRunEvent(
                    event_id=fingerprint(payload), symbol=symbol,
                    entry_open_time_ms=start.open_time_ms, peak_open_time_ms=peak.open_time_ms,
                    confirmation_end_ms=peak.close_time_ms + 1,
                    duration_candles=distance, entry_price=start.close, peak_price=peak.close,
                    gross_move_bps=gross, round_trip_cost_bps=float(start.round_trip_cost_bps),
                    net_excursion_bps=gross - float(start.round_trip_cost_bps),
                    atr_normalized_move=(
                        (peak.close - start.close) / start.atr if start.atr > 0 else None
                    ), source_checksums=checksums,
                ))
        chosen = _weighted_interval_selection(candidates)
        selected.extend(chosen)
        diagnostics["symbols"][symbol] = {
            "outcome": "READY" if not missing_cost_starts else "PARTIAL_COST_COVERAGE",
            "gaps": 0, "duplicates": 0, "missing_cost_starts": missing_cost_starts,
            "candidate_count": len(candidates), "selected_count": len(chosen),
        }
    diagnostics["event_count"] = len(selected)
    diagnostics["blocked_symbols"] = sorted(
        symbol for symbol, value in diagnostics["symbols"].items()
        if value["outcome"] == "BLOCKED_DATA"
    )
    return sorted(selected, key=lambda item: (item.entry_open_time_ms, item.symbol)), diagnostics


def entry_score(observation: CausalObservation, weights: EntryScoreWeights) -> float:
    raw = sum(float(getattr(weights, name)) * observation.entry_components[name] / 100.0
              for name in ENTRY_COMPONENTS)
    return max(0.0, min(observation.entry_cap, raw - observation.entry_penalty))


def exit_score(point: ExitPathPoint, weights: ExitScoreWeights, *, economics: bool) -> float:
    factors = {
        "graphical_structure": point.graphical_structure,
        "technical_indicators": point.technical_indicators,
        "momentum_volume": point.momentum_volume,
        "holding_economics": 1.0 if economics else 0.0,
    }
    return min(100.0, sum(float(getattr(weights, name)) * factors[name] for name in EXIT_COMPONENTS))


def _match_event(observation: CausalObservation, events: Sequence[BullRunEvent]) -> BullRunEvent | None:
    eligible = [event for event in events if event.symbol == observation.symbol and
                event.entry_open_time_ms <= observation.boundary_ms <= event.peak_open_time_ms]
    return min(eligible, key=lambda item: abs(item.entry_open_time_ms - observation.boundary_ms)) if eligible else None


def replay_configuration(
    observations: Iterable[CausalObservation], events: Sequence[BullRunEvent],
    configuration: WeightConfiguration, *, confirmation_boundaries: int = 2,
    maximum_holding_minutes: int = 30, initial_capital: float = 1000.0,
    risk_per_trade_bps: float = 5.0, maximum_open_positions: int = 2,
) -> tuple[list[Trade], dict[str, Any]]:
    """Replay independent causal opportunities with stop-first conservative exits."""
    trades: list[Trade] = []
    rejection_counts: dict[str, int] = {}
    busy_until: dict[str, int] = {}
    active_exits: list[int] = []
    for observation in sorted(observations, key=lambda item: (item.boundary_ms, item.symbol)):
        active_exits = [value for value in active_exits if value > observation.boundary_ms]
        reason = None
        if observation.future_bars_used:
            reason = "FUTURE_BARS_REJECTED"
        elif observation.hard_invalid:
            reason = "HARD_INVALIDATION"
        elif observation.direction.upper() != "BULLISH":
            reason = "NON_BULLISH_DIRECTION"
        elif entry_score(observation, configuration.entry) < configuration.thresholds.entry:
            reason = "ENTRY_SCORE_BELOW_THRESHOLD"
        elif not observation.exit_path:
            reason = "EXIT_PATH_UNAVAILABLE"
        elif busy_until.get(observation.symbol, -1) > observation.boundary_ms:
            reason = "SYMBOL_POSITION_ALREADY_OPEN"
        elif len(active_exits) >= maximum_open_positions:
            reason = "PORTFOLIO_MAX_OPEN_POSITIONS"
        if reason:
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            continue
        entry_impact = observation.entry_slippage_bps
        entry_impact += observation.spread_bps / 2.0 + observation.adverse_fill_reserve_bps / 2.0
        effective_entry = observation.entry_price * (1.0 + entry_impact / 10_000.0)
        prior_scores: list[float] = []
        exit_price = observation.exit_path[-1].close
        exit_boundary = observation.exit_path[-1].close_time_ms + 1
        exit_reason = "TIME_STOP"
        for index, point in enumerate(observation.exit_path):
            if point.future_bars_used:
                rejection_counts["EXIT_FUTURE_BARS_REJECTED"] = rejection_counts.get(
                    "EXIT_FUTURE_BARS_REJECTED", 0) + 1
                break
            if point.low <= observation.stop_price:
                exit_price, exit_boundary, exit_reason = observation.stop_price, point.close_time_ms + 1, "STOP"
                break
            if point.high >= observation.target_price:
                exit_price, exit_boundary, exit_reason = observation.target_price, point.close_time_ms + 1, "TARGET"
                break
            gross_so_far = (point.close / effective_entry - 1.0) * 10_000.0
            progress = max(0.0, min(1.0, (point.close - observation.entry_price) /
                                      (observation.target_price - observation.entry_price)))
            economics = gross_so_far > observation.exit_fee_bps and progress >= 0.5
            score = exit_score(point, configuration.exit, economics=economics)
            strong = point.strong_reversal and score >= configuration.thresholds.strong_reversal
            confirmed = score >= configuration.thresholds.exit and sum(
                value >= configuration.thresholds.exit
                for value in prior_scores[-(confirmation_boundaries - 1):]
            ) >= confirmation_boundaries - 1
            profit_protection = economics and score >= configuration.thresholds.at_risk
            prior_scores.append(score)
            if strong or confirmed or profit_protection:
                next_index = min(index + 1, len(observation.exit_path) - 1)
                fill = observation.exit_path[next_index]
                exit_price, exit_boundary = fill.open, fill.open_time_ms
                exit_reason = "STRONG_REVERSAL" if strong else (
                    "ANALYTICAL_EXIT" if confirmed else "PROFIT_PROTECTION"
                )
                break
            if point.close_time_ms + 1 - observation.boundary_ms >= maximum_holding_minutes * 60_000:
                exit_price, exit_boundary, exit_reason = point.close, point.close_time_ms + 1, "TIME_STOP"
                break
        exit_impact = observation.exit_slippage_bps + observation.spread_bps / 2.0
        exit_impact += observation.adverse_fill_reserve_bps / 2.0
        effective_exit = exit_price * (1.0 - exit_impact / 10_000.0)
        gross_bps = (exit_price / observation.entry_price - 1.0) * 10_000.0
        fees = observation.entry_fee_bps + observation.exit_fee_bps
        impacts = entry_impact + exit_impact
        # The bps ledger is deliberately additive and independently auditable.
        # Effective prices are retained for explainability, while the accounting
        # identity below is the authoritative research PnL contract.
        net_bps = gross_bps - fees - impacts
        risk_budget = initial_capital * risk_per_trade_bps / 10_000.0
        risk_per_unit = effective_entry - observation.stop_price
        if risk_per_unit <= 0:
            rejection_counts["NONPOSITIVE_INITIAL_RISK"] = rejection_counts.get(
                "NONPOSITIVE_INITIAL_RISK", 0
            ) + 1
            continue
        quantity = risk_budget / risk_per_unit
        gross_money = (exit_price - observation.entry_price) * quantity
        fee_money = (observation.entry_fee_bps * observation.entry_price +
                     observation.exit_fee_bps * exit_price) * quantity / 10_000.0
        impact_money = impacts * observation.entry_price * quantity / 10_000.0
        net_money = gross_money - fee_money - impact_money
        event = _match_event(observation, events)
        trades.append(Trade(
            observation_id=observation.observation_id, symbol=observation.symbol,
            entry_boundary_ms=observation.boundary_ms, exit_boundary_ms=exit_boundary,
            entry_price=effective_entry, exit_price=effective_exit, quantity=quantity,
            exit_reason=exit_reason, gross_pnl=gross_money, fees=fee_money,
            impact_cost=impact_money, net_pnl=net_money,
            gross_pnl_bps=gross_bps, fees_bps=fees,
            slippage_spread_reserve_bps=impacts, net_pnl_bps=net_bps,
            matched_event_id=event.event_id if event else None,
            entry_delay_ms=(observation.boundary_ms - event.entry_open_time_ms) if event else None,
            exit_delay_ms=(exit_boundary - event.confirmation_end_ms) if event else None,
        ))
        busy_until[observation.symbol] = exit_boundary
        active_exits.append(exit_boundary)
    return trades, {"rejections": rejection_counts, "observations": len(list(observations))
                    if isinstance(observations, Sequence) else None}


def trade_metrics(trades: Sequence[Trade]) -> dict[str, Any]:
    pnl = [trade.net_pnl for trade in trades]
    pnl_bps = [trade.net_pnl_bps for trade in trades]
    wins = [value for value in pnl if value > 0]
    losses = [-value for value in pnl if value < 0]
    equity = peak = drawdown = 0.0
    equity_bps = peak_bps = drawdown_bps = 0.0
    by_symbol: dict[str, float] = {}
    days: set[str] = set()
    for trade in trades:
        equity += trade.net_pnl
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        equity_bps += trade.net_pnl_bps
        peak_bps = max(peak_bps, equity_bps)
        drawdown_bps = max(drawdown_bps, peak_bps - equity_bps)
        by_symbol[trade.symbol] = by_symbol.get(trade.symbol, 0.0) + trade.net_pnl
        days.add(datetime.fromtimestamp(trade.entry_boundary_ms / 1000, timezone.utc).date().isoformat())
    positive_total = sum(max(0.0, value) for value in by_symbol.values())
    concentration = max((max(0.0, value) / positive_total for value in by_symbol.values()), default=0.0)
    matched = [trade for trade in trades if trade.matched_event_id]
    return {
        "closed_trades": len(trades), "wins": len(wins), "losses": len(losses),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "net_pnl": sum(pnl), "expectancy": sum(pnl) / len(pnl) if pnl else 0.0,
        "net_pnl_bps": sum(pnl_bps),
        "expectancy_bps": sum(pnl_bps) / len(pnl_bps) if pnl_bps else 0.0,
        # Keep artifacts strict-JSON. A lossless cohort has an explicit flag and
        # a finite ranking sentinel rather than a non-standard Infinity token.
        "profit_factor": sum(wins) / sum(losses) if losses else (1_000_000.0 if wins else 0.0),
        "profit_factor_no_losses": bool(wins and not losses),
        "max_drawdown": drawdown, "max_drawdown_bps": drawdown_bps,
        "independent_days": len(days),
        "symbol_coverage": len({trade.symbol for trade in trades}),
        "maximum_symbol_profit_share": concentration,
        "bull_event_matched_trades": len(matched),
        "false_entry_trades": len(trades) - len(matched),
        "false_entry_net_pnl": sum(trade.net_pnl for trade in trades if not trade.matched_event_id),
        "false_entry_net_pnl_bps": sum(trade.net_pnl_bps for trade in trades if not trade.matched_event_id),
        "mean_entry_delay_ms": (
            sum(trade.entry_delay_ms or 0 for trade in matched) / len(matched) if matched else None
        ),
        "mean_exit_delay_ms": (
            sum(trade.exit_delay_ms or 0 for trade in matched) / len(matched) if matched else None
        ),
        "net_pnl_by_symbol": dict(sorted(by_symbol.items())),
    }


def acceptance_failures(metrics: Mapping[str, Any], baseline: Mapping[str, Any],
                        gates: AcceptanceGates) -> list[str]:
    failures: list[str] = []
    predicates = (
        (metrics["closed_trades"] >= gates.minimum_closed_trades, "MINIMUM_CLOSED_TRADES"),
        (metrics["independent_days"] >= gates.minimum_independent_days, "MINIMUM_INDEPENDENT_DAYS"),
        (metrics["net_pnl"] > 0, "NET_PNL_POSITIVE"),
        (metrics["expectancy"] > 0, "EXPECTANCY_POSITIVE"),
        (metrics["profit_factor"] >= gates.minimum_profit_factor, "PROFIT_FACTOR"),
        (metrics["win_rate"] > gates.minimum_win_rate_exclusive, "WIN_RATE"),
        (metrics["max_drawdown"] <= baseline["max_drawdown"] + 1e-9, "DRAWDOWN_BASELINE"),
        (metrics["maximum_symbol_profit_share"] <= gates.maximum_symbol_profit_share,
         "SYMBOL_PROFIT_CONCENTRATION"),
        (metrics["false_entry_net_pnl"] >= 0, "NEGATIVE_WINDOW_PNL"),
    )
    failures.extend(name for passed, name in predicates if not passed)
    return failures


def pareto_front(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    def dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        lm, rm = left["metrics"], right["metrics"]
        values = (
            (lm["net_pnl"], rm["net_pnl"], True),
            (lm["expectancy"], rm["expectancy"], True),
            (lm["profit_factor"], rm["profit_factor"], True),
            (lm["max_drawdown"], rm["max_drawdown"], False),
            (lm["mean_entry_delay_ms"] or math.inf, rm["mean_entry_delay_ms"] or math.inf, False),
        )
        no_worse = all(a >= b if maximize else a <= b for a, b, maximize in values)
        better = any(a > b if maximize else a < b for a, b, maximize in values)
        return no_worse and better
    return [row for row in rows if not any(dominates(other, row) for other in rows if other is not row)]


def _perturb_weights(baseline: Mapping[str, float], step: int) -> Iterable[dict[str, float]]:
    names = tuple(baseline)
    yield dict(baseline)
    for source, target in itertools.permutations(names, 2):
        candidate = dict(baseline)
        if candidate[source] >= step and candidate[target] + step <= 45:
            candidate[source] -= step
            candidate[target] += step
            yield candidate


def candidate_configurations(request: CalibrationRequest) -> list[WeightConfiguration]:
    """Deterministic bounded sensitivity plus random simplex exploration."""
    candidates = _sensitivity_configurations(request)
    rng = random.Random(request.seed)
    while len(candidates) < request.max_trials:
        config = _sample_configuration(request, lambda name, values: rng.choice(tuple(values)))
        candidates[config.identity] = config
    return list(candidates.values())[:request.max_trials]


def _sensitivity_configurations(request: CalibrationRequest) -> dict[str, WeightConfiguration]:
    baseline = WeightConfiguration()
    candidates: dict[str, WeightConfiguration] = {baseline.identity: baseline}
    entry_candidates = list(_perturb_weights(BASELINE_ENTRY_WEIGHTS, request.coarse_weight_step))
    exit_candidates = list(_perturb_weights(BASELINE_EXIT_WEIGHTS, request.coarse_weight_step))
    for entry in entry_candidates:
        config = WeightConfiguration(entry=EntryScoreWeights(**entry))
        candidates[config.identity] = config
    for exit_values in exit_candidates:
        config = WeightConfiguration(exit=ExitScoreWeights(**exit_values))
        candidates[config.identity] = config
    for entry_threshold in (75.0, 80.0, 85.0, 87.75, 90.0):
        for exit_threshold in (65.0, 70.0, 75.0):
            strong = max(80.0, exit_threshold)
            config = WeightConfiguration(thresholds=ScoreThresholds(
                entry=entry_threshold, at_risk=min(55.0, exit_threshold - 5.0),
                exit=exit_threshold, strong_reversal=strong,
            ))
            candidates[config.identity] = config
    return candidates


def _normalized_sample(names: Sequence[str], raw: Sequence[float], step: int) -> dict[str, float]:
    total = sum(raw)
    values = [round(value / total * 100 / step) * step for value in raw]
    difference = 100.0 - sum(values)
    values[values.index(max(values))] += difference
    if max(values) > 45 or min(values) < 0:
        # Deterministic projection toward the uniform simplex. This preserves
        # the TPE proposal ordering while satisfying the public weight contract.
        uniform = 100.0 / len(values)
        while max(values) > 45 or min(values) < 0:
            values = [round(((value + uniform) / 2.0) / step) * step for value in values]
            values[values.index(max(values))] += 100.0 - sum(values)
    return dict(zip(names, values))


def _sample_configuration(request: CalibrationRequest, choose) -> WeightConfiguration:
    entry_raw = [float(choose(f"entry_raw_{name}", tuple(range(1, 101)))) for name in ENTRY_COMPONENTS]
    exit_raw = [float(choose(f"exit_raw_{name}", tuple(range(1, 101)))) for name in EXIT_COMPONENTS]
    entry_values = _normalized_sample(ENTRY_COMPONENTS, entry_raw, request.refinement_weight_step)
    exit_values = _normalized_sample(EXIT_COMPONENTS, exit_raw, request.refinement_weight_step)
    entry_threshold = float(choose("entry_threshold", (75.0, 80.0, 85.0, 87.75, 90.0)))
    exit_threshold = float(choose("exit_threshold", (65.0, 70.0, 75.0)))
    at_risk = float(choose("at_risk_threshold", tuple(
        value for value in (50.0, 55.0, 60.0) if value < exit_threshold
    )))
    strong = float(choose("strong_reversal_threshold", tuple(
        value for value in (80.0, 85.0, 90.0) if value >= exit_threshold
    )))
    return WeightConfiguration(
        entry=EntryScoreWeights(**entry_values), exit=ExitScoreWeights(**exit_values),
        thresholds=ScoreThresholds(entry=entry_threshold, at_risk=at_risk,
                                   exit=exit_threshold, strong_reversal=strong),
    )


def _split_rows(request: CalibrationRequest, observations: Sequence[CausalObservation],
                events: Sequence[BullRunEvent], name: str) -> tuple[list[CausalObservation], list[BullRunEvent]]:
    split = next(item for item in request.splits if item.name == name)
    rows = [item for item in observations if split.start_ms <= item.boundary_ms < split.end_ms]
    labels = [item for item in events if split.start_ms <= item.entry_open_time_ms < split.end_ms
              and item.confirmation_end_ms <= split.end_ms]
    return rows, labels


def run_search(request: CalibrationRequest, observations: Sequence[CausalObservation],
               events: Sequence[BullRunEvent]) -> dict[str, Any]:
    baseline = WeightConfiguration()
    search_rows, search_events = _split_rows(request, observations, events, "SEARCH")
    validation_rows, validation_events = _split_rows(request, observations, events, "VALIDATION")
    holdout_rows, holdout_events = _split_rows(request, observations, events, "HOLDOUT")
    baseline_trades, _ = replay_configuration(search_rows, search_events, baseline,
        confirmation_boundaries=request.confirmation_boundaries,
        maximum_holding_minutes=request.maximum_holding_minutes,
        initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
        maximum_open_positions=request.maximum_open_positions)
    baseline_metrics = trade_metrics(baseline_trades)
    evaluated: list[dict[str, Any]] = []
    evaluated_by_hash: dict[str, dict[str, Any]] = {}

    def evaluate(config: WeightConfiguration) -> dict[str, Any]:
        existing = evaluated_by_hash.get(config.identity)
        if existing is not None:
            return existing
        trades, diagnostics = replay_configuration(search_rows, search_events, config,
            confirmation_boundaries=request.confirmation_boundaries,
            maximum_holding_minutes=request.maximum_holding_minutes,
            initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
            maximum_open_positions=request.maximum_open_positions)
        row = {"configuration": config.model_dump(mode="json"),
               "configuration_hash": config.identity,
               "metrics": trade_metrics(trades), "diagnostics": diagnostics}
        evaluated.append(row)
        evaluated_by_hash[config.identity] = row
        return row

    seeds = list(_sensitivity_configurations(request).values())[:request.max_trials]
    for config in seeds:
        evaluate(config)
    optimizer = "SENSITIVITY_ONLY"
    remaining = request.max_trials - len(evaluated)
    if remaining > 0:
        try:
            import optuna
        except ImportError as error:
            raise ValueError("OPTUNA_RESEARCH_DEPENDENCY_REQUIRED") from error
        optimizer = "OPTUNA_TPE_SINGLE_WORKER"
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            directions=("maximize", "maximize", "minimize", "minimize"),
            sampler=optuna.samplers.TPESampler(seed=request.seed),
        )

        def objective(trial):
            def choose(name: str, values: Sequence[float | int]):
                return trial.suggest_categorical(name, tuple(values))
            config = _sample_configuration(request, choose)
            row = evaluate(config)
            metrics = row["metrics"]
            trial.set_user_attr("configuration_hash", config.identity)
            delay = metrics["mean_entry_delay_ms"]
            return (metrics["net_pnl"], metrics["profit_factor"], metrics["max_drawdown"],
                    float(delay) if delay is not None else 1e15)

        study.optimize(objective, n_trials=remaining, n_jobs=1, show_progress_bar=False)
        # Duplicate TPE proposals are legitimate but do not consume the unique
        # configuration budget. Fill any remainder deterministically.
        if len(evaluated) < request.max_trials:
            for config in candidate_configurations(request):
                evaluate(config)
                if len(evaluated) >= request.max_trials:
                    break
    front = pareto_front(evaluated)
    front.sort(key=lambda row: (
        -row["metrics"]["net_pnl"], -row["metrics"]["profit_factor"],
        row["metrics"]["max_drawdown"], row["configuration_hash"],
    ))
    validation: list[dict[str, Any]] = []
    for row in front[:request.finalist_count]:
        config = WeightConfiguration.model_validate(row["configuration"])
        trades, _ = replay_configuration(validation_rows, validation_events, config,
            confirmation_boundaries=request.confirmation_boundaries,
            maximum_holding_minutes=request.maximum_holding_minutes,
            initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
            maximum_open_positions=request.maximum_open_positions)
        metrics = trade_metrics(trades)
        validation.append(row | {"validation_metrics": metrics,
                                 "validation_trades": [trade.to_dict() for trade in trades]})
    frozen = sorted(validation, key=lambda row: (
        -row["validation_metrics"]["net_pnl"],
        -row["validation_metrics"]["profit_factor"],
        row["validation_metrics"]["max_drawdown"], row["configuration_hash"],
    ))
    frozen_hash = fingerprint([row["configuration_hash"] for row in frozen])
    holdout: list[dict[str, Any]] = []
    baseline_holdout_trades, _ = replay_configuration(holdout_rows, holdout_events, baseline,
        confirmation_boundaries=request.confirmation_boundaries,
        maximum_holding_minutes=request.maximum_holding_minutes,
        initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
        maximum_open_positions=request.maximum_open_positions)
    baseline_holdout = trade_metrics(baseline_holdout_trades)
    for row in frozen:
        config = WeightConfiguration.model_validate(row["configuration"])
        repeated, _ = replay_configuration(holdout_rows, holdout_events, config,
            confirmation_boundaries=request.confirmation_boundaries,
            maximum_holding_minutes=request.maximum_holding_minutes,
            initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
            maximum_open_positions=request.maximum_open_positions)
        metrics = trade_metrics(repeated)
        replayed, _ = replay_configuration(holdout_rows, holdout_events, config,
            confirmation_boundaries=request.confirmation_boundaries,
            maximum_holding_minutes=request.maximum_holding_minutes,
            initial_capital=request.initial_capital, risk_per_trade_bps=request.risk_per_trade_bps,
            maximum_open_positions=request.maximum_open_positions)
        if [trade.to_dict() for trade in repeated] != [trade.to_dict() for trade in replayed]:
            raise ValueError("NONDETERMINISTIC_HOLDOUT_REPLAY")
        failures = acceptance_failures(metrics, baseline_holdout, request.gates)
        holdout.append(row | {"holdout_metrics": metrics, "acceptance_failures": failures,
                              "eligible": not failures,
                              "holdout_trades": [trade.to_dict() for trade in repeated]})
    eligible = [row for row in holdout if row["eligible"]]
    return {
        "schema": "bull-run-search-result/1", "engine": ENGINE_VERSION,
        "request_hash": request.identity, "baseline_configuration": baseline.model_dump(mode="json"),
        "baseline_search_metrics": baseline_metrics, "baseline_holdout_metrics": baseline_holdout,
        "optimizer": optimizer, "optimizer_seed": request.seed, "optimizer_workers": 1,
        "evaluated_count": len(evaluated), "pareto_count": len(front),
        "finalists_frozen_hash": frozen_hash, "finalists": holdout,
        "outcome": "ELIGIBLE_CANDIDATE" if eligible else "NO_ELIGIBLE_CANDIDATE",
        "selected": eligible[0] if eligible else None,
        "holdout_opened_after_finalist_freeze": True,
    }


def _atomic_json(path: Path, value: Any) -> None:
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(path, json.dumps(
        value, sort_keys=True, allow_nan=False, indent=2, default=str,
    ).encode("utf-8"))


def _jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    data = b"".join(json.dumps(row, sort_keys=True, allow_nan=False, separators=(",", ":"),
                               default=str).encode("utf-8") + b"\n" for row in rows)
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(path, data)


def load_dataset(directory: Path) -> tuple[dict[str, Any], list[Candle5m], list[CausalObservation]]:
    manifest = json.loads((directory / "DATASET_MANIFEST.json").read_text(encoding="utf-8"))
    candles_data = (directory / "CANDLES_5M.jsonl").read_bytes()
    observations_data = (directory / "CAUSAL_OBSERVATIONS.jsonl").read_bytes()
    if sha256(candles_data).hexdigest() != manifest["candles_sha256"]:
        raise ValueError("CANDLE_DATASET_CHECKSUM_MISMATCH")
    if sha256(observations_data).hexdigest() != manifest["observations_sha256"]:
        raise ValueError("OBSERVATION_DATASET_CHECKSUM_MISMATCH")
    candles = [Candle5m.model_validate_json(line) for line in candles_data.splitlines()]
    observations = [CausalObservation.model_validate_json(line) for line in observations_data.splitlines()]
    claimed = manifest.pop("fingerprint")
    try:
        if fingerprint(manifest) != claimed:
            raise ValueError("DATASET_MANIFEST_FINGERPRINT_MISMATCH")
    finally:
        manifest["fingerprint"] = claimed
    return manifest, candles, observations


def publish_report(output: Path, request: CalibrationRequest, dataset_manifest: Mapping[str, Any],
                   events: Sequence[BullRunEvent], labels: Mapping[str, Any],
                   result: Mapping[str, Any]) -> None:
    if output.exists():
        raise ValueError("OUTPUT_DIRECTORY_ALREADY_EXISTS")
    output.mkdir(parents=True, exist_ok=False)
    _atomic_json(output / "REQUEST.json", request.model_dump(mode="json"))
    _atomic_json(output / "DATASET_REFERENCE.json", dict(dataset_manifest))
    _atomic_json(output / "LABEL_MANIFEST.json", dict(labels))
    _jsonl(output / "BULL_RUN_EVENTS.jsonl", (event.model_dump(mode="json") for event in events))
    _atomic_json(output / "SEARCH_RESULT.json", result)
    finalists = result["finalists"]
    _atomic_json(output / "FINALISTS.json", finalists)
    selected = result.get("selected")
    candidate = {
        "schema_version": 1, "active": False, "authority": "RESEARCH_ONLY_NOT_ACTIVATED",
        "request_hash": request.identity, "dataset_fingerprint": dataset_manifest["fingerprint"],
        "configuration": selected["configuration"] if selected else None,
        "external_november_holdout": "REQUIRED_AFTER_2026-12-01",
    }
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "INACTIVE_CANDIDATE.yaml",
        yaml.safe_dump(candidate, sort_keys=False, allow_unicode=True).encode("utf-8"))
    trades = selected["holdout_trades"] if selected else [
        trade for row in finalists for trade in row.get("holdout_trades", [])
    ]
    columns = list(trades[0]) if trades else ["observation_id", "symbol", "net_pnl_bps"]
    csv_path = output / "TRADES.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trades)
    report = [
        "# Bull-run weight calibration", "", f"Outcome: `{result['outcome']}`", "",
        "## Safety", "", "- Read-only offline research; production parameters were not changed.",
        "- The candidate YAML is inactive and cannot enable PAPER or LIVE.",
        "- November 2026 external holdout remains mandatory after 2026-12-01.", "",
        "## Dataset and labels", "", f"- Dataset: `{dataset_manifest['fingerprint']}`",
        f"- Symbols: {len(request.symbols)}", f"- Bull events: {len(events)}",
        f"- Blocked symbols: {', '.join(labels.get('blocked_symbols', [])) or 'none'}", "",
        "## Search", "", f"- Evaluated configurations: {result['evaluated_count']}",
        f"- Pareto configurations: {result['pareto_count']}",
        f"- Frozen finalists hash: `{result['finalists_frozen_hash']}`", "",
        "## Baseline holdout", "", "```json",
        json.dumps(result["baseline_holdout_metrics"], indent=2, sort_keys=True, default=str), "```", "",
    ]
    if selected:
        report.extend(["## Selected inactive candidate", "", f"- Hash: `{selected['configuration_hash']}`",
                       "- Acceptance gates: PASS", "", "```json",
                       json.dumps(selected["holdout_metrics"], indent=2, sort_keys=True, default=str), "```", ""])
    else:
        report.extend(["## Selection", "", "No finalist passed every mandatory gate. No candidate was activated.", ""])
    DEFAULT_ARTIFACT_WRITER.atomic_bytes(output / "REPORT.md", "\n".join(report).encode("utf-8"))
    evidence = {}
    for path in sorted(output.iterdir()):
        if path.name == "INTEGRITY.json" or not path.is_file():
            continue
        evidence[path.name] = sha256(path.read_bytes()).hexdigest()
    integrity = {"schema": "bull-run-integrity/1", "files": evidence,
                 "production_mutations": 0, "live_enabled": False,
                 "candidate_active": False}
    integrity["fingerprint"] = fingerprint(integrity)
    _atomic_json(output / "INTEGRITY.json", integrity)


def run(request_path: Path, dataset: Path, output: Path) -> dict[str, Any]:
    request = CalibrationRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    manifest, candles, observations = load_dataset(dataset)
    if manifest.get("schema") != DATASET_SCHEMA:
        raise ValueError("UNSUPPORTED_BULL_RUN_DATASET_SCHEMA")
    if tuple(sorted(manifest["symbols"])) != request.symbols:
        raise ValueError("REQUEST_DATASET_SYMBOL_MISMATCH")
    if manifest.get("evidence_quality") != "HISTORICAL_VERIFIED":
        raise ValueError("BLOCKED_DATA:HISTORICAL_COST_OR_CAUSAL_EVIDENCE_INCOMPLETE")
    events, labels = label_bull_runs(candles, minimum_edge_bps=request.minimum_edge_bps,
        minimum_leg_candles=request.minimum_leg_candles,
        maximum_leg_candles=request.maximum_leg_candles)
    if labels["blocked_symbols"]:
        raise ValueError("BLOCKED_DATA:CANDLE_COVERAGE_INCOMPLETE")
    result = run_search(request, observations, events)
    publish_report(output, request, manifest, events, labels, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    try:
        result = run(args.request, args.dataset, args.output)
    except (OSError, ValueError) as error:
        print("BULL_RUN_WEIGHT_CALIBRATION = FAILED")
        print(f"REASON = {error}")
        raise SystemExit(2) from None
    print(f"BULL_RUN_WEIGHT_CALIBRATION = {result['outcome']}")
    print(args.output / "REPORT.md")


if __name__ == "__main__":
    main()
