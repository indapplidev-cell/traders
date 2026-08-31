"""Production-only composition root for the loopback Operator Control API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from uvicorn import run as run_server

from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_paper.command_ingestion_service import PaperCommandIngestionService
from app.engine_paper.production_approval import PaperProductionApprovalSourceAdapter
from app.engine_paper.unit_of_work import PaperUnitOfWork
from app.engine_paper.production_preparation_backend import RUNTIME_DATABASE_KEY
from app.engine_paper.controlled_worker import (
    PaperControlledLifecycleWorker,
    SqlAlchemyPaperLifecycleGraphLoader,
)
from app.engine_paper.production_market_data import PaperProductionMarketDataInputAdapter
from app.engine_safety.paper_production_control import (
    PaperProductionMutationSafetyGate,
    PaperProductionSafetyControl,
)
from app.engine_safety.production_control_root import resolve_production_control_root
from app.trading_universe.activation import SqlAlchemyTradingUniverseStore

from .app import create_paper_operator_control_app
from .auth import PaperOperatorAuthenticator, ProtectedFileOperatorCredentialBinding
from .config import (
    DEFAULT_BIND_HOST,
    DEFAULT_MOBILE_PORT,
    DEFAULT_PORT,
    ControlAuthProfile,
    PaperOperatorControlConfig,
)
from .mobile_security import MobileRequestVerifier, SqlAlchemyMobileSecurityStore
from .service import PaperFirstCanaryExecutor, PaperFirstCanaryStore, PaperOperatorArmReadiness
from .production_executor import ExistingCanaryRuntimeReadiness, ProductionPaperFirstCanaryExecutor
from .continuation_worker import (
    PaperFirstCanaryEligibleApprovalContinuationWorker,
    PostgresCanaryContinuationLock,
    continuation_poll_seconds,
)
from .production_lifecycle_worker import (
    ProductionPaperFirstCanaryLifecycleWorker,
    lifecycle_poll_seconds,
)
from .runtime_health import PaperRuntimeHealthPublisher


APPLICATION_NAME = "traders-operator-control-api"
FACTORY_REFERENCE = "app.operator_control.runtime:create_runtime_app"
PROTECTED_TOKEN_PATH = Path("/run/secrets/traders_control_api_token")
RUNTIME_IDENTITY_KEY = "TRADERS_CONTROL_SOURCE_IDENTITY"
CONTAINER_LISTENER_KEY = "TRADERS_CONTROL_CONTAINER_LISTENER"
READONLY_INTERNAL_URL_KEY = "TRADERS_READONLY_API_INTERNAL_URL"
DEFAULT_READONLY_INTERNAL_URL = "http://readonly-api:8765"
RUNTIME_DATABASE_HOST_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_HOST"
RUNTIME_DATABASE_PORT_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_PORT"
MOBILE_BIND_HOST_KEY = "TRADERS_CONTROL_MOBILE_BIND_HOST"
MOBILE_PORT_KEY = "TRADERS_CONTROL_MOBILE_PORT"
MOBILE_TLS_CERTIFICATE_KEY = "TRADERS_CONTROL_MOBILE_TLS_CERTIFICATE"
MOBILE_TLS_PRIVATE_KEY_KEY = "TRADERS_CONTROL_MOBILE_TLS_PRIVATE_KEY"
MOBILE_TLS_CHAIN_KEY = "TRADERS_CONTROL_MOBILE_TLS_CHAIN"
MOBILE_TLS_SERVER_IDENTITY_KEY = "TRADERS_CONTROL_MOBILE_TLS_SERVER_IDENTITY"


class ReadonlyPaperArmReadinessSource:
    """Fail closed over the already-authoritative Readonly readiness projection."""

    def __init__(self, base_url: str = DEFAULT_READONLY_INTERNAL_URL) -> None:
        self._url = base_url.rstrip("/") + "/api/v1/paper/readiness"

    def __call__(self) -> PaperOperatorArmReadiness:
        try:
            request = urllib.request.Request(self._url, method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                document = json.loads(response.read())
            payload = document.get("data") if isinstance(document, dict) else None
            ready = (
                response.status == 200
                and isinstance(payload, dict)
                and payload.get("status") == "READY"
                and payload.get("current_mutation_ready") is True
                and payload.get("current_mutation_denial_reasons") == []
                and payload.get("paper_control_state") == "DISABLED"
                and payload.get("paper_control_effective_state") == "DISABLED"
                and payload.get("paper_control_health") == "HEALTHY"
            )
        except Exception:
            ready = False
        return PaperOperatorArmReadiness.isolated_ready() if ready else PaperOperatorArmReadiness()


class ReadonlyExistingCanaryRuntimeReadinessSource:
    """Fail closed over current non-control gates for the already-ARMED runtime."""

    def __init__(self, base_url: str = DEFAULT_READONLY_INTERNAL_URL) -> None:
        self._url = base_url.rstrip("/") + "/api/v1/paper/readiness"

    def __call__(self) -> ExistingCanaryRuntimeReadiness:
        try:
            request = urllib.request.Request(self._url, method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                document = json.loads(response.read())
            payload = document.get("data") if isinstance(document, dict) else None
            denials = payload.get("current_mutation_denial_reasons") if isinstance(payload, dict) else None
            common_ready = (
                response.status == 200
                and isinstance(payload, dict)
                and payload.get("status") == "READY"
                and payload.get("paper_schema_ready") is True
                and payload.get("account_baseline_exists") is True
                and payload.get("account_baseline_valid") is True
                and payload.get("accounting_reconciliation_status") == "HEALTHY"
                and payload.get("paper_reconciliation_status") == "HEALTHY"
                and payload.get("paper_runtime_enabled") is True
                and payload.get("paper_control_state") == "ARMED"
                and payload.get("paper_control_effective_state") == "ARMED"
                and payload.get("paper_control_health") == "HEALTHY"
                and payload.get("live_allowed") is False
                and isinstance(denials, list)
                and denials == []
                and payload.get("current_mutation_ready") is True
            )
            if not common_ready:
                return ExistingCanaryRuntimeReadiness(live_disabled=False)
            return ExistingCanaryRuntimeReadiness(
                market_data_ready=payload.get("market_data_adapter_ready") is True,
                approval_source_ready=payload.get("approval_source_adapter_ready") is True,
                wal_ready=payload.get("wal_ready") is True,
                pitr_ready=payload.get("pitr_ready") is True,
                live_disabled=True,
            )
        except Exception:
            return ExistingCanaryRuntimeReadiness(live_disabled=False)


def _production_canary_store() -> tuple[SqlAlchemyPaperFirstCanaryStore, Engine]:
    database_url = os.environ.get(RUNTIME_DATABASE_KEY)
    if not database_url:
        raise RuntimeError("CONTROL_RUNTIME_DATABASE_BINDING_UNAVAILABLE")
    target_host = os.environ.get(RUNTIME_DATABASE_HOST_KEY)
    target_port = os.environ.get(RUNTIME_DATABASE_PORT_KEY)
    try:
        url = make_url(database_url)
        if target_host is not None or target_port is not None:
            if (
                url.host not in {"127.0.0.1", "localhost"}
                or url.port != 5433
                or target_host != "postgres"
                or target_port != "5432"
            ):
                raise ValueError
            url = url.set(host=target_host, port=int(target_port))
    except Exception:
        raise RuntimeError("CONTROL_RUNTIME_DATABASE_BINDING_INVALID") from None
    engine = create_engine(url, hide_parameters=True, pool_pre_ping=True)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SqlAlchemyPaperFirstCanaryStore(sessions), engine


def create_runtime_app(
    *,
    credential_binding: ProtectedFileOperatorCredentialBinding | None = None,
    control: PaperProductionSafetyControl | None = None,
    runtime_identity: str | None = None,
    readiness: Callable[[], PaperOperatorArmReadiness] | None = None,
    canary_store: PaperFirstCanaryStore | None = None,
    executor: PaperFirstCanaryExecutor | None = None,
    require_production_store: bool = True,
    config: PaperOperatorControlConfig | None = None,
    mobile_verifier: MobileRequestVerifier | None = None,
) -> FastAPI:
    """Compose the authenticated PAPER mutation boundary without transitioning it."""

    active_config = config or PaperOperatorControlConfig.production_paper()
    binding = credential_binding or ProtectedFileOperatorCredentialBinding(PROTECTED_TOKEN_PATH)
    capability = (
        binding.load_current()
        if active_config.auth_profile is ControlAuthProfile.OPERATOR_LOOPBACK_BEARER
        else None
    )
    engine = None
    sessions = None
    if canary_store is None and require_production_store:
        canary_store, engine = _production_canary_store()
        sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    active_control = control or PaperProductionSafetyControl(
        resolve_production_control_root(),
        # Docker Desktop does not preserve Windows ACL metadata in its
        # Linux view. The production mount is enforced by Compose.
        acl_checker=(lambda _path: True),
    )
    if executor is None and require_production_store:
        if sessions is None or not isinstance(canary_store, SqlAlchemyPaperFirstCanaryStore):
            raise RuntimeError("CONTROL_RUNTIME_EXECUTOR_COMPOSITION_UNAVAILABLE")
        executor = ProductionPaperFirstCanaryExecutor(
            control=active_control,
            canary_store=canary_store,
            approval_source=PaperProductionApprovalSourceAdapter(sessions),
            ingestion_service=PaperCommandIngestionService(
                lambda: PaperUnitOfWork(sessions), sessions
            ),
            mutation_safety_gate=PaperProductionMutationSafetyGate(active_control),
            runtime_readiness=ReadonlyExistingCanaryRuntimeReadinessSource(
                os.environ.get(READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL)
            ),
        )
    continuation_worker = None
    lifecycle_worker = None
    runtime_health_publisher = None
    universe_store = SqlAlchemyTradingUniverseStore(sessions) if sessions is not None else None
    if (
        require_production_store
        and engine is not None
        and isinstance(canary_store, SqlAlchemyPaperFirstCanaryStore)
        and isinstance(executor, ProductionPaperFirstCanaryExecutor)
    ):
        continuation_worker = PaperFirstCanaryEligibleApprovalContinuationWorker(
            control=active_control,
            canary_store=canary_store,
            executor=executor,
            lock=PostgresCanaryContinuationLock(engine),
            poll_seconds=continuation_poll_seconds(),
        )
        lifecycle_worker = ProductionPaperFirstCanaryLifecycleWorker(
            control=active_control,
            canary_store=canary_store,
            graph_loader=SqlAlchemyPaperLifecycleGraphLoader(
                lambda: PaperUnitOfWork(sessions)
            ),
            lifecycle_worker=PaperControlledLifecycleWorker.from_factories(
                lambda: PaperUnitOfWork(sessions), sessions
            ),
            market_data=PaperProductionMarketDataInputAdapter(sessions),
            mutation_safety_gate=PaperProductionMutationSafetyGate(active_control),
            runtime_readiness=ReadonlyExistingCanaryRuntimeReadinessSource(
                os.environ.get(READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL)
            ),
            lock=PostgresCanaryContinuationLock(engine),
            readonly_base_url=os.environ.get(
                READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL
            ),
            poll_seconds=lifecycle_poll_seconds(),
        )
        runtime_health_publisher = PaperRuntimeHealthPublisher(
            resolve_production_control_root(),
            approval_loop=continuation_worker,
            lifecycle_loop=lifecycle_worker,
            mutation_enabled=active_config.mutation_foundation_enabled,
        )

    from .service import PaperOperatorControlService
    service = PaperOperatorControlService(
        config=active_config,
        control=active_control,
        readiness=readiness or ReadonlyPaperArmReadinessSource(
            os.environ.get(READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL)
        ),
        canary_store=canary_store,
        executor=executor,
        continuation_status=(
            (lambda: (continuation_worker.active, continuation_worker.poll_seconds))
            if continuation_worker is not None else None
        ),
        active_universe=(universe_store.active_universe if universe_store is not None else None),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if continuation_worker is not None:
            continuation_worker.start()
        if lifecycle_worker is not None:
            lifecycle_worker.start()
        if runtime_health_publisher is not None:
            runtime_health_publisher.start()
        try:
            yield
        finally:
            if runtime_health_publisher is not None:
                runtime_health_publisher.stop()
            if lifecycle_worker is not None:
                lifecycle_worker.stop()
            if continuation_worker is not None:
                continuation_worker.stop()
            if engine is not None and hasattr(engine, "dispose"):
                engine.dispose()

    app = create_paper_operator_control_app(
        config=active_config,
        authenticator=PaperOperatorAuthenticator((capability,)) if capability is not None else None,
        mobile_verifier=(
            mobile_verifier
            or (MobileRequestVerifier(SqlAlchemyMobileSecurityStore(sessions)) if sessions is not None else None)
        ),
        service=service,
        lifespan=lifespan,
    )
    app.state.runtime_identity = runtime_identity or os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET")
    app.state.credential_binding = binding
    app.state.runtime_engine = engine
    app.state.first_canary_executor = service.executor
    app.state.first_canary_continuation_worker = continuation_worker
    app.state.first_canary_lifecycle_worker = lifecycle_worker
    app.state.paper_runtime_health_publisher = runtime_health_publisher
    app.state.trading_universe_store = universe_store
    return app


def mobile_runtime_config_from_environment() -> PaperOperatorControlConfig:
    try:
        host = os.environ[MOBILE_BIND_HOST_KEY]
        certificate = Path(os.environ[MOBILE_TLS_CERTIFICATE_KEY])
        private_key = Path(os.environ[MOBILE_TLS_PRIVATE_KEY_KEY])
        identity = os.environ[MOBILE_TLS_SERVER_IDENTITY_KEY]
        port = int(os.environ.get(MOBILE_PORT_KEY, str(DEFAULT_MOBILE_PORT)))
        chain_value = os.environ.get(MOBILE_TLS_CHAIN_KEY)
    except (KeyError, ValueError):
        raise RuntimeError("MOBILE_TLS_REQUIRED") from None
    if not certificate.is_file() or not private_key.is_file():
        raise RuntimeError("MOBILE_TLS_REQUIRED")
    chain = Path(chain_value) if chain_value else None
    if chain is not None and not chain.is_file():
        raise RuntimeError("MOBILE_TLS_REQUIRED")
    return PaperOperatorControlConfig.mobile_device_signed_tls(
        bind_host=host,
        port=port,
        tls_certificate_path=certificate,
        tls_private_key_path=private_key,
        tls_chain_path=chain,
        tls_server_identity=identity,
    )


def create_mobile_runtime_app() -> FastAPI:
    """Factory for the future, separately deployed TLS mobile instance."""
    return create_runtime_app(config=mobile_runtime_config_from_environment())


def mobile_main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    config = mobile_runtime_config_from_environment()
    run_server(
        "app.operator_control.runtime:create_mobile_runtime_app",
        factory=True,
        host=config.bind_host,
        port=config.port,
        ssl_certfile=str(config.tls_certificate_path),
        ssl_keyfile=str(config.tls_private_key_path),
        log_level="info",
        access_log=False,
        reload=False,
        workers=1,
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog=APPLICATION_NAME,
        description="Run only the localhost PAPER Operator Control API.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    _parser().parse_args(argv)
    run_server(
        FACTORY_REFERENCE,
        factory=True,
        host=("0.0.0.0" if os.environ.get(CONTAINER_LISTENER_KEY) == "1" else DEFAULT_BIND_HOST),
        port=DEFAULT_PORT,
        log_level="info",
        access_log=False,
        reload=False,
        workers=1,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
