from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.server_api.errors import ApiError
from app.server_api.mapping import ContractMapper
from app.server_api.mapping.contract import utc_text
from app.server_api.pagination import decode_cursor, encode_cursor
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.records import (
    CursorPosition,
    IncidentQuery,
    IncidentRecord,
    SetupQuery,
    SetupRecord,
)
from app.server_api.schemas.models import (
    AnalysisEnvelope,
    DashboardEnvelope,
    DashboardSnapshot,
    HealthEnvelope,
    IncidentDetailEnvelope,
    IncidentPage,
    IncidentPageEnvelope,
    MarketDetailEnvelope,
    MarketList,
    MarketListEnvelope,
    PageInfo,
    SetupDetailEnvelope,
    SetupPage,
    SetupPageEnvelope,
    TradingUniverseEnvelope,
    TradingUniverseSnapshot,
    TradingUniverseSymbolStatus,
)
from app.trading_universe.domain import PREPARED_NEXT_TRADING_UNIVERSE
from app.server_api.settings import ApiSettings


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | None, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        if not value.endswith("Z"):
            raise ValueError
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except ValueError:
        raise ApiError(
            422,
            "INVALID_REQUEST",
            "The request parameters are invalid.",
            {"field": field},
        ) from None


class ApiQueryService:
    def __init__(
        self,
        repositories: ApiRepositories | None,
        settings: ApiSettings,
        *,
        clock: Callable[[], datetime] = _utc_now,
        mapper: ContractMapper | None = None,
    ) -> None:
        self._repositories = repositories
        self._settings = settings
        self._clock = clock
        self._mapper = mapper or ContractMapper()

    def _repos(self) -> ApiRepositories:
        if self._repositories is None:
            raise ApiError(
                503,
                "SERVICE_NOT_CONFIGURED",
                "The read-only data service is not configured.",
            )
        return self._repositories

    def _generated_at(self) -> str:
        return utc_text(self._clock())

    @staticmethod
    def _range(from_value: str | None, to_value: str | None) -> tuple[datetime | None, datetime | None]:
        from_at = _parse_timestamp(from_value, "from")
        to_at = _parse_timestamp(to_value, "to")
        if from_at is not None and to_at is not None and from_at >= to_at:
            raise ApiError(
                422,
                "INVALID_REQUEST",
                "The request parameters are invalid.",
                {"field": "from"},
            )
        return from_at, to_at

    def health(self) -> HealthEnvelope:
        value = self._repos().health.get_health()
        return HealthEnvelope(generated_at=self._generated_at(), data=self._mapper.health(value))

    def markets(self) -> MarketListEnvelope:
        records = self._repos().markets.list_markets()
        items = sorted((self._mapper.market_summary(item) for item in records), key=lambda item: item.symbol)
        return MarketListEnvelope(generated_at=self._generated_at(), data=MarketList(items=items))

    def trading_universe(self) -> TradingUniverseEnvelope:
        repository = self._repos().universe
        if repository is None:
            raise ApiError(503, "SERVICE_NOT_CONFIGURED", "Trading universe readiness is not configured.")
        records = repository.trading_universe_readiness()
        active_universe = repository.active_trading_universe()
        active = set(active_universe.symbols)
        items = []
        for record in records:
            is_active = record.symbol in active
            items.append(TradingUniverseSymbolStatus(
                symbol=record.symbol,
                universe_version=(active_universe.version_id if is_active else PREPARED_NEXT_TRADING_UNIVERSE.version_id),
                market_data_ready=len(record.ready_timeframes) == 6,
                ready_streams=len(record.ready_timeframes),
                history_ready=record.history_ready,
                analysis_ready=record.analysis_ready,
                setup_ready=record.setup_ready,
                strategy_compatible=record.strategy_compatible,
                risk_compatible=record.risk_compatible,
                trading_activation_state=("ACTIVE" if is_active else "PREPARED_NOT_ACTIVE"),
            ))
        data = TradingUniverseSnapshot(
            active_universe_version=active_universe.version_id,
            prepared_universe_version=PREPARED_NEXT_TRADING_UNIVERSE.version_id,
            active_symbols=list(active_universe.symbols),
            prepared_symbols=list(PREPARED_NEXT_TRADING_UNIVERSE.symbols),
            active_symbol_count=len(active_universe.symbols),
            ready_market_data_streams=sum(item.ready_streams for item in items),
            symbols=items,
        )
        return TradingUniverseEnvelope(generated_at=self._generated_at(), data=data)

    def market(self, symbol: str) -> MarketDetailEnvelope:
        record = self._repos().markets.get_market(symbol)
        if record is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "The requested resource was not found.")
        return MarketDetailEnvelope(generated_at=self._generated_at(), data=self._mapper.market_detail(record))

    def analysis(self, symbol: str) -> AnalysisEnvelope:
        record = self._repos().analysis.get_analysis(symbol)
        if record is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "The requested resource was not found.")
        return AnalysisEnvelope(generated_at=self._generated_at(), data=self._mapper.analysis(record))

    def setups(
        self,
        *,
        limit: int,
        cursor: str | None,
        symbol: str | None,
        status: str | None,
        from_value: str | None,
        to_value: str | None,
    ) -> SetupPageEnvelope:
        from_at, to_at = self._range(from_value, to_value)
        position = decode_cursor(cursor, "setups")
        page = self._repos().setups.list_setups(
            SetupQuery(limit=limit, cursor=position, symbol=symbol, status=status, from_at=from_at, to_at=to_at)
        )
        records = tuple(item for item in page.items if isinstance(item, SetupRecord))
        if len(records) > limit:
            records = records[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor(
                "setups",
                CursorPosition(
                    last.updated_at,
                    last.cursor_identifier or last.setup_id,
                ),
            )
        data = SetupPage(
            items=[self._mapper.setup_summary(item) for item in records],
            page=PageInfo(limit=limit, next_cursor=next_cursor),
        )
        return SetupPageEnvelope(generated_at=self._generated_at(), data=data)

    def setup(self, setup_id: str) -> SetupDetailEnvelope:
        record = self._repos().setups.get_setup(setup_id)
        if record is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "The requested resource was not found.")
        return SetupDetailEnvelope(generated_at=self._generated_at(), data=self._mapper.setup_detail(record))

    def incidents(
        self,
        *,
        limit: int,
        cursor: str | None,
        symbol: str | None,
        status: str | None,
        severity: str | None,
        from_value: str | None,
        to_value: str | None,
    ) -> IncidentPageEnvelope:
        from_at, to_at = self._range(from_value, to_value)
        position = decode_cursor(cursor, "incidents")
        page = self._repos().incidents.list_incidents(
            IncidentQuery(
                limit=limit,
                cursor=position,
                symbol=symbol,
                status=status,
                severity=severity,
                from_at=from_at,
                to_at=to_at,
            )
        )
        records = tuple(item for item in page.items if isinstance(item, IncidentRecord))
        if len(records) > limit:
            records = records[:limit]
        next_cursor = None
        if page.has_more and records:
            last = records[-1]
            next_cursor = encode_cursor("incidents", CursorPosition(last.updated_at, last.incident_id))
        data = IncidentPage(
            items=[self._mapper.incident_summary(item) for item in records],
            page=PageInfo(limit=limit, next_cursor=next_cursor),
        )
        return IncidentPageEnvelope(generated_at=self._generated_at(), data=data)

    def incident(self, incident_id: str) -> IncidentDetailEnvelope:
        record = self._repos().incidents.get_incident(incident_id)
        if record is None:
            raise ApiError(404, "RESOURCE_NOT_FOUND", "The requested resource was not found.")
        return IncidentDetailEnvelope(
            generated_at=self._generated_at(),
            data=self._mapper.incident_detail(record),
        )

    def dashboard(self) -> DashboardEnvelope:
        repos = self._repos()
        health = repos.health.get_health()
        markets = sorted(
            (self._mapper.market_summary(item) for item in repos.markets.list_markets()),
            key=lambda item: item.symbol,
        )
        runs = repos.dashboard.list_recent_runs(self._settings.dashboard_run_limit)
        data = DashboardSnapshot(
            status=self._mapper.health(health).status,
            observed_at=utc_text(health.observed_at),
            markets=markets,
            recent_runs=[self._mapper.run(item) for item in runs],
            active_incident_count=repos.incidents.count_active_incidents(),
        )
        return DashboardEnvelope(generated_at=self._generated_at(), data=data)
