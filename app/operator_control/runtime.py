"""Production-only composition root for the loopback Operator Control API."""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from uvicorn import run as run_server

from app.engine_paper.first_canary_correlation import SqlAlchemyPaperFirstCanaryStore
from app.engine_paper.production_preparation_backend import RUNTIME_DATABASE_KEY
from app.engine_safety.paper_production_control import PaperProductionSafetyControl
from app.engine_safety.production_control_root import resolve_production_control_root

from .app import create_paper_operator_control_app
from .auth import PaperOperatorAuthenticator, ProtectedFileOperatorCredentialBinding
from .config import DEFAULT_BIND_HOST, DEFAULT_PORT, PaperOperatorControlConfig
from .service import PaperFirstCanaryStore, PaperOperatorArmReadiness


APPLICATION_NAME = "traders-operator-control-api"
FACTORY_REFERENCE = "app.operator_control.runtime:create_runtime_app"
PROTECTED_TOKEN_PATH = Path("/run/secrets/traders_control_api_token")
RUNTIME_IDENTITY_KEY = "TRADERS_CONTROL_SOURCE_IDENTITY"
CONTAINER_LISTENER_KEY = "TRADERS_CONTROL_CONTAINER_LISTENER"
READONLY_INTERNAL_URL_KEY = "TRADERS_READONLY_API_INTERNAL_URL"
DEFAULT_READONLY_INTERNAL_URL = "http://readonly-api:8765"
RUNTIME_DATABASE_HOST_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_HOST"
RUNTIME_DATABASE_PORT_KEY = "TRADERS_PAPER_RUNTIME_DATABASE_PORT"


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
    require_production_store: bool = True,
) -> FastAPI:
    """Compose the authenticated PAPER mutation boundary without transitioning it."""

    binding = credential_binding or ProtectedFileOperatorCredentialBinding(PROTECTED_TOKEN_PATH)
    capability = binding.load_current()
    engine = None
    if canary_store is None and require_production_store:
        canary_store, engine = _production_canary_store()
    config = PaperOperatorControlConfig.production_paper()
    active_control = control or PaperProductionSafetyControl(
        resolve_production_control_root(),
        # Docker Desktop does not preserve Windows ACL metadata in its
        # Linux view. The production mount is enforced by Compose.
        acl_checker=(lambda _path: True),
    )
    from .service import PaperOperatorControlService
    service = PaperOperatorControlService(
        config=config,
        control=active_control,
        readiness=readiness or ReadonlyPaperArmReadinessSource(
            os.environ.get(READONLY_INTERNAL_URL_KEY, DEFAULT_READONLY_INTERNAL_URL)
        ),
        canary_store=canary_store,
    )
    app = create_paper_operator_control_app(
        config=config,
        authenticator=PaperOperatorAuthenticator((capability,)),
        service=service,
    )
    app.state.runtime_identity = runtime_identity or os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET")
    app.state.credential_binding = binding
    app.state.runtime_engine = engine
    return app


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
