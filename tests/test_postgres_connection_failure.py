from __future__ import annotations

import json
import ssl

import psycopg
import pytest
from sqlalchemy.exc import OperationalError as SqlAlchemyOperationalError

from app.db.connection_failure import (
    ConnectionFailureClass,
    build_safe_connection_report,
    classify_connection_failure,
    extract_postgres_sqlstate,
    is_invalid_password_failure,
    render_safe_connection_report,
)
from app.db.postgres_auth_probe import extract_error_response_sqlstate
from scripts import verify_postgres_invalid_password


class DriverOperationalError(psycopg.OperationalError):
    sqlstate = "28P01"


class OtherDatabaseError(psycopg.OperationalError):
    sqlstate = "42P01"


def _invalid_password() -> psycopg.errors.InvalidPassword:
    return psycopg.errors.InvalidPassword("unsafe authentication detail")


def test_direct_invalid_password_uses_sqlstate() -> None:
    error = _invalid_password()
    assert extract_postgres_sqlstate(error) == "28P01"
    assert is_invalid_password_failure(error)


def test_driver_operational_error_with_28p01_is_authentication_failure() -> None:
    error = DriverOperationalError("unsafe authentication detail")
    assert classify_connection_failure(error) is ConnectionFailureClass.AUTHENTICATION_FAILED


def test_sqlalchemy_operational_error_orig_with_28p01() -> None:
    error = SqlAlchemyOperationalError(
        "unsafe statement",
        {"password": "unsafe synthetic password"},
        DriverOperationalError("unsafe authentication detail"),
    )
    assert extract_postgres_sqlstate(error) == "28P01"
    assert is_invalid_password_failure(error)


def test_nested_cause_with_28p01() -> None:
    wrapper = RuntimeError("unsafe wrapper")
    wrapper.__cause__ = DriverOperationalError("unsafe authentication detail")
    assert is_invalid_password_failure(wrapper)


def test_nested_context_with_28p01() -> None:
    wrapper = RuntimeError("unsafe wrapper")
    wrapper.__context__ = DriverOperationalError("unsafe authentication detail")
    assert is_invalid_password_failure(wrapper)


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (TimeoutError("unsafe timeout detail"), ConnectionFailureClass.TIMEOUT),
        (
            ConnectionRefusedError("unsafe connection detail"),
            ConnectionFailureClass.CONNECTION_UNAVAILABLE,
        ),
        (ssl.SSLError("unsafe TLS detail"), ConnectionFailureClass.CONNECTION_SECURITY_ERROR),
        (OtherDatabaseError("unsafe database detail"), ConnectionFailureClass.DATABASE_ERROR),
        (RuntimeError("password authentication failed"), ConnectionFailureClass.UNKNOWN_CONNECTION_FAILURE),
    ),
)
def test_non_authentication_failures_are_not_authentication(
    error: BaseException,
    expected: ConnectionFailureClass,
) -> None:
    assert classify_connection_failure(error) is expected
    assert not is_invalid_password_failure(error)


def test_success_is_connected() -> None:
    report = build_safe_connection_report(None, pool_disabled=True, retries=0)
    assert report.connection == "CONNECTED"
    assert report.normalized_class == "CONNECTED"


def test_reporter_excludes_messages_uri_password_traceback_and_derived_data() -> None:
    prohibited_value = "unsafe synthetic " + "password"
    render_target = "postgresql" + "://" + "role:unsafe@database.example/app"
    wrapper = SqlAlchemyOperationalError(
        render_target,
        {"password": prohibited_value},
        DriverOperationalError(
            f"password authentication failed: {prohibited_value}"
        ),
    )

    report = build_safe_connection_report(wrapper, pool_disabled=True, retries=0)
    rendered = render_safe_connection_report(report)
    serialized = json.dumps(report.as_dict())

    for prohibited in (
        prohibited_value,
        render_target,
        "password authentication failed",
        "Traceback",
        "fingerprint",
        "sha256",
    ):
        assert prohibited not in rendered
        assert prohibited not in serialized
    assert report.sqlstate == "28P01"
    assert report.condition == "invalid_password"
    assert report.normalized_class == "AUTHENTICATION_FAILED"


def test_report_proves_pool_disabled_and_zero_retries() -> None:
    report = build_safe_connection_report(
        DriverOperationalError("unsafe authentication detail"),
        pool_disabled=True,
        retries=0,
    )
    assert report.as_dict()["pool_disabled"] == "YES"
    assert report.as_dict()["retries"] == 0


def test_authentication_classification_does_not_use_exception_message() -> None:
    misleading = RuntimeError("password authentication failed")
    assert (
        classify_connection_failure(misleading)
        is ConnectionFailureClass.UNKNOWN_CONNECTION_FAILURE
    )


def test_live_verifier_entrypoint_fails_closed_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_safely() -> int:
        raise RuntimeError("unsafe URI and password detail")

    monkeypatch.setattr(
        verify_postgres_invalid_password,
        "verify_synthetic_wrong_password",
        fail_safely,
    )
    assert verify_postgres_invalid_password.main([]) == 1
    output = capsys.readouterr().out
    assert "Traceback" not in output
    assert "unsafe" not in output
    assert "password" not in output
    assert "UNKNOWN_CONNECTION_FAILURE" in output


def test_postgres_error_response_extracts_only_structured_sqlstate() -> None:
    payload = (
        b"SERROR\x00"
        b"C28P01\x00"
        b"Mpassword authentication failed with unsafe detail\x00"
        b"\x00"
    )
    assert extract_error_response_sqlstate(payload) == "28P01"
