"""Serializable result and safety contracts for one closed window."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from app.engine_orchestrator.orchestrator_status import FinalResult, PipelineStatus


@dataclass(frozen=True, slots=True)
class SafetyCounters:
    future_bars_used_count: int = 0
    trade_signal_count: int = 0
    is_executable_count: int = 0
    order_approved_count: int = 0
    execution_approved_count: int = 0
    position_opened_count: int = 0
    position_size_approved_count: int = 0
    private_api_used: int = 0
    api_keys_used: int = 0
    synthetic_candles_used: int = 0
    outcome_pnl_used: int = 0

    @property
    def has_violation(self) -> bool:
        return any(asdict(self).values())


def json_safe(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    elif hasattr(value, "to_dict") and callable(value.to_dict):
        value = value.to_dict()
    elif hasattr(value, "__dict__"):
        value = vars(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(slots=True)
class PipelineResult:
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    status: str = PipelineStatus.COMPLETED.value
    final_result: str = FinalResult.NO_DECISION.value
    final_reason: str | None = None
    market_data_payload: dict[str, Any] = field(default_factory=dict)
    analysis_payload: dict[str, Any] = field(default_factory=dict)
    setup_payload: dict[str, Any] = field(default_factory=dict)
    strategy_payload: dict[str, Any] = field(default_factory=dict)
    risk_payload: dict[str, Any] = field(default_factory=dict)
    paper_payload: dict[str, Any] = field(default_factory=dict)
    analysis_status: str | None = None
    setup_status: str | None = None
    strategy_status: str | None = None
    risk_status: str | None = None
    paper_status: str | None = None
    module_reasons: dict[str, Any] = field(default_factory=dict)
    module_warnings: dict[str, Any] = field(default_factory=dict)
    safety_counters: SafetyCounters = field(default_factory=SafetyCounters)
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        PipelineStatus(self.status)
        FinalResult(self.final_result)
