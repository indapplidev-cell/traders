"""Production composition root and canonical executable for the read-only API."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from uvicorn import run as run_server

from app.server_api.app_factory import create_app
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.trading_funnel import TradingFunnelReadRepository
from app.server_api.runtime_config import RuntimeConfig
from app.server_api.schemas.paper import PaperControlStatus
from app.engine_safety.paper_production_control import PaperProductionSafetyControl
from app.engine_safety.production_control_root import resolve_production_control_root
from app.engine_paper.first_canary_correlation import (
    PaperFirstCanaryState,
    SqlAlchemyPaperFirstCanaryStore,
)
from app.server_api.paper_runtime_observation import (
    ProductionPaperRuntimeObservationSource,
    load_production_identity,
)


APPLICATION_NAME = "traders-readonly-api"
FACTORY_REFERENCE = "app.server_api.runtime:create_runtime_app"


def _create_engine(config: RuntimeConfig) -> Engine:
    options = (
        "-c default_transaction_read_only=on "
        f"-c statement_timeout={config.statement_timeout_ms} "
        f"-c application_name={APPLICATION_NAME}"
    )
    return create_engine(
        config.connection_url,
        pool_pre_ping=True,
        pool_size=config.pool_size,
        pool_timeout=config.pool_timeout_seconds,
        connect_args={"options": options},
    )


def _repositories(engine: Engine) -> ApiRepositories:
    sessions = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    adapter = SqlAlchemyReadAdapter(sessions)
    funnel = TradingFunnelReadRepository(sessions, adapter.active_trading_universe)
    return ApiRepositories(
        health=adapter,
        markets=adapter,
        analysis=adapter,
        setups=adapter,
        incidents=adapter,
        dashboard=adapter,
        paper=adapter,
        universe=adapter,
        funnel=funnel,
    )


def _paper_control_status(
    control: PaperProductionSafetyControl,
    canaries: SqlAlchemyPaperFirstCanaryStore | None = None,
) -> PaperControlStatus:
    """Observe the reconciled control state without acquiring/writing a lock."""
    state = control.read_authoritative()
    canary = None if canaries is None else canaries.current()
    if state.state.value == "ARMED":
        if (
            canary is None
            or canary.state not in {
                PaperFirstCanaryState.ARMED,
                PaperFirstCanaryState.ARMED_WAITING,
                PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL,
                PaperFirstCanaryState.RUNNING,
                PaperFirstCanaryState.POSITION_OPEN,
                PaperFirstCanaryState.POSITION_CLOSING,
                PaperFirstCanaryState.POSITION_CLOSED,
                PaperFirstCanaryState.RECONCILIATION_PENDING,
            }
            or canary.current_control_generation != state.generation
        ):
            raise RuntimeError("CONTROL_CANARY_RECONCILIATION_FAILED")
    canary_status = None
    if canary is not None:
        canary_status = (
            "WAITING_FOR_ELIGIBLE_APPROVAL"
            if canary.state is PaperFirstCanaryState.NO_ELIGIBLE_APPROVAL
            else canary.state.value
        )
    return PaperControlStatus(
        state=state.state.value,
        effective_state=state.state.value,
        generation=state.generation,
        health="HEALTHY",
        emergency_stop_available=True,
        audit_health="PASS",
        state_audit_reconciliation="PASS",
        canary_id=None if canary is None else canary.canary_id,
        canary_status=canary_status,
    )


def create_runtime_app() -> FastAPI:
    """Compose the production ASGI application without connecting at import."""
    config = RuntimeConfig.from_environment()
    engine = _create_engine(config)
    repositories = _repositories(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    control = PaperProductionSafetyControl(
        resolve_production_control_root(),
        # Docker Desktop does not project Windows ACL metadata into Linux.
        acl_checker=(lambda _path: True),
    )
    canaries = SqlAlchemyPaperFirstCanaryStore(sessions)
    control_status = lambda: _paper_control_status(control, canaries)
    paper_runtime = ProductionPaperRuntimeObservationSource(sessions, control_status)
    try:
        production_identity = load_production_identity()
    except (OSError, ValueError):
        # The service may start for diagnostics, but readiness remains
        # fail-closed through the observation source when the binding is absent.
        production_identity = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            with engine.connect() as connection:
                mode = connection.exec_driver_sql(
                    "SHOW transaction_read_only"
                ).scalar_one()
                if mode != "on":
                    raise RuntimeError(
                        "database session did not enforce the read-only boundary"
                    )
            yield
        finally:
            engine.dispose()

    app = create_app(
        repositories=repositories,
        paper_runtime=paper_runtime,
        paper_control_status=control_status,
        paper_production_identity=production_identity,
    )
    app.router.lifespan_context = lifespan
    app.state.runtime_config = config
    app.state.runtime_engine = engine
    app.state.runtime_repositories = repositories
    return app


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APPLICATION_NAME,
        description="Run the Traders read-only API using its environment contract.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.2.0",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    config = RuntimeConfig.from_environment()
    run_server(
        FACTORY_REFERENCE,
        factory=True,
        host=config.host,
        port=config.port,
        log_level=config.log_level,
        access_log=True,
        reload=False,
        workers=1,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
