"""Canonical non-executable output model for ENGINE-STRATEGY-01."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engine_setup.setup_status import DirectionHint, SetupQuality, SetupStatus
from app.engine_setup.setup_type import SetupType
from app.engine_strategy.strategy_errors import StrategyContractError
from app.engine_strategy.strategy_status import StrategyQuality, StrategyStatus
from app.engine_strategy.strategy_type import StrategyType
from app.engine_strategy.lineage_identity import bounded_lineage_identity


_QUALITY_RANK = {"GOOD": 0, "ACCEPTABLE": 1, "WEAK": 2, "POOR": 3, "INVALID": 4, "UNKNOWN": 5}
_FORBIDDEN_CONTEXT_KEYS = {
    "entry", "stop", "target", "take_profit", "planned_rr", "rr", "outcome",
    "gross_return", "net_return", "pnl", "fee", "slippage", "position_size", "order_id",
}


def canonical_strategy_decision_identity(
    symbol: str,
    timeframe: str,
    closed_until_ms: int,
    source_setup_id: str | None,
) -> str:
    return f"{symbol.upper()}:{timeframe}:{int(closed_until_ms)}:{source_setup_id or 'NONE'}"


def strategy_decision_id(symbol: str, timeframe: str, closed_until_ms: int,
                         source_setup_id: str | None) -> str:
    canonical = canonical_strategy_decision_identity(
        symbol, timeframe, closed_until_ms, source_setup_id
    )
    return bounded_lineage_identity("strategy:v2", canonical)


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    decision_id: str
    created_at_ms: int
    source_setup_id: str | None
    source_analysis_snapshot_id: str | None
    symbol: str
    timeframe: str
    closed_until_ms: int
    decision_status: str
    strategy_type: str
    direction_hint: str
    setup_status: str
    setup_type: str
    setup_quality: str
    setup_quality_score: float | None
    strategy_score: float | None
    strategy_quality: str
    decision_reasons: list[str] = field(default_factory=list)
    decision_warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    wait_reasons: list[str] = field(default_factory=list)
    required_next_layer: str | None = None
    requires_risk_review: bool = False
    context: dict[str, Any] = field(default_factory=dict)
    strategy_quality_threshold: float | None = None
    component_scores: dict[str, float | None] = field(default_factory=dict)
    strategy_raw_score: float | None = None
    strategy_penalty_total: float | None = None
    strategy_final_score: float | None = None
    strategy_margin_to_threshold: float | None = None
    risk_approved: bool = field(default=False, init=False)
    is_executable: bool = field(default=False, init=False)
    is_trade_signal: bool = field(default=False, init=False)
    future_bars_used: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        status = StrategyStatus(self.decision_status).value
        strategy_type = StrategyType(self.strategy_type).value
        direction = DirectionHint(self.direction_hint).value
        setup_status = SetupStatus(self.setup_status).value
        setup_type = SetupType(self.setup_type).value
        setup_quality = SetupQuality(self.setup_quality).value
        strategy_quality = StrategyQuality(self.strategy_quality).value
        object.__setattr__(self, "decision_status", status)
        object.__setattr__(self, "strategy_type", strategy_type)
        object.__setattr__(self, "direction_hint", direction)
        object.__setattr__(self, "setup_status", setup_status)
        object.__setattr__(self, "setup_type", setup_type)
        object.__setattr__(self, "setup_quality", setup_quality)
        object.__setattr__(self, "strategy_quality", strategy_quality)
        object.__setattr__(self, "symbol", self.symbol.upper())
        if not self.decision_id:
            raise StrategyContractError("decision_id must not be empty")
        if self.strategy_score is not None and not 0.0 <= float(self.strategy_score) <= 100.0:
            raise StrategyContractError("strategy_score must be in the 0..100 range")
        if self.strategy_final_score is not None and self.strategy_score != self.strategy_final_score:
            raise StrategyContractError("strategy_final_score must equal strategy_score")
        allow = status == StrategyStatus.ALLOW_RESEARCH_TRADE_PLAN.value
        if bool(self.requires_risk_review) != allow:
            raise StrategyContractError("requires_risk_review is true only for allowed research plans")
        if (self.required_next_layer is not None) != allow:
            raise StrategyContractError("required_next_layer is set only for allowed research plans")
        if allow and self.required_next_layer != "engine_risk":
            raise StrategyContractError("allowed research plans require future engine_risk review")
        if strategy_quality in _QUALITY_RANK:
            if _QUALITY_RANK[strategy_quality] < _QUALITY_RANK[setup_quality]:
                raise StrategyContractError("strategy_quality cannot exceed setup_quality")
        forbidden = _FORBIDDEN_CONTEXT_KEYS.intersection(str(key).lower() for key in self.context)
        if forbidden:
            raise StrategyContractError(f"forbidden strategy context keys: {sorted(forbidden)}")

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)
