"""Shared parameter-sweep front-end models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RunRequest:
    config_path: Path
    run_id: str
    resume: bool = False
    max_configs: int | None = None
    max_rows: int | None = None
    database_url: str | None = None


@dataclass(frozen=True, slots=True)
class SearchPlanState:
    search_dimensions: tuple[str, ...]
    dimension_values: dict[str, list[Any]]
    conditional_dimensions: tuple[str, ...]
    raw_search_space_size: int
    planned_configs: int
    selected_strategy: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "search_dimensions": list(self.search_dimensions),
            "dimension_values": self.dimension_values,
            "conditional_dimensions": list(self.conditional_dimensions),
            "raw_search_space_size": self.raw_search_space_size,
            "planned_configs": self.planned_configs,
            "selected_strategy": self.selected_strategy,
        }


@dataclass(frozen=True, slots=True)
class ReplayDiagnostics:
    dataset_rows: int
    outcome_replay_rows: int
    time_stop_replay_rows: int
    full_replay_rows: int
    post_instrumentation_rows: int
    missing_market_timeline_rows: int
    missing_cost_timeline_rows: int
    historical_market_rows: int = 0
    opportunity_universe_size: int = 0
    persisted_closed_trades: int = 0
    reconstructed_opportunities: int = 0
    replay_capabilities: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "dataset_rows": self.dataset_rows,
            "outcome_replay_rows": self.outcome_replay_rows,
            "time_stop_replay_rows": self.time_stop_replay_rows,
            "full_replay_rows": self.full_replay_rows,
            "post_instrumentation_rows": self.post_instrumentation_rows,
            "missing_market_timeline_rows": self.missing_market_timeline_rows,
            "missing_cost_timeline_rows": self.missing_cost_timeline_rows,
            "historical_market_rows": self.historical_market_rows,
            "opportunity_universe_size": self.opportunity_universe_size,
            "persisted_closed_trades": self.persisted_closed_trades,
            "reconstructed_opportunities": self.reconstructed_opportunities,
            "replay_capabilities": self.replay_capabilities or {},
        }


@dataclass(frozen=True, slots=True)
class StructuredError:
    error_code: str
    error_title_ru: str
    error_message_ru: str
    error_details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_title_ru": self.error_title_ru,
            "error_message_ru": self.error_message_ru,
            "error_details": self.error_details,
        }
