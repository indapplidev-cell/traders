from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
import hashlib
import logging
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.engine_safety.paper_production_control import PaperProductionSafetyControl

from .auth import OperatorAuthError, PaperOperatorAuthenticator, PaperOperatorScope
from .config import ControlAuthProfile, PaperOperatorControlConfig
from .mobile_security import MobileRequestVerifier
from .routes import build_operator_control_router
from .schemas import ControlErrorEnvelope, ControlErrorItem
from .service import ControlApiError, ControlDecisionError, PaperOperatorControlService


TRADING_DECISION_FIELDS = frozenset({
    "side", "direction", "buy", "sell", "long", "short", "quantity", "entry_price",
    "price", "stop", "stop_loss", "target", "take_profit", "leverage", "risk_override",
    "approval", "approval_override", "final_approval_override",
})
QUERY_CREDENTIAL_FIELDS = frozenset({"token", "access_token", "credential", "authorization", "api_key"})
SECURITY_AUDIT_LOG = logging.getLogger("traders.control.mobile.security")


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", ())}
        raw_length = headers.get(b"content-length")
        if raw_length is not None:
            try:
                if int(raw_length) > self.limit:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send)
                return
        consumed = 0

        async def limited_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.limit:
                    raise _BodyTooLarge
            return message
        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLarge:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = b'{"error":{"code":"INVALID_REQUEST","message":"The request body is too large.","details":{}},"request_id":"unassigned"}'
        await send({"type": "http.response.start", "status": 413, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]})
        await send({"type": "http.response.body", "body": body})


class _BodyTooLarge(Exception):
    pass


def create_paper_operator_control_app(
    *,
    config: PaperOperatorControlConfig | None = None,
    authenticator: PaperOperatorAuthenticator | None = None,
    mobile_verifier: MobileRequestVerifier | None = None,
    service: PaperOperatorControlService | None = None,
    control: PaperProductionSafetyControl | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    active_config = config or PaperOperatorControlConfig()
    active_authenticator = authenticator or PaperOperatorAuthenticator()
    if (
        active_config.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS
        and mobile_verifier is None
    ):
        raise ValueError("CONTROL_MOBILE_PERSISTENCE_REQUIRED")
    active_service = service or PaperOperatorControlService(
        config=active_config,
        control=control or PaperProductionSafetyControl(),
    )
    app = FastAPI(
        title="TRADERS PAPER Operator Control API",
        version="1",
        docs_url="/docs" if active_config.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if active_config.docs_enabled else None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def browser_and_query_guard(request: Request, call_next):
        request.state.request_id = f"req-{uuid4().hex}"
        if request.headers.get("origin") is not None:
            return _error_response(request, 403, "CONTROL_FORBIDDEN", "Browser-origin control requests are forbidden.")
        if any(key.casefold() in QUERY_CREDENTIAL_FIELDS for key in request.query_params.keys()):
            return _error_response(request, 400, "INVALID_REQUEST", "Credentials are not accepted in the URL.")
        response = await call_next(request)
        principal = getattr(request.state, "control_principal", None)
        if active_config.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS and principal is not None:
            SECURITY_AUDIT_LOG.info(
                "mobile_control_request device_id=%s key_version=%s fingerprint=%s "
                "action=%s request_id=%s generation=%s nonce_fingerprint=%s status=%s",
                principal.device_id,
                principal.key_version,
                principal.public_key_fingerprint,
                principal.action,
                principal.request_id,
                principal.expected_generation,
                principal.nonce_fingerprint,
                response.status_code,
            )
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def require_scope(scope: PaperOperatorScope, action: str, mutation: bool):
        async def dependency(request: Request) -> None:
            if active_config.auth_profile is ControlAuthProfile.OPERATOR_LOOPBACK_BEARER:
                request.state.control_principal = active_authenticator.authenticate(
                    request.headers.get("authorization"), scope
                )
                return
            if active_config.auth_profile is not ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS:
                raise OperatorAuthError(401, "MOBILE_AUTH_PROFILE_INVALID")
            if mobile_verifier is None:
                raise OperatorAuthError(503, "MOBILE_AUTH_PROFILE_INVALID")
            request.state.control_principal = await mobile_verifier.authenticate(
                request, expected_action=action, mutation=mutation
            )
        return dependency

    @app.exception_handler(OperatorAuthError)
    async def auth_error(request: Request, exc: OperatorAuthError) -> JSONResponse:
        if active_config.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS:
            nonce = request.headers.get("x-traders-nonce", "")[:128]
            SECURITY_AUDIT_LOG.warning(
                "mobile_control_rejected device_id=%s key_version=%s action=%s "
                "request_id=%s nonce_fingerprint=%s result=%s",
                request.headers.get("x-traders-device-id", "")[:64],
                request.headers.get("x-traders-key-version", "")[:16],
                request.headers.get("x-traders-action", "")[:48],
                request.headers.get("x-traders-request-id", "")[:128],
                hashlib.sha256(nonce.encode("utf-8")).hexdigest()[:16] if nonce else "",
                exc.code,
            )
        return _error_response(request, exc.status_code, exc.code, "Operator authentication was denied.")

    @app.exception_handler(ControlDecisionError)
    async def decision_error(request: Request, exc: ControlDecisionError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(exc.decision))

    @app.exception_handler(ControlApiError)
    async def control_error(request: Request, exc: ControlApiError) -> JSONResponse:
        code = (
            "MOBILE_GENERATION_MISMATCH"
            if active_config.auth_profile is ControlAuthProfile.MOBILE_DEVICE_SIGNED_TLS
            and exc.code == "STALE_GENERATION"
            else exc.code
        )
        return _error_response(request, exc.status_code, code, exc.safe_message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = {
            str(error.get("loc", ("", ""))[-1]).casefold()
            for error in exc.errors()
        }
        code = "CLIENT_TRADING_DECISION_NOT_ALLOWED" if fields & TRADING_DECISION_FIELDS else "INVALID_REQUEST"
        return _error_response(request, 400, code, "The control request is invalid.")

    @app.exception_handler(Exception)
    async def safe_failure(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(request, 503, "CONTROL_SAFE_FAILURE", "The control subsystem failed closed.")

    # Materialize the already-composed narrow router.  FastAPI 0.116 defers
    # include_router() behind an internal placeholder; direct materialization
    # keeps the exact eight-route inventory inspectable before startup.
    app.router.routes.extend(
        build_operator_control_router(active_service, require_scope).routes
    )
    app.add_middleware(RequestBodyLimitMiddleware, limit=active_config.max_request_body_bytes)
    app.state.operator_control_config = active_config
    app.state.operator_control_service = active_service
    return app


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unassigned")
    body = ControlErrorEnvelope(error=ControlErrorItem(code=code, message=message), request_id=request_id)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))
