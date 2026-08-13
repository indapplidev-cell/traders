"""Header-only local capability authentication."""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from pathlib import Path


class PaperOperatorScope(StrEnum):
    CONTROL_STATUS_READ = "paper.control.status.read"
    CANARY_STATUS_READ = "paper.canary.status.read"
    CANARY_ARM = "paper.canary.arm"
    CANARY_START = "paper.canary.start"
    CONTROL_DISABLE = "paper.control.disable"
    CONTROL_EMERGENCY_STOP = "paper.control.emergency_stop"
    CONTROL_CLEAR_EMERGENCY_STOP = "paper.control.clear_emergency_stop"


ALL_OPERATOR_SCOPES = frozenset(PaperOperatorScope)


@dataclass(frozen=True, slots=True)
class PaperOperatorPrincipal:
    scopes: frozenset[PaperOperatorScope]


@dataclass(frozen=True, slots=True)
class PaperOperatorCapability:
    """An in-memory capability used only by explicit composition/tests."""

    secret: bytes
    scopes: frozenset[PaperOperatorScope]

    def __post_init__(self) -> None:
        if not 32 <= len(self.secret) <= 512:
            raise ValueError("INVALID_OPERATOR_CAPABILITY")
        if not self.scopes or not self.scopes <= ALL_OPERATOR_SCOPES:
            raise ValueError("INVALID_OPERATOR_SCOPES")


class PaperOperatorControlCredentialBinding(Protocol):
    """Future OS-protected, restrictive-ACL, rotatable local binding port.

    Implementations must be independent of database credentials and
    ``.env.production.local``.  They must return capability bytes only to the
    authenticator and must never expose their location through the API.
    """

    def load_current(self) -> PaperOperatorCapability: ...

    def rotate(self) -> None: ...


class ProtectedFileOperatorCredentialBinding:
    """Read one capability from a protected runtime file without disclosure."""

    def __init__(self, path: Path) -> None:
        self._path = path.resolve()

    def __repr__(self) -> str:
        return "ProtectedFileOperatorCredentialBinding(protected=True)"

    __str__ = __repr__

    def load_current(self) -> PaperOperatorCapability:
        try:
            secret = self._path.read_bytes().strip()
        except Exception:
            raise OperatorAuthError(503, "CONTROL_CREDENTIAL_UNAVAILABLE") from None
        try:
            return PaperOperatorCapability(secret=secret, scopes=ALL_OPERATOR_SCOPES)
        except ValueError:
            raise OperatorAuthError(503, "CONTROL_CREDENTIAL_INVALID") from None

    def rotate(self) -> None:
        raise OperatorAuthError(503, "CONTROL_CREDENTIAL_ROTATION_REQUIRES_DEPLOYMENT_BOUNDARY")


class OperatorAuthError(RuntimeError):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


class PaperOperatorAuthenticator:
    def __init__(self, capabilities: tuple[PaperOperatorCapability, ...] = ()) -> None:
        self._capabilities = capabilities

    def authenticate(
        self, authorization: str | None, required_scope: PaperOperatorScope
    ) -> PaperOperatorPrincipal:
        if authorization is None:
            raise OperatorAuthError(401, "CONTROL_AUTH_REQUIRED")
        scheme, separator, supplied = authorization.partition(" ")
        if separator != " " or scheme.casefold() != "bearer" or not supplied:
            raise OperatorAuthError(401, "CONTROL_AUTH_INVALID")
        try:
            candidate = supplied.encode("ascii")
        except UnicodeEncodeError as error:
            raise OperatorAuthError(401, "CONTROL_AUTH_INVALID") from error
        if len(candidate) > 512:
            raise OperatorAuthError(401, "CONTROL_AUTH_INVALID")
        matched: PaperOperatorCapability | None = None
        for capability in self._capabilities:
            if hmac.compare_digest(candidate, capability.secret):
                matched = capability
        if matched is None:
            raise OperatorAuthError(401, "CONTROL_AUTH_INVALID")
        if required_scope not in matched.scopes:
            raise OperatorAuthError(403, "CONTROL_FORBIDDEN")
        return PaperOperatorPrincipal(matched.scopes)
