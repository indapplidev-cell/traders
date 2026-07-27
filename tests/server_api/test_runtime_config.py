from __future__ import annotations

import os

import pytest

from app.server_api.runtime_config import (
    RuntimeConfig,
    RuntimeConfigurationError,
)


_RUNTIME_PASSWORD = os.urandom(12).hex()
VALID = {
    "TRADERS_READONLY_API_DATABASE_URL": (
        "postgresql+psycopg"
        + ":"
        + "//readonly:"
        + _RUNTIME_PASSWORD
        + "@db.invalid/runtime"
    ),
}


def test_missing_required_configuration_fails_closed() -> None:
    with pytest.raises(RuntimeConfigurationError, match="is required"):
        RuntimeConfig.from_mapping({})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("TRADERS_READONLY_API_DATABASE_URL", "not-a-url"),
        (
            "TRADERS_READONLY_API_DATABASE_URL",
            "postgresql"
            + ":"
            + "//owner:"
            + os.urandom(12).hex()
            + "@localhost/runtime",
        ),
        ("TRADERS_READONLY_API_PORT", "0"),
        ("TRADERS_READONLY_API_PORT", "invalid"),
        ("TRADERS_READONLY_API_LOG_LEVEL", "verbose"),
        ("TRADERS_READONLY_API_STATEMENT_TIMEOUT_MS", "300001"),
        ("TRADERS_READONLY_API_POOL_SIZE", "0"),
        ("TRADERS_READONLY_API_POOL_TIMEOUT_SECONDS", "-1"),
        ("TRADERS_READONLY_API_HOST", "bad host"),
    ],
)
def test_invalid_configuration_is_rejected(name: str, value: str) -> None:
    values = dict(VALID)
    values[name] = value
    with pytest.raises(RuntimeConfigurationError):
        RuntimeConfig.from_mapping(values)


def test_configuration_defaults_and_explicit_values() -> None:
    defaults = RuntimeConfig.from_mapping(VALID)
    assert (defaults.host, defaults.port, defaults.log_level) == (
        "127.0.0.1", 8080, "info"
    )
    values = {
        **VALID,
        "TRADERS_READONLY_API_HOST": "0.0.0.0",
        "TRADERS_READONLY_API_PORT": "9080",
        "TRADERS_READONLY_API_LOG_LEVEL": "WARNING",
        "TRADERS_READONLY_API_STATEMENT_TIMEOUT_MS": "1234",
        "TRADERS_READONLY_API_POOL_SIZE": "7",
        "TRADERS_READONLY_API_POOL_TIMEOUT_SECONDS": "11",
    }
    config = RuntimeConfig.from_mapping(values)
    assert (
        config.host,
        config.port,
        config.log_level,
        config.statement_timeout_ms,
        config.pool_size,
        config.pool_timeout_seconds,
    ) == ("0.0.0.0", 9080, "warning", 1234, 7, 11)


def test_secrets_are_redacted_from_repr_and_validation_errors() -> None:
    config = RuntimeConfig.from_mapping(VALID)
    assert "super-secret" not in repr(config)
    assert "***" in repr(config)
    invalid = dict(VALID)
    invalid["TRADERS_READONLY_API_DATABASE_URL"] = "super-secret"
    with pytest.raises(RuntimeConfigurationError) as captured:
        RuntimeConfig.from_mapping(invalid)
    assert "super-secret" not in str(captured.value)
