"""Canonical paper-only output model for ENGINE-PAPER-01."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

from app.engine_paper.paper_errors import PaperContractError
from app.engine_paper.paper_plan_direction import PaperPlanDirection
from app.engine_paper.paper_plan_status import PaperPlanStatus
from app.engine_paper.paper_plan_type import PaperPlanType


PLAN_QUALITIES = frozenset({"GOOD", "ACCEPTABLE", "WEAK", "REJECTED", "WAITING",
                            "UNKNOWN", "ERROR"})


def paper_plan_id(symbol: str, timeframe: str, closed_until_ms: int,
                  source_risk_decision_id: str | None) -> str:
    identity = f"{symbol.upper()}:{timeframe}:{int(closed_until_ms)}:{source_risk_decision_id or 'NONE'}"
    return f"paper:{identity}:{sha256(identity.encode()).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class PaperTradePlan:
    paper_plan_id: str
    created_at_ms: int
    source_risk_decision_id: str | None
    source_strategy_decision_id: str | None
    source_setup_id: str | None
    source_analysis_snapshot_id: str | None
    symbol: str
    timeframe: str
    closed_until_ms: int
    paper_status: str
    paper_plan_type: str
    paper_direction: str
    source_risk_status: str
    source_risk_level: str
    source_risk_score: float | None
    source_strategy_type: str | None
    source_strategy_quality: str | None
    source_direction_hint: str | None
    hypothetical_entry_reference: float | None = None
    hypothetical_invalidation_level: float | None = None
    hypothetical_stop_level: float | None = None
    hypothetical_target_level: float | None = None
    planned_rr: float | None = None
    entry_reference_source: str | None = None
    invalidation_source: str | None = None
    stop_source: str | None = None
    target_source: str | None = None
    plan_quality: str = "UNKNOWN"
    plan_score: float | None = None
    plan_reasons: list[str] = field(default_factory=list)
    plan_warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    wait_reasons: list[str] = field(default_factory=list)
    paper_context: dict[str, Any] = field(default_factory=dict)
    paper_only: bool = field(default=True, init=False)
    is_executable: bool = field(default=False, init=False)
    is_trade_signal: bool = field(default=False, init=False)
    order_approved: bool = field(default=False, init=False)
    execution_approved: bool = field(default=False, init=False)
    position_opened: bool = field(default=False, init=False)
    position_size_approved: bool = field(default=False, init=False)
    future_bars_used: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        try:
            status = PaperPlanStatus(self.paper_status).value
            plan_type = PaperPlanType(self.paper_plan_type).value
            direction = PaperPlanDirection(self.paper_direction).value
        except ValueError as exc:
            raise PaperContractError(str(exc)) from exc
        quality = str(self.plan_quality).upper()
        if quality not in PLAN_QUALITIES:
            raise PaperContractError(f"unsupported plan quality: {quality}")
        if not self.paper_plan_id or not self.symbol or not self.timeframe:
            raise PaperContractError("plan id, symbol and timeframe must not be empty")
        if self.plan_score is not None and not 0 <= float(self.plan_score) <= 100:
            raise PaperContractError("plan_score must be in the 0..100 range")
        if status == PaperPlanStatus.PAPER_PLAN_READY.value:
            levels = (self.hypothetical_entry_reference, self.hypothetical_invalidation_level,
                      self.hypothetical_stop_level, self.hypothetical_target_level, self.planned_rr)
            if any(value is None for value in levels):
                raise PaperContractError("ready paper plans require complete hypothetical levels and RR")
            if quality not in {"GOOD", "ACCEPTABLE"}:
                raise PaperContractError("ready paper plans require GOOD or ACCEPTABLE quality")
            if direction not in {"BULLISH", "BEARISH"}:
                raise PaperContractError("ready paper plans require a directional paper context")
        object.__setattr__(self, "paper_status", status)
        object.__setattr__(self, "paper_plan_type", plan_type)
        object.__setattr__(self, "paper_direction", direction)
        object.__setattr__(self, "plan_quality", quality)
        object.__setattr__(self, "symbol", self.symbol.upper())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
