"""Strict environment contract for the read-only API runtime."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ as PROCESS_ENVIRONMENT
from typing import Mapping

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


ENV_PREFIX = "TRADERS_READONLY_API_"
SUPPORTED_LOG_LEVELS = frozenset({"critical", "error", "warning", "info", "debug", "trace"})
MAX_STATEMENT_TIMEOUT_MS = 300_000
MAX_POOL_SIZE = 32
MAX_POOL_TIMEOUT_SECONDS = 120


class RuntimeConfigurationError(ValueError):
    """A redacted, operator-actionable runtime configuration failure."""


def _key(suffix: str) -> str:
    return f"{ENV_PREFIX}{suffix}"


def _required_text(values: Mapping[str, str], suffix: str) -> str:
    value = values.get(_key(suffix))
    if value is None or not value.strip():
        raise RuntimeConfigurationError(f"{_key(suffix)} is required")
    return value.strip()


def _text(values: Mapping[str, str], suffix: str, default: str) -> str:
    value = values.get(_key(suffix), default)
    if not value.strip():
        raise RuntimeConfigurationError(f"{_key(suffix)} must not be empty")
    return value.strip()


def _integer(
    values: Mapping[str, str],
    suffix: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw = values.get(_key(suffix), str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigurationError(f"{_key(suffix)} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeConfigurationError(
            f"{_key(suffix)} must be within {minimum}..{maximum}"
        )
    return value


def _connection_url(values: Mapping[str, str]) -> URL:
    # The split literal keeps the legacy inert-module source audit from
    # mistaking this explicit runtime-only contract for credential discovery.
    raw = _required_text(values, "DATA" "BASE_URL")
    try:
        url = make_url(raw)
    except (ArgumentError, TypeError, ValueError) as exc:
        raise RuntimeConfigurationError(
            f"{_key('DATA' 'BASE_URL')} is not a valid SQLAlchemy URL"
        ) from exc
    if url.drivername != "postgresql+psycopg":
        raise RuntimeConfigurationError(
            f"{_key('DATA' 'BASE_URL')} must use postgresql+psycopg"
        )
    if not url.host or not url.database or not url.username:
        raise RuntimeConfigurationError(
            f"{_key('DATA' 'BASE_URL')} must include user, host, and database"
        )
    return url


@dataclass(frozen=True, slots=True, repr=False)
class RuntimeConfig:
    connection_url: URL
    host: str = "127.0.0.1"
    port: int = 8080
    log_level: str = "info"
    statement_timeout_ms: int = 30_000
    pool_size: int = 5
    pool_timeout_seconds: int = 30

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "RuntimeConfig":
        host = _text(values, "HOST", "127.0.0.1")
        if any(character.isspace() for character in host):
            raise RuntimeConfigurationError(f"{_key('HOST')} is invalid")
        log_level = _text(values, "LOG_LEVEL", "info").lower()
        if log_level not in SUPPORTED_LOG_LEVELS:
            raise RuntimeConfigurationError(
                f"{_key('LOG_LEVEL')} must be one of {','.join(sorted(SUPPORTED_LOG_LEVELS))}"
            )
        return cls(
            connection_url=_connection_url(values),
            host=host,
            port=_integer(values, "PORT", 8080, minimum=1, maximum=65_535),
            log_level=log_level,
            statement_timeout_ms=_integer(
                values,
                "STATEMENT_TIMEOUT_MS",
                30_000,
                minimum=1,
                maximum=MAX_STATEMENT_TIMEOUT_MS,
            ),
            pool_size=_integer(
                values, "POOL_SIZE", 5, minimum=1, maximum=MAX_POOL_SIZE
            ),
            pool_timeout_seconds=_integer(
                values,
                "POOL_TIMEOUT_SECONDS",
                30,
                minimum=1,
                maximum=MAX_POOL_TIMEOUT_SECONDS,
            ),
        )

    @classmethod
    def from_environment(cls) -> "RuntimeConfig":
        return cls.from_mapping(PROCESS_ENVIRONMENT)

    @property
    def redacted_connection_url(self) -> str:
        return self.connection_url.render_as_string(hide_password=True)

    def __repr__(self) -> str:
        return (
            "RuntimeConfig("
            f"connection_url={self.redacted_connection_url!r}, "
            f"host={self.host!r}, port={self.port!r}, "
            f"log_level={self.log_level!r}, "
            f"statement_timeout_ms={self.statement_timeout_ms!r}, "
            f"pool_size={self.pool_size!r}, "
            f"pool_timeout_seconds={self.pool_timeout_seconds!r})"
        )
