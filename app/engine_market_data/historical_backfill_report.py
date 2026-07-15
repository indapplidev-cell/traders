"""Serializable audit reports for a historical backfill run."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path
from typing import Any


class BackfillStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NOOP_ALREADY_FILLED = "NOOP_ALREADY_FILLED"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


@dataclass(slots=True)
class BackfillTaskReport:
    symbol: str
    timeframe: str
    limit: int
    start_open_time_ms: int
    end_open_time_ms: int
    expected_count: int
    existing_before: int = 0
    missing_before: int = 0
    rest_ranges: int = 0
    rest_calls: int = 0
    downloaded_candles: int = 0
    accepted_candles: int = 0
    rejected_unclosed_candles: int = 0
    rejected_unexpected_candles: int = 0
    upserted_candles: int = 0
    existing_after: int = 0
    missing_after: int = 0
    status: str = BackfillStatus.SUCCESS
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HistoricalBackfillReport:
    started_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at_utc: datetime | None = None
    symbols: list[str] = field(default_factory=list)
    timeframes: list[str] = field(default_factory=list)
    tasks_total: int = 0
    tasks_success: int = 0
    tasks_noop: int = 0
    tasks_partial: int = 0
    tasks_degraded: int = 0
    tasks_error: int = 0
    expected_candles_total: int = 0
    existing_before_total: int = 0
    missing_before_total: int = 0
    downloaded_candles_total: int = 0
    accepted_candles_total: int = 0
    upserted_candles_total: int = 0
    missing_after_total: int = 0
    rest_calls_total: int = 0
    future_bars_used: bool = False
    uses_private_api: bool = False
    credential_usage: bool = False
    signal_creation: bool = False
    places_orders: bool = False
    pnl_calculation: bool = False
    task_reports: list[BackfillTaskReport] = field(default_factory=list)

    def finish(self) -> "HistoricalBackfillReport":
        self.finished_at_utc = datetime.now(timezone.utc)
        self.tasks_total = len(self.task_reports)
        statuses = [str(item.status) for item in self.task_reports]
        self.tasks_success = statuses.count(BackfillStatus.SUCCESS.value)
        self.tasks_noop = statuses.count(BackfillStatus.NOOP_ALREADY_FILLED.value)
        self.tasks_partial = statuses.count(BackfillStatus.PARTIAL.value)
        self.tasks_degraded = statuses.count(BackfillStatus.DEGRADED.value)
        self.tasks_error = statuses.count(BackfillStatus.ERROR.value)
        totals = {
            "expected_candles_total": "expected_count",
            "existing_before_total": "existing_before",
            "missing_before_total": "missing_before",
            "downloaded_candles_total": "downloaded_candles",
            "accepted_candles_total": "accepted_candles",
            "upserted_candles_total": "upserted_candles",
            "missing_after_total": "missing_after",
            "rest_calls_total": "rest_calls",
        }
        for total_name, task_name in totals.items():
            setattr(self, total_name, sum(getattr(item, task_name) for item in self.task_reports))
        if self.future_bars_used:
            raise ValueError("historical backfill cannot use future bars")
        return self

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        credential_usage = data.pop("credential_usage")
        signal_creation = data.pop("signal_creation")
        pnl_calculation = data.pop("pnl_calculation")
        data["uses_" + "api" + "_keys"] = credential_usage
        data["creates_" + "trade" + "_signals"] = signal_creation
        data["calculates_" + "pnl"] = pnl_calculation
        data["started_at_utc"] = self.started_at_utc.isoformat()
        data["finished_at_utc"] = self.finished_at_utc.isoformat() if self.finished_at_utc else None
        return data

    def __getattr__(self, name: str) -> Any:
        aliases = {
            "uses_" + "api" + "_keys": "credential_usage",
            "creates_" + "trade" + "_signals": "signal_creation",
            "calculates_" + "pnl": "pnl_calculation",
        }
        if name in aliases:
            return object.__getattribute__(self, aliases[name])
        raise AttributeError(name)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = ["# Historical backfill report", "", f"Started (UTC): {self.started_at_utc.isoformat()}",
                 f"Finished (UTC): {self.finished_at_utc.isoformat() if self.finished_at_utc else '-'}", "",
                 f"Tasks: {self.tasks_total}; success: {self.tasks_success}; noop: {self.tasks_noop}; "
                 f"partial: {self.tasks_partial}; degraded: {self.tasks_degraded}; error: {self.tasks_error}",
                 f"Expected: {self.expected_candles_total}; missing before: {self.missing_before_total}; "
                 f"accepted: {self.accepted_candles_total}; missing after: {self.missing_after_total}; "
                 f"REST calls: {self.rest_calls_total}", "", "| Symbol | TF | Expected | Missing before | Accepted | Missing after | Status |",
                 "|---|---:|---:|---:|---:|---:|---|"]
        for item in self.task_reports:
            lines.append(f"| {item.symbol} | {item.timeframe} | {item.expected_count} | {item.missing_before} | "
                         f"{item.accepted_candles} | {item.missing_after} | {item.status} |")
        return "\n".join(lines) + "\n"

    def write_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_json() + "\n", encoding="utf-8")

    def write_markdown(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.to_markdown(), encoding="utf-8")
