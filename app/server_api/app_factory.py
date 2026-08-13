from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI

from app.server_api.errors.handlers import install_error_handlers
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.mapping.contract import utc_text
from app.server_api.routes import build_paper_router, build_v1_router
from app.server_api.services import ApiQueryService, PaperReadonlyReportingService, PaperRuntimeObservation
from app.server_api.schemas.paper import PaperControlStatus
from app.server_api.settings import ApiSettings
from app.engine_paper.production_preparation import PaperProductionAccountIdentityBinding


def create_app(
    *,
    repositories: ApiRepositories | None = None,
    settings: ApiSettings | None = None,
    clock: Callable[[], datetime] | None = None,
    paper_runtime: PaperRuntimeObservation | Callable[[], PaperRuntimeObservation] | None = None,
    paper_control_status: Callable[[], PaperControlStatus] | None = None,
    paper_production_identity: PaperProductionAccountIdentityBinding | None = None,
) -> FastAPI:
    """Build an inert ASGI application with explicit read dependencies only."""
    active_settings = settings or ApiSettings()
    service_args = {}
    if clock is not None:
        service_args["clock"] = clock
    service = ApiQueryService(repositories, active_settings, **service_args)
    paper_service = PaperReadonlyReportingService(
        None if repositories is None else repositories.paper,
        runtime=paper_runtime,
        production_identity=paper_production_identity,
        **({"control_status": paper_control_status} if paper_control_status is not None else {}),
    )
    active_clock = clock or (lambda: datetime.now().astimezone())
    app = FastAPI(
        title="Traders Read-Only Observability API",
        version="v1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    install_error_handlers(app)
    app.include_router(build_v1_router(service))
    app.include_router(build_paper_router(paper_service, lambda: utc_text(active_clock())))
    return app
