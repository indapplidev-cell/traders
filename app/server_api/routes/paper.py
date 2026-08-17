from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.server_api.schemas.models import ErrorEnvelope
from app.server_api.schemas.paper import (
    PaperAccount, PaperControlStatus, PaperEnvelope, PaperList, PaperPositionDetail,
    PaperPositionItem, PaperReadiness, PaperReconciliation, PaperRuntimeStatus,
    PaperTradeItem, PaperTradeReport, TradingCriteriaSnapshot, PaperOrderItem,
    PaperFillItem, PaperJournalItem,
)
from app.server_api.services.paper_reporting import PaperReadonlyReportingService


SafeIdPath = Annotated[str, Path(pattern=r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")]
SymbolFilter = Annotated[str | None, Query()]


def build_paper_router(service: PaperReadonlyReportingService, generated_at) -> APIRouter:
    router = APIRouter(prefix="/api/v1/paper", tags=["paper-readonly"])
    errors = {409: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}}

    def envelope(data):
        return {"api_version": "v1", "paper_reporting_api_version": 1, "generated_at": generated_at(), "data": data}

    @router.get("/readiness", response_model=PaperEnvelope[PaperReadiness], operation_id="getPaperReadiness", responses=errors)
    def readiness(): return envelope(service.readiness())

    @router.get("/account", response_model=PaperEnvelope[PaperAccount], operation_id="getPaperAccount", responses=errors)
    def account(): return envelope(service.account())

    @router.get("/positions", response_model=PaperEnvelope[PaperList[PaperPositionItem]], operation_id="listPaperPositions", responses=errors)
    def positions(limit: int = 50, cursor: str | None = None,
                  state: str | None = None,
                  symbol: SymbolFilter = None):
        return envelope(service.positions(limit=limit, cursor=cursor, state=state, symbol=symbol))

    @router.get("/positions/{position_id}", response_model=PaperEnvelope[PaperPositionDetail], operation_id="getPaperPosition", responses={404: {"model": ErrorEnvelope}, **errors})
    def position(position_id: SafeIdPath): return envelope(service.position(position_id))

    @router.get("/trades", response_model=PaperEnvelope[PaperList[PaperTradeItem]], operation_id="listPaperTrades", responses=errors)
    def trades(limit: int = 50, cursor: str | None = None,
               symbol: SymbolFilter = None, side: str | None = None,
               exit_reason: str | None = None, from_value: Annotated[str | None, Query(alias="from")] = None,
               to_value: Annotated[str | None, Query(alias="to")] = None):
        return envelope(service.trades(limit=limit, cursor=cursor, symbol=symbol, side=side,
            exit_reason=exit_reason, from_value=from_value, to_value=to_value))

    @router.get("/orders", response_model=PaperEnvelope[PaperList[PaperOrderItem]], operation_id="listPaperOrders", responses=errors)
    def orders(limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None,
               symbol: SymbolFilter = None):
        return envelope(service.orders(limit=limit, cursor=cursor, symbol=symbol))

    @router.get("/fills", response_model=PaperEnvelope[PaperList[PaperFillItem]], operation_id="listPaperFills", responses=errors)
    def fills(limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None,
              symbol: SymbolFilter = None):
        return envelope(service.fills(limit=limit, cursor=cursor, symbol=symbol))

    @router.get("/journal", response_model=PaperEnvelope[PaperList[PaperJournalItem]], operation_id="listPaperJournal", responses=errors)
    def journal(limit: Annotated[int, Query(ge=1, le=100)] = 50, cursor: str | None = None):
        return envelope(service.journal(limit=limit, cursor=cursor))

    @router.get("/trades/{position_id}/report", response_model=PaperEnvelope[PaperTradeReport], operation_id="getPaperTradeReport", responses={404: {"model": ErrorEnvelope}, **errors})
    def report(position_id: SafeIdPath): return envelope(service.trade_report(position_id))

    @router.get("/reconciliation", response_model=PaperEnvelope[PaperReconciliation], operation_id="getPaperReconciliation", responses=errors)
    def reconciliation(): return envelope(service.reconciliation())

    @router.get("/runtime/status", response_model=PaperEnvelope[PaperRuntimeStatus], operation_id="getPaperRuntimeStatus", responses=errors)
    def runtime_status(): return envelope(service.runtime_status())

    @router.get("/control/status", response_model=PaperEnvelope[PaperControlStatus], operation_id="getPaperControlStatus", responses=errors)
    def control_status(): return envelope(service.control_status())

    @router.get("/trading-criteria", response_model=PaperEnvelope[TradingCriteriaSnapshot], operation_id="getPaperTradingCriteria", responses=errors)
    def trading_criteria(): return envelope(service.trading_criteria())

    return router
