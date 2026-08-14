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
    PaperPositionQuery,
    PaperPositionRecordView,
    PaperTradeQuery,
    TradingUniverseSymbolReadinessRecord,
)

from app.engine_paper.accounting import PaperAccountBaseline, PaperClosedTradeFacts


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


class TradingUniverseReadRepository(Protocol):
    def trading_universe_readiness(self) -> tuple[TradingUniverseSymbolReadinessRecord, ...]: ...


class PaperReportingReadRepository(Protocol):
    def schema_revision(self) -> str | None: ...
    def list_account_baselines(self, limit: int = 2) -> tuple[PaperAccountBaseline, ...]: ...
    def list_closed_trade_facts(self, limit: int) -> tuple[PaperClosedTradeFacts, ...]: ...
    def list_paper_positions(self, query: PaperPositionQuery) -> RecordPage: ...
    def get_paper_position(self, position_id: str) -> PaperPositionRecordView | None: ...
    def list_paper_trades(self, query: PaperTradeQuery) -> RecordPage: ...


@dataclass(frozen=True, slots=True)
class ApiRepositories:
    health: HealthReadRepository
    markets: MarketReadRepository
    analysis: AnalysisReadRepository
    setups: SetupReadRepository
    incidents: IncidentReadRepository
    dashboard: DashboardReadRepository
    paper: PaperReportingReadRepository | None = None
    universe: TradingUniverseReadRepository | None = None
