from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    closed_until_utc: datetime
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    trigger_source: str = ""
    daemon_instance_id: str = ""
    market_data_freshness_status: str | None = None
    analysis_status: str | None = None
    setup_status: str | None = None
    strategy_status: str | None = None
    risk_status: str | None = None
    paper_status: str | None = None
    final_result: str | None = None
    final_reason: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    future_bars_used: bool = False
    is_trade_signal: bool = False
    is_executable: bool = False
    order_approved: bool = False
    execution_approved: bool = False
    position_opened: bool = False
    position_size_approved: bool = False

    def __post_init__(self) -> None:
        self.closed_until_utc = utc(self.closed_until_utc)  # type: ignore[assignment]
        self.started_at, self.finished_at = utc(self.started_at), utc(self.finished_at)


@dataclass(slots=True)
class ResultRecord:
    run_id: str
    symbol: str
    primary_timeframe: str
    closed_until_ms: int
    market_data_payload_json: Any = field(default_factory=dict)
    analysis_payload_json: Any = field(default_factory=dict)
    setup_payload_json: Any = field(default_factory=dict)
    strategy_payload_json: Any = field(default_factory=dict)
    risk_payload_json: Any = field(default_factory=dict)
    paper_payload_json: Any = field(default_factory=dict)
    module_reasons_json: Any = field(default_factory=dict)
    module_warnings_json: Any = field(default_factory=dict)
    safety_counters_json: Any = field(default_factory=dict)


def jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, datetime):
        return utc(value).isoformat().replace("+00:00", "Z")
    return value
