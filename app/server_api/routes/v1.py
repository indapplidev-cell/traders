from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from app.server_api.schemas.models import (
    AnalysisEnvelope,
    AnalysisListEnvelope,
    DashboardEnvelope,
    ErrorEnvelope,
    HealthEnvelope,
    IncidentDetailEnvelope,
    IncidentPageEnvelope,
    MarketDetailEnvelope,
    MarketListEnvelope,
    SetupDetailEnvelope,
    SetupPageEnvelope,
    TradingUniverseEnvelope,
    TradingFunnelEnvelope,
    Severity,
)
from app.server_api.services import ApiQueryService
from app.server_api.schemas.i18n import I18nCatalog, I18nManifest
from app.i18n import catalog_payload, manifest_payload


SymbolPath = Annotated[str, Path(pattern=r"^[A-Z0-9]{5,20}$")]
SafeIdPath = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")]
SymbolFilter = Annotated[str | None, Query(pattern=r"^[A-Z0-9]{5,20}$")]


def build_v1_router(service: ApiQueryService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    error_responses = {
        404: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        500: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
    }

    @router.get("/health", response_model=HealthEnvelope, operation_id="getHealth", responses={500: {"model": ErrorEnvelope}})
    def get_health() -> HealthEnvelope:
        return service.health()

    @router.get("/dashboard", response_model=DashboardEnvelope, operation_id="getDashboard", responses={500: {"model": ErrorEnvelope}})
    def get_dashboard() -> DashboardEnvelope:
        return service.dashboard()

    @router.get(
        "/i18n/manifest", response_model=I18nManifest,
        operation_id="getI18nManifest", responses={500: {"model": ErrorEnvelope}},
    )
    def get_i18n_manifest() -> I18nManifest:
        return I18nManifest.model_validate(manifest_payload())

    @router.get(
        "/i18n/catalog/{locale}", response_model=I18nCatalog,
        operation_id="getI18nCatalog", responses={422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
    )
    def get_i18n_catalog(locale: Literal["ru", "en"]) -> I18nCatalog:
        return I18nCatalog.model_validate(catalog_payload(locale))

    @router.get("/markets", response_model=MarketListEnvelope, operation_id="listMarkets", responses={500: {"model": ErrorEnvelope}})
    def list_markets() -> MarketListEnvelope:
        return service.markets()

    @router.get("/trading-universe", response_model=TradingUniverseEnvelope, operation_id="getTradingUniverse", responses={500: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})
    def get_trading_universe() -> TradingUniverseEnvelope:
        return service.trading_universe()

    @router.get("/trading/funnel", response_model=TradingFunnelEnvelope, operation_id="getTradingFunnel", responses={500: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}})
    def get_trading_funnel(
        trade_profile: Annotated[
            Literal["trade-15m-v1", "trade-5m-v1"], Query()
        ] = "trade-15m-v1",
    ) -> TradingFunnelEnvelope:
        return service.trading_funnel(trade_profile)

    @router.get(
        "/trading/funnel/export", operation_id="exportTradingFunnel",
        responses={422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
    )
    def export_trading_funnel(
        trade_profile_id: Annotated[Literal["trade-15m-v1", "trade-5m-v1"], Query()],
        from_value: Annotated[str, Query(alias="from")],
        to_value: Annotated[str, Query(alias="to")],
        format_name: Annotated[Literal["jsonl", "csv", "summary-json", "summary-md"], Query(alias="format")] = "jsonl",
        symbol: SymbolFilter = None,
        include_candles: Annotated[Literal[False], Query()] = False,
    ) -> Response:
        del include_candles
        body, media_type, extension = service.trading_funnel_export(
            trade_profile_id, from_value, to_value, symbol, format_name,
        )
        return Response(
            content=body, media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="trading-funnel-{trade_profile_id}.{extension}"'},
        )

    @router.get("/markets/{symbol}", response_model=MarketDetailEnvelope, operation_id="getMarket", responses=error_responses)
    def get_market(symbol: SymbolPath) -> MarketDetailEnvelope:
        return service.market(symbol)

    @router.get("/analysis", response_model=AnalysisListEnvelope, operation_id="listLatestAnalysis", responses=error_responses)
    def list_analysis() -> AnalysisListEnvelope:
        return service.analyses()

    @router.get("/analysis/{symbol}", response_model=AnalysisEnvelope, operation_id="getAnalysis", responses=error_responses)
    def get_analysis(symbol: SymbolPath) -> AnalysisEnvelope:
        return service.analysis(symbol)

    @router.get("/setups", response_model=SetupPageEnvelope, operation_id="listSetups", responses=error_responses)
    def list_setups(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
        symbol: SymbolFilter = None,
        status: str | None = None,
        from_value: Annotated[str | None, Query(alias="from")] = None,
        to_value: Annotated[str | None, Query(alias="to")] = None,
    ) -> SetupPageEnvelope:
        return service.setups(
            limit=limit,
            cursor=cursor,
            symbol=symbol,
            status=status,
            from_value=from_value,
            to_value=to_value,
        )

    @router.get("/setups/{setup_id}", response_model=SetupDetailEnvelope, operation_id="getSetup", responses=error_responses)
    def get_setup(setup_id: SafeIdPath) -> SetupDetailEnvelope:
        return service.setup(setup_id)

    @router.get("/incidents", response_model=IncidentPageEnvelope, operation_id="listIncidents", responses=error_responses)
    def list_incidents(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
        symbol: SymbolFilter = None,
        status: str | None = None,
        severity: Severity | None = None,
        from_value: Annotated[str | None, Query(alias="from")] = None,
        to_value: Annotated[str | None, Query(alias="to")] = None,
    ) -> IncidentPageEnvelope:
        return service.incidents(
            limit=limit,
            cursor=cursor,
            symbol=symbol,
            status=status,
            severity=severity.value if severity else None,
            from_value=from_value,
            to_value=to_value,
        )

    @router.get("/incidents/{incident_id}", response_model=IncidentDetailEnvelope, operation_id="getIncident", responses=error_responses)
    def get_incident(incident_id: SafeIdPath) -> IncidentDetailEnvelope:
        return service.incident(incident_id)

    return router
