"""Production-only composition root for the loopback Operator Control API."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI
from uvicorn import run as run_server

from app.engine_safety.paper_production_control import PaperProductionSafetyControl

from .app import create_paper_operator_control_app
from .auth import PaperOperatorAuthenticator, ProtectedFileOperatorCredentialBinding
from .config import DEFAULT_BIND_HOST, DEFAULT_PORT, PaperOperatorControlConfig


APPLICATION_NAME = "traders-operator-control-api"
FACTORY_REFERENCE = "app.operator_control.runtime:create_runtime_app"
PROTECTED_TOKEN_PATH = Path("/run/secrets/traders_control_api_token")
PRODUCTION_CONTROL_ROOT = Path("/run/traders-control")
RUNTIME_IDENTITY_KEY = "TRADERS_CONTROL_SOURCE_IDENTITY"
CONTAINER_LISTENER_KEY = "TRADERS_CONTROL_CONTAINER_LISTENER"


def create_runtime_app(
    *,
    credential_binding: ProtectedFileOperatorCredentialBinding | None = None,
    control: PaperProductionSafetyControl | None = None,
    runtime_identity: str | None = None,
) -> FastAPI:
    """Compose only the disabled PAPER control surface; import has no I/O."""

    binding = credential_binding or ProtectedFileOperatorCredentialBinding(PROTECTED_TOKEN_PATH)
    capability = binding.load_current()
    app = create_paper_operator_control_app(
        config=PaperOperatorControlConfig(),
        authenticator=PaperOperatorAuthenticator((capability,)),
        control=control or PaperProductionSafetyControl(
            PRODUCTION_CONTROL_ROOT,
            # Docker Desktop does not preserve Windows ACL metadata in its
            # Linux view. The production mount is enforced read-only.
            acl_checker=(lambda _path: True),
        ),
    )
    app.state.runtime_identity = runtime_identity or os.environ.get(RUNTIME_IDENTITY_KEY, "UNSET")
    app.state.credential_binding = binding
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
