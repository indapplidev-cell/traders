"""Safe PostgreSQL connection-failure classification.

Authentication decisions are based on PostgreSQL SQLSTATE, never on rendered
exception text.  The public report intentionally exposes only fixed
classification metadata and exception type names.
"""

from __future__ import annotations

import errno
import re
import socket
import ssl
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterator


INVALID_PASSWORD_SQLSTATE = "28P01"
_SQLSTATE_PATTERN = re.compile(r"^[0-9A-Z]{5}$")


class ConnectionFailureClass(StrEnum):
    CONNECTED = "CONNECTED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TIMEOUT = "TIMEOUT"
    CONNECTION_UNAVAILABLE = "CONNECTION_UNAVAILABLE"
    CONNECTION_SECURITY_ERROR = "CONNECTION_SECURITY_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    UNKNOWN_CONNECTION_FAILURE = "UNKNOWN_CONNECTION_FAILURE"


@dataclass(frozen=True)
class SafeConnectionReport:
    connection: str
    sqlstate: str
    condition: str
    normalized_class: str
    driver_exception_type: str
    wrapper_exception_type: str
    pool_disabled: bool
    retries: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "connection": self.connection,
            "sqlstate": self.sqlstate,
            "condition": self.condition,
            "normalized_class": self.normalized_class,
            "driver_exception_type": self.driver_exception_type,
            "wrapper_exception_type": self.wrapper_exception_type,
            "pool_disabled": "YES" if self.pool_disabled else "NO",
            "retries": self.retries,
        }


def _exception_chain(exception: BaseException) -> Iterator[BaseException]:
    pending: list[BaseException] = [exception]
    visited: set[int] = set()
    while pending:
        current = pending.pop(0)
        identity = id(current)
        if identity in visited:
            continue
        visited.add(identity)
        yield current

        for candidate in (
            getattr(current, "orig", None),
            current.__cause__,
            current.__context__,
        ):
            if isinstance(candidate, BaseException) and id(candidate) not in visited:
                pending.append(candidate)


def _sqlstate_from_exception(exception: BaseException) -> str | None:
    candidates = (
        getattr(exception, "sqlstate", None),
        getattr(exception, "pgcode", None),
        getattr(getattr(exception, "diag", None), "sqlstate", None),
    )
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        normalized = candidate.strip().upper()
        if _SQLSTATE_PATTERN.fullmatch(normalized):
            return normalized
    return None


def extract_postgres_sqlstate(exception: BaseException) -> str | None:
    """Return the first structured SQLSTATE found across known wrappers."""

    for current in _exception_chain(exception):
        sqlstate = _sqlstate_from_exception(current)
        if sqlstate is not None:
            return sqlstate
    return None


def classify_connection_failure(
    exception: BaseException | None,
) -> ConnectionFailureClass:
    if exception is None:
        return ConnectionFailureClass.CONNECTED

    sqlstate = extract_postgres_sqlstate(exception)
    if sqlstate == INVALID_PASSWORD_SQLSTATE:
        return ConnectionFailureClass.AUTHENTICATION_FAILED
    if sqlstate is not None:
        return ConnectionFailureClass.DATABASE_ERROR

    chain = tuple(_exception_chain(exception))
    if any(
        isinstance(current, (TimeoutError, socket.timeout))
        or "timeout" in type(current).__name__.casefold()
        for current in chain
    ):
        return ConnectionFailureClass.TIMEOUT

    unavailable_errno = {
        errno.ECONNREFUSED,
        errno.EHOSTUNREACH,
        errno.ENETUNREACH,
        errno.ENETDOWN,
    }
    if any(
        isinstance(current, (ConnectionRefusedError, socket.gaierror))
        or (
            isinstance(current, OSError)
            and getattr(current, "errno", None) in unavailable_errno
        )
        for current in chain
    ):
        return ConnectionFailureClass.CONNECTION_UNAVAILABLE

    if any(isinstance(current, ssl.SSLError) for current in chain):
        return ConnectionFailureClass.CONNECTION_SECURITY_ERROR

    return ConnectionFailureClass.UNKNOWN_CONNECTION_FAILURE


def is_invalid_password_failure(exception: BaseException) -> bool:
    return (
        classify_connection_failure(exception)
        is ConnectionFailureClass.AUTHENTICATION_FAILED
    )


def _type_name(exception: BaseException) -> str:
    exception_type = type(exception)
    return f"{exception_type.__module__}.{exception_type.__qualname__}"


def build_safe_connection_report(
    exception: BaseException | None,
    *,
    pool_disabled: bool,
    retries: int,
) -> SafeConnectionReport:
    classification = classify_connection_failure(exception)
    if exception is None:
        return SafeConnectionReport(
            connection="CONNECTED",
            sqlstate="NONE",
            condition="none",
            normalized_class=classification.value,
            driver_exception_type="NONE",
            wrapper_exception_type="NONE",
            pool_disabled=pool_disabled,
            retries=retries,
        )

    chain = tuple(_exception_chain(exception))
    driver = next(
        (current for current in chain if _sqlstate_from_exception(current)),
        chain[-1],
    )
    sqlstate = extract_postgres_sqlstate(exception)
    condition = "invalid_password" if sqlstate == INVALID_PASSWORD_SQLSTATE else "none"
    return SafeConnectionReport(
        connection="DENIED",
        sqlstate=sqlstate or "NONE",
        condition=condition,
        normalized_class=classification.value,
        driver_exception_type=_type_name(driver),
        wrapper_exception_type=(
            _type_name(exception) if exception is not driver else "NONE"
        ),
        pool_disabled=pool_disabled,
        retries=retries,
    )


def render_safe_connection_report(report: SafeConnectionReport) -> str:
    """Render only the fixed safe-output contract."""

    return "\n".join(
        f"{key}={value}" for key, value in report.as_dict().items()
    )


__all__ = [
    "ConnectionFailureClass",
    "INVALID_PASSWORD_SQLSTATE",
    "SafeConnectionReport",
    "build_safe_connection_report",
    "classify_connection_failure",
    "extract_postgres_sqlstate",
    "is_invalid_password_failure",
    "render_safe_connection_report",
]
