from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .records import (
    AnalysisRecord,
    HealthRecord,
    IncidentQuery,
    IncidentRecord,
    MarketRecord,
    RecordPage,
    RunRecord,
    SetupQuery,
    SetupRecord,
)


class HealthReadRepository(Protocol):
    def get_health(self) -> HealthRecord: ...


class MarketReadRepository(Protocol):
    def list_markets(self) -> tuple[MarketRecord, ...]: ...
    def get_market(self, symbol: str) -> MarketRecord | None: ...


class AnalysisReadRepository(Protocol):
    def get_analysis(self, symbol: str) -> AnalysisRecord | None: ...


class SetupReadRepository(Protocol):
    def list_setups(self, query: SetupQuery) -> RecordPage: ...
    def get_setup(self, setup_id: str) -> SetupRecord | None: ...


class IncidentReadRepository(Protocol):
    def list_incidents(self, query: IncidentQuery) -> RecordPage: ...
    def get_incident(self, incident_id: str) -> IncidentRecord | None: ...
    def count_active_incidents(self) -> int: ...


class DashboardReadRepository(Protocol):
    def list_recent_runs(self, limit: int) -> tuple[RunRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class ApiRepositories:
    health: HealthReadRepository
    markets: MarketReadRepository
    analysis: AnalysisReadRepository
    setups: SetupReadRepository
    incidents: IncidentReadRepository
    dashboard: DashboardReadRepository
