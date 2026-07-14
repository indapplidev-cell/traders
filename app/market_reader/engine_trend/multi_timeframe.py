"""Multi-timeframe confluence without allowing higher frames to invent a signal."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from app.market_reader.engine_trend.analysis_contract import interval_duration
from app.market_reader.engine_trend.engine import EngineTrendFacadeOutput, run_engine_trend
from app.market_reader.engine_trend.schemas import (
    EngineTrendCandle,
    EngineTrendRegime,
    EngineTrendSafety,
)


class TimeframeAlignment(str, Enum):
    ALIGNED = "ALIGNED"
    MIXED = "MIXED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class MultiTimeframeResult:
    symbol: str
    decision_interval: str
    market_regime: EngineTrendRegime
    confidence: float
    alignment: TimeframeAlignment
    interval_regimes: dict[str, str]
    reason_codes: tuple[str, ...]
    outputs: dict[str, EngineTrendFacadeOutput]
    safety: EngineTrendSafety = EngineTrendSafety()

    def to_dict(self) -> dict[str, Any]:
        return {
            "service": "ENGINE_TREND_MULTI_TIMEFRAME",
            "contract_version": "engine_trend_mtf_v1",
            "symbol": self.symbol,
            "decision_interval": self.decision_interval,
            "market_regime": self.market_regime.value,
            "confidence": self.confidence,
            "alignment": self.alignment.value,
            "interval_regimes": dict(self.interval_regimes),
            "reason_codes": list(self.reason_codes),
            "timeframes": {
                interval: output.to_dict() for interval, output in self.outputs.items()
            },
            "safety": self.safety.to_dict(),
        }


def run_multi_timeframe_engine_trend(
    symbol: str,
    candles_by_interval: Mapping[
        str, Sequence[EngineTrendCandle]
    ],
    *,
    decision_interval: str,
) -> MultiTimeframeResult:
    """Return one decision-frame regime checked against higher-frame context."""

    if decision_interval not in candles_by_interval:
        raise ValueError("decision_interval is absent from candles_by_interval")
    ordered_intervals = sorted(candles_by_interval, key=interval_duration)
    decision_duration = interval_duration(decision_interval)
    outputs = {
        interval: run_engine_trend(symbol, interval, tuple(candles_by_interval[interval]))
        for interval in ordered_intervals
    }
    decision = outputs[decision_interval].composer_output.result
    higher = [
        output.composer_output.result
        for interval, output in outputs.items()
        if interval_duration(interval) > decision_duration
    ]
    regimes = {
        interval: output.composer_output.result.market_regime.value
        for interval, output in outputs.items()
    }
    codes = ["MTF_DECISION_FRAME_PRESERVED"]
    selected = decision.market_regime
    confidence = decision.confidence
    directional = {EngineTrendRegime.UP, EngineTrendRegime.DOWN}
    higher_directional = [item.market_regime for item in higher if item.market_regime in directional]

    if not higher:
        alignment = TimeframeAlignment.INSUFFICIENT
        codes.append("MTF_NO_HIGHER_TIMEFRAME")
    elif selected in directional and any(item is not selected for item in higher_directional):
        selected = EngineTrendRegime.UNKNOWN
        confidence = min(0.35, confidence)
        alignment = TimeframeAlignment.CONFLICTED
        codes.extend(("MTF_DIRECTIONAL_CONFLICT", "MTF_UNKNOWN_SELECTED"))
    elif selected in directional and higher_directional and all(
        item is selected for item in higher_directional
    ):
        alignment = TimeframeAlignment.ALIGNED
        confidence = min(1.0, confidence + min(0.10, 0.04 * len(higher_directional)))
        codes.append(f"MTF_{selected.value}_ALIGNED")
    elif selected is EngineTrendRegime.UNKNOWN:
        alignment = TimeframeAlignment.INSUFFICIENT
        codes.append("MTF_CANNOT_PROMOTE_UNKNOWN_DECISION_FRAME")
    else:
        alignment = TimeframeAlignment.MIXED
        codes.append("MTF_NON_DIRECTIONAL_DECISION_FRAME")

    return MultiTimeframeResult(
        symbol=symbol,
        decision_interval=decision_interval,
        market_regime=selected,
        confidence=confidence,
        alignment=alignment,
        interval_regimes=regimes,
        reason_codes=tuple(codes),
        outputs=outputs,
    )
