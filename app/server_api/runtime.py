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
from app.server_api.runtime_config import RuntimeConfig


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
    return ApiRepositories(
        health=adapter,
        markets=adapter,
        analysis=adapter,
        setups=adapter,
        incidents=adapter,
        dashboard=adapter,
    )


def create_runtime_app() -> FastAPI:
    """Compose the production ASGI application without connecting at import."""
    config = RuntimeConfig.from_environment()
    engine = _create_engine(config)
    repositories = _repositories(engine)

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

    app = create_app(repositories=repositories)
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
