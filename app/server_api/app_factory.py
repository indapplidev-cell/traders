from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fastapi import FastAPI

from app.server_api.errors.handlers import install_error_handlers
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.routes import build_v1_router
from app.server_api.services import ApiQueryService
from app.server_api.settings import ApiSettings


def create_app(
    *,
    repositories: ApiRepositories | None = None,
    settings: ApiSettings | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    """Build an inert ASGI application with explicit read dependencies only."""
    active_settings = settings or ApiSettings()
    service_args = {}
    if clock is not None:
        service_args["clock"] = clock
    service = ApiQueryService(repositories, active_settings, **service_args)
    app = FastAPI(
        title="Traders Read-Only Observability API",
        version="v1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    install_error_handlers(app)
    app.include_router(build_v1_router(service))
    return app
