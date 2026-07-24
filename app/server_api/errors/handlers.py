from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHttpException

from app.server_api.errors.api_errors import ApiError
from app.server_api.schemas.models import Error, ErrorEnvelope


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else f"req-{uuid4().hex}"


def _response(request: Request, status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=Error(code=code, message=message, details=details or {}),
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(envelope))


def install_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def assign_request_id(request: Request, call_next):
        request.state.request_id = f"req-{uuid4().hex}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _response(request, exc.status_code, exc.code, exc.safe_message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(part) for part in error.get("loc", ())[1:]) for error in exc.errors()})
        return _response(
            request,
            422,
            "INVALID_REQUEST",
            "The request parameters are invalid.",
            {"fields": fields},
        )

    @app.exception_handler(StarletteHttpException)
    async def http_error(request: Request, exc: StarletteHttpException) -> JSONResponse:
        if exc.status_code == 404:
            return _response(request, 404, "RESOURCE_NOT_FOUND", "The requested resource was not found.")
        return _response(request, exc.status_code, "INVALID_REQUEST", "The request could not be processed.")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return _response(request, 500, "INTERNAL_ERROR", "An internal service error occurred.")
