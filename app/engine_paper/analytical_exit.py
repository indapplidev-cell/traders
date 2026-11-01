"""Causal multi-timeframe analytical exit evidence for Scalping v2 PAPER.

The contract is authoritative evidence but SHADOW policy by default.  It uses
only closed 1m/5m candles at or before the evaluated 1m boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from time import perf_counter
from typing import Iterable

from app.config.trade_parameters import SCALPING_V2, TRADE_PARAMETERS
from app.engine_analysis import AnalysisWindowConfig, EngineAnalysisCandle, run_engine_analysis


CONTRACT_VERSION = "exit-evidence-v2"


class AnalyticalExitDecision(StrEnum):
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    ERROR = "ERROR"
    HOLD = "HOLD"
    AT_RISK = "AT_RISK"
    EXIT_CONFIRMATION_PENDING = "EXIT_CONFIRMATION_PENDING"
    ANALYTICAL_EXIT = "ANALYTICAL_EXIT"
    STRONG_REVERSAL_EXIT = "STRONG_REVERSAL_EXIT"
    PROFIT_PROTECTION_EXIT = "PROFIT_PROTECTION_EXIT"


@dataclass(frozen=True, slots=True)
class ClosedAnalysisCandle:
    symbol: str
    timeframe: str
    open_time_ms: int
    close_boundary_ms: int
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    quote_volume: Decimal | None
    trades_count: int | None
    source: str | None
    is_closed: bool


@dataclass(frozen=True, slots=True)
class ExitEvidenceV2:
    contract_version: str
    position_id: str
    symbol: str
    side: str
    causal_boundary_ms: int
    source_1m_boundary_ms: int | None
    source_5m_boundary_ms: int | None
    technical_1m: dict[str, object]
    technical_5m: dict[str, object]
    graphical_1m: dict[str, object]
    graphical_5m: dict[str, object]
    volume_1m: dict[str, object]
    component_scores: dict[str, float]
    continuation_score: float
    exit_score: float
    preceding_confirmations: int
    decision: AnalyticalExitDecision
    reason_codes: tuple[str, ...]
    target_progress: float
    current_price: str | None
    distance_to_target_bps: float | None
    distance_to_stop_bps: float | None
    mfe_bps: float | None
    mae_bps: float | None
    gross_pnl: str | None
    net_pnl: str | None
    analysis_latency_ms: int
    config_hash: str
    runtime_revision: str | None
    future_bars_used: bool = False

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["decision"] = self.decision.value
        return value


def _direction_opposed(value: object, side: str) -> bool:
    token = str(getattr(value, "value", value) or "").upper()
    bearish = "BEAR" in token or token in {"DOWN", "TREND_DOWN"}
    bullish = "BULL" in token or token in {"UP", "TREND_UP"}
    return bearish if side == "LONG" else bullish


def _engine_candles(values: tuple[ClosedAnalysisCandle, ...]) -> tuple[EngineAnalysisCandle, ...]:
    return tuple(EngineAnalysisCandle(
        timestamp=datetime.fromtimestamp(item.open_time_ms / 1000, tz=timezone.utc).isoformat(),
        open=float(item.open_price), high=float(item.high_price), low=float(item.low_price),
        close=float(item.close_price), volume=float(item.volume),
    ) for item in values)


def _causal_series(
    values: Iterable[ClosedAnalysisCandle], timeframe: str, boundary_ms: int,
) -> tuple[ClosedAnalysisCandle, ...]:
    duration = 60_000 if timeframe == "1m" else 300_000
    selected = tuple(sorted((item for item in values if (
        item.timeframe == timeframe and item.is_closed
        and item.close_boundary_ms <= boundary_ms
    )), key=lambda item: item.open_time_ms))[-AnalysisWindowConfig().context_candles:]
    if len(selected) < AnalysisWindowConfig().minimum_candles:
        return ()
    if any(current.open_time_ms - previous.open_time_ms != duration
           for previous, current in zip(selected, selected[1:])):
        return ()
    if len({item.open_time_ms for item in selected}) != len(selected):
        return ()
    return selected


def _target_progress(side: str, entry: Decimal, target: Decimal, current: Decimal) -> float:
    span = (target - entry) if side == "LONG" else (entry - target)
    moved = (current - entry) if side == "LONG" else (entry - current)
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, float(moved / span)))


def classify_analytical_exit(
    *, exit_score: float, strong_reversal: bool,
    prior_exit_scores: tuple[float, ...], net_positive: bool,
    target_progress: float,
) -> tuple[AnalyticalExitDecision, tuple[str, ...], int]:
    policy = SCALPING_V2.exit_policy.analytical_exit
    confirmations = sum(
        value >= policy.exit_threshold
        for value in prior_exit_scores[-(policy.confirmation_boundaries - 1):]
    )
    if strong_reversal and exit_score >= policy.strong_reversal_threshold:
        return (AnalyticalExitDecision.STRONG_REVERSAL_EXIT,
                ("STRUCTURE_AND_REGIME_OPPOSE_POSITION",), confirmations)
    if exit_score >= policy.exit_threshold:
        if confirmations >= policy.confirmation_boundaries - 1:
            return (AnalyticalExitDecision.ANALYTICAL_EXIT,
                    ("EXIT_SCORE_CONFIRMED",), confirmations)
        return (AnalyticalExitDecision.EXIT_CONFIRMATION_PENDING,
                ("EXIT_SCORE_AWAITS_CONFIRMATION",), confirmations)
    if (net_positive and target_progress >= policy.profit_protection_target_progress
            and exit_score >= policy.at_risk_threshold):
        return (AnalyticalExitDecision.PROFIT_PROTECTION_EXIT,
                ("POSITIVE_NET_PNL_WITH_CONTINUATION_DECAY",), confirmations)
    if exit_score >= policy.at_risk_threshold:
        return (AnalyticalExitDecision.AT_RISK,
                ("EXIT_SCORE_AT_RISK",), confirmations)
    return AnalyticalExitDecision.HOLD, (), confirmations


def analyze_position_exit(
    *, position_id: str, symbol: str, side: str,
    entry_price: Decimal, stop_price: Decimal, target_price: Decimal,
    opened_at_ms: int,
    candles_1m: Iterable[ClosedAnalysisCandle],
    candles_5m: Iterable[ClosedAnalysisCandle], boundary_ms: int,
    prior_exit_scores: tuple[float, ...] = (),
    gross_pnl: Decimal | None = None, net_pnl: Decimal | None = None,
    runtime_revision: str | None = None,
) -> ExitEvidenceV2:
    started = perf_counter()
    policy = SCALPING_V2.exit_policy.analytical_exit
    one = _causal_series(candles_1m, "1m", boundary_ms)
    five_boundary = (boundary_ms // 300_000) * 300_000
    five = _causal_series(candles_5m, "5m", five_boundary)
    empty = dict(available=False)
    if not one or not five:
        return ExitEvidenceV2(
            CONTRACT_VERSION, position_id, symbol, side, boundary_ms,
            one[-1].close_boundary_ms if one else None,
            five[-1].close_boundary_ms if five else None,
            empty, empty, empty, empty, empty,
            {"graphical_structure": 0.0, "technical_indicators": 0.0,
             "momentum_volume": 0.0, "holding_economics": 0.0},
            0.0, 0.0, 0, AnalyticalExitDecision.DATA_UNAVAILABLE,
            ("INSUFFICIENT_OR_NON_CAUSAL_OHLCV",), 0.0,
            None, None, None, None, None,
            None if gross_pnl is None else format(gross_pnl, "f"),
            None if net_pnl is None else format(net_pnl, "f"),
            int((perf_counter() - started) * 1000), TRADE_PARAMETERS.config_hash,
            runtime_revision,
        )
    try:
        output_1m = run_engine_analysis(symbol, "1m", _engine_candles(one))
        output_5m = run_engine_analysis(symbol, "5m", _engine_candles(five))
        context_1m = output_1m.composer_output.matrix.unified_context
        context_5m = output_5m.composer_output.matrix.unified_context
        technical_1m = context_1m.indicator_context.to_dict()
        technical_5m = context_5m.indicator_context.to_dict()
        graphical_1m = {
            "altunina": context_1m.altunina_context.to_dict(),
            "schwager": context_1m.schwager_context.to_dict(),
            "nison": context_1m.nison_context.to_dict(),
            "regime": output_1m.composer_output.result.market_regime.value,
        }
        graphical_5m = {
            "altunina": context_5m.altunina_context.to_dict(),
            "schwager": context_5m.schwager_context.to_dict(),
            "nison": context_5m.nison_context.to_dict(),
            "regime": output_5m.composer_output.result.market_regime.value,
        }
        structure_1m_opposed = _direction_opposed(
            context_1m.altunina_context.structure_direction, side)
        structure_5m_opposed = _direction_opposed(
            context_5m.altunina_context.structure_direction, side)
        regime_1m_opposed = _direction_opposed(
            output_1m.composer_output.result.market_regime, side)
        technical_1m_opposed = _direction_opposed(
            context_1m.indicator_context.direction, side)
        technical_5m_opposed = _direction_opposed(
            context_5m.indicator_context.direction, side)
        weights = policy.weights
        graphical = weights.graphical_structure * (
            (4.0 / 7.0 if structure_1m_opposed else 0.0)
            + (3.0 / 7.0 if structure_5m_opposed else 0.0)
        )
        technical = weights.technical_indicators * (
            (4.0 / 7.0 if technical_1m_opposed else 0.0)
            + (3.0 / 7.0 if technical_5m_opposed else 0.0)
        )
        ratio = float(context_1m.volume_context.recent_to_baseline_ratio)
        impulse = str(output_1m.json_payload.get("impulse_phase") or "").upper()
        momentum = weights.momentum_volume * (
            0.5 if regime_1m_opposed or impulse in {
            "IMPULSE_EXHAUSTION", "IMPULSE_EXHAUSTION_RISK", "POST_SPIKE_PULLBACK"
            } else 0.0
        ) + weights.momentum_volume * (0.5 if ratio < 0.80 else 0.0)
        current = one[-1].close_price
        progress = _target_progress(side, entry_price, target_price, current)
        held = tuple(item for item in one if item.close_boundary_ms > opened_at_ms)
        highest = max((item.high_price for item in held), default=current)
        lowest = min((item.low_price for item in held), default=current)
        if side == "LONG":
            target_distance = float((target_price - current) / current * Decimal("10000"))
            stop_distance = float((current - stop_price) / current * Decimal("10000"))
            mfe = float(max(Decimal("0"), highest - entry_price) / entry_price * Decimal("10000"))
            mae = float(max(Decimal("0"), entry_price - lowest) / entry_price * Decimal("10000"))
        else:
            target_distance = float((current - target_price) / current * Decimal("10000"))
            stop_distance = float((stop_price - current) / current * Decimal("10000"))
            mfe = float(max(Decimal("0"), entry_price - lowest) / entry_price * Decimal("10000"))
            mae = float(max(Decimal("0"), highest - entry_price) / entry_price * Decimal("10000"))
        economics = weights.holding_economics if (
            net_pnl is not None and net_pnl > 0
            and progress >= policy.profit_protection_target_progress
        ) else 0.0
        scores = {
            "graphical_structure": graphical,
            "technical_indicators": technical,
            "momentum_volume": momentum,
            "holding_economics": economics,
        }
        exit_score = min(100.0, sum(scores.values()))
        strong = structure_1m_opposed and regime_1m_opposed
        decision, reason_values, confirmation_count = classify_analytical_exit(
            exit_score=exit_score, strong_reversal=strong,
            prior_exit_scores=prior_exit_scores,
            net_positive=net_pnl is not None and net_pnl > 0,
            target_progress=progress,
        )
        return ExitEvidenceV2(
            CONTRACT_VERSION, position_id, symbol, side, boundary_ms,
            one[-1].close_boundary_ms, five[-1].close_boundary_ms,
            technical_1m, technical_5m, graphical_1m, graphical_5m,
            context_1m.volume_context.to_dict(), scores,
            100.0 - exit_score, exit_score, int(confirmation_count), decision,
            reason_values, progress, format(current, "f"),
            target_distance, stop_distance, mfe, mae,
            None if gross_pnl is None else format(gross_pnl, "f"),
            None if net_pnl is None else format(net_pnl, "f"),
            int((perf_counter() - started) * 1000), TRADE_PARAMETERS.config_hash,
            runtime_revision,
        )
    except Exception as error:
        return ExitEvidenceV2(
            CONTRACT_VERSION, position_id, symbol, side, boundary_ms,
            one[-1].close_boundary_ms, five[-1].close_boundary_ms,
            empty, empty, empty, empty, empty,
            {"graphical_structure": 0.0, "technical_indicators": 0.0,
             "momentum_volume": 0.0, "holding_economics": 0.0},
            0.0, 0.0, 0, AnalyticalExitDecision.ERROR,
            (f"ANALYTICAL_EXIT_{type(error).__name__}",), 0.0,
            None, None, None, None, None,
            None if gross_pnl is None else format(gross_pnl, "f"),
            None if net_pnl is None else format(net_pnl, "f"),
            int((perf_counter() - started) * 1000), TRADE_PARAMETERS.config_hash,
            runtime_revision,
        )


__all__ = (
    "AnalyticalExitDecision", "ClosedAnalysisCandle", "ExitEvidenceV2",
    "analyze_position_exit", "classify_analytical_exit",
)
