from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.records import (
    AnalysisRecord,
    HealthRecord,
    IncidentQuery,
    IncidentRecord,
    MarketRecord,
    RecordPage,
    RunRecord,
    ServiceRecord,
    SetupQuery,
    SetupRecord,
)


NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


class FakeReadRepository:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.markets = (
            MarketRecord(
                symbol="BTCUSDT",
                status="OK",
                latest_price=Decimal("60123.4500"),
                closed_until_ms=1784894400000,
                regime="TREND",
                setup_status="SETUP_CANDIDATE",
                risk_status="RISK_PRE_APPROVED_RESEARCH",
                updated_at=NOW,
                open=Decimal("60000.10"),
                high=Decimal("60200.20"),
                low=Decimal("59900.30"),
                close=Decimal("60123.4500"),
                volume=Decimal("120.500"),
                has_gaps=False,
                enough_data=True,
            ),
            MarketRecord(
                symbol="ETHUSDT",
                status="MYSTERY_INTERNAL_STATE",
                latest_price=None,
                closed_until_ms=None,
                regime=None,
                setup_status="FUTURE_INTERNAL_STATUS",
                risk_status=None,
                updated_at=NOW,
                has_gaps=None,
                enough_data=None,
            ),
        )
        self.analysis_record = AnalysisRecord(
            analysis_id="analysis:BTCUSDT:15m:1784894400000",
            symbol="BTCUSDT",
            timeframe="15m",
            closed_until_ms=1784894400000,
            status="ANALYZED",
            market_data_status="OK",
            regime="TREND",
            direction="BULLISH",
            confidence=0.75,
            impulse_phase="EXPANSION",
            entry_quality="GOOD",
            reason_codes=("STRUCTURE_ALIGNED",),
            updated_at=NOW,
        )
        self.setup_records = tuple(
            SetupRecord(
                setup_id=f"setup:BTCUSDT:15m:{index}",
                symbol="BTCUSDT",
                timeframe="15m",
                closed_until_ms=1784894400000 - index * 900000,
                status="SETUP_CANDIDATE" if index < 2 else "NO_SETUP",
                setup_type="PULLBACK",
                direction="BULLISH",
                quality="GOOD",
                quality_score=0.8,
                updated_at=NOW.replace(minute=59 - index),
                confirmation_state="CONFIRMED",
                reason_codes=("SETUP_VALID",),
                warnings=(),
                invalidation_reasons=(),
                strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
                risk_status="RISK_PRE_APPROVED_RESEARCH",
                paper_status="PAPER_PLAN_READY",
                hypothetical_entry=Decimal("60100.25"),
                hypothetical_stop=Decimal("59800.00"),
                hypothetical_target=Decimal("60700.75"),
                planned_rr=Decimal("2.00"),
            )
            for index in range(3)
        )
        self.incident_records = (
            IncidentRecord(
                incident_id="incident:001",
                status="OPEN",
                severity="ERROR",
                source="engine_orchestrator",
                title="Pipeline run requires review",
                symbol="BTCUSDT",
                opened_at=NOW.replace(hour=10),
                updated_at=NOW.replace(hour=11),
                safe_description="A persisted pipeline run recorded a non-success state.",
                reason_code="MODULE_ERROR",
                timeframe="15m",
                closed_until_ms=1784894400000,
            ),
            IncidentRecord(
                incident_id="incident:002",
                status="RESOLVED",
                severity="WARNING",
                source="semantic-observer",
                title="Freshness recovered",
                symbol=None,
                opened_at=NOW.replace(hour=8),
                updated_at=NOW.replace(hour=9),
                resolved_at=NOW.replace(hour=9),
                safe_description="A redacted freshness condition recovered.",
            ),
        )

    def api_repositories(self) -> ApiRepositories:
        return ApiRepositories(
            health=self,
            markets=self,
            analysis=self,
            setups=self,
            incidents=self,
            dashboard=self,
        )

    def get_health(self) -> HealthRecord:
        self.calls.append("get_health")
        return HealthRecord(
            "OK",
            NOW,
            (
                ServiceRecord("market-data", "OK", NOW, None),
                ServiceRecord("online-orchestrator", "OK", NOW, "closed-only"),
            ),
            timing_state="CURRENT",
            reason_code="CURRENT",
            operational=True,
            ready=True,
            acceptance_blocking=False,
        )

    def list_markets(self) -> tuple[MarketRecord, ...]:
        self.calls.append("list_markets")
        return tuple(reversed(self.markets))

    def get_market(self, symbol: str) -> MarketRecord | None:
        self.calls.append("get_market")
        return next((item for item in self.markets if item.symbol == symbol), None)

    def get_analysis(self, symbol: str) -> AnalysisRecord | None:
        self.calls.append("get_analysis")
        return self.analysis_record if symbol == "BTCUSDT" else None

    def list_latest_analyses(self, symbols: tuple[str, ...]) -> tuple[AnalysisRecord, ...]:
        self.calls.append("list_latest_analyses")
        return (self.analysis_record,) if "BTCUSDT" in symbols else ()

    @staticmethod
    def _after_cursor(items, cursor, identifier):
        if cursor is None:
            return items
        anchor = (cursor.updated_at, cursor.identifier)
        return [item for item in items if (item.updated_at, getattr(item, identifier)) < anchor]

    def list_setups(self, query: SetupQuery) -> RecordPage:
        self.calls.append("list_setups")
        items = list(self.setup_records)
        if query.symbol:
            items = [item for item in items if item.symbol == query.symbol]
        if query.status:
            items = [item for item in items if item.status == query.status]
        if query.from_at:
            items = [item for item in items if item.updated_at >= query.from_at]
        if query.to_at:
            items = [item for item in items if item.updated_at < query.to_at]
        items.sort(key=lambda item: (item.updated_at, item.setup_id), reverse=True)
        items = self._after_cursor(items, query.cursor, "setup_id")
        selected = items[: query.limit + 1]
        return RecordPage(tuple(selected[: query.limit]), len(selected) > query.limit)

    def get_setup(self, setup_id: str) -> SetupRecord | None:
        self.calls.append("get_setup")
        return next((item for item in self.setup_records if item.setup_id == setup_id), None)

    def list_incidents(self, query: IncidentQuery) -> RecordPage:
        self.calls.append("list_incidents")
        items = list(self.incident_records)
        if query.symbol:
            items = [item for item in items if item.symbol == query.symbol]
        if query.status:
            items = [item for item in items if item.status == query.status]
        if query.severity:
            items = [item for item in items if item.severity == query.severity]
        if query.from_at:
            items = [item for item in items if item.updated_at >= query.from_at]
        if query.to_at:
            items = [item for item in items if item.updated_at < query.to_at]
        items.sort(key=lambda item: (item.updated_at, item.incident_id), reverse=True)
        items = self._after_cursor(items, query.cursor, "incident_id")
        selected = items[: query.limit + 1]
        return RecordPage(tuple(selected[: query.limit]), len(selected) > query.limit)

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        self.calls.append("get_incident")
        return next((item for item in self.incident_records if item.incident_id == incident_id), None)

    def count_active_incidents(self) -> int:
        self.calls.append("count_active_incidents")
        return sum(item.status != "RESOLVED" for item in self.incident_records)

    def list_recent_runs(self, limit: int) -> tuple[RunRecord, ...]:
        self.calls.append("list_recent_runs")
        return (
            RunRecord(
                run_id="orchestrator:001",
                symbol="BTCUSDT",
                primary_timeframe="15m",
                closed_until_ms=1784894400000,
                status="COMPLETED",
                attempt_count=2,
                result_count=1,
            ),
        )[:limit]
