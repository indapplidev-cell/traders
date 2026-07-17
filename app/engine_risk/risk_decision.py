"""Canonical non-executable output model for ENGINE-RISK-01."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Any

from app.engine_risk.risk_errors import RiskContractError
from app.engine_risk.risk_level import RiskLevel
from app.engine_risk.risk_status import RiskStatus


_FORBIDDEN_CONTEXT_KEYS = {
    "entry", "stop", "target", "take_profit", "planned_rr", "rr", "outcome",
    "gross_return", "net_return", "pnl", "fee", "slippage", "position_size", "order_id",
    "account_balance", "margin", "leverage", "liquidation_price",
}


def risk_decision_id(symbol: str, timeframe: str, closed_until_ms: int,
                     source_strategy_decision_id: str | None) -> str:
    identity = f"{symbol.upper()}:{timeframe}:{int(closed_until_ms)}:{source_strategy_decision_id or 'NONE'}"
    return f"risk:{identity}:{sha256(identity.encode()).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class RiskDecision:
    risk_decision_id: str
    created_at_ms: int
    source_strategy_decision_id: str | None
    source_setup_id: str | None
    source_analysis_snapshot_id: str | None
    symbol: str
    timeframe: str
    closed_until_ms: int
    risk_status: str
    risk_level: str
    risk_score: float | None
    risk_policy_version: str
    source_decision_status: str
    source_strategy_type: str
    source_strategy_quality: str
    source_strategy_score: float | None
    direction_hint: str
    risk_reasons: list[str] = field(default_factory=list)
    risk_warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    wait_reasons: list[str] = field(default_factory=list)
    risk_context: dict[str, Any] = field(default_factory=dict)
    risk_pre_approved: bool = False
    requires_execution_review: bool = False
    execution_approved: bool = field(default=False, init=False)
    order_approved: bool = field(default=False, init=False)
    position_size_approved: bool = field(default=False, init=False)
    is_executable: bool = field(default=False, init=False)
    is_trade_signal: bool = field(default=False, init=False)
    future_bars_used: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        try:
            status = RiskStatus(self.risk_status).value
            level = RiskLevel(self.risk_level).value
        except ValueError as exc:
            raise RiskContractError(str(exc)) from exc
        object.__setattr__(self, "risk_status", status)
        object.__setattr__(self, "risk_level", level)
        object.__setattr__(self, "symbol", self.symbol.upper())
        if not self.risk_decision_id or not self.risk_policy_version:
            raise RiskContractError("decision id and policy version must not be empty")
        if self.risk_score is not None and not 0 <= float(self.risk_score) <= 100:
            raise RiskContractError("risk_score must be in the 0..100 range")
        approved = status == RiskStatus.RISK_PRE_APPROVED_RESEARCH.value
        if self.risk_pre_approved != approved or self.requires_execution_review != approved:
            raise RiskContractError("pre-approval and execution review are true only for research pre-approval")
        if approved and level not in {RiskLevel.LOW.value, RiskLevel.MEDIUM.value}:
            raise RiskContractError("research pre-approval requires LOW or MEDIUM policy risk")
        forbidden = _FORBIDDEN_CONTEXT_KEYS.intersection(str(key).lower() for key in self.risk_context)
        if forbidden:
            raise RiskContractError(f"forbidden risk context keys: {sorted(forbidden)}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
