"""Prove PostgreSQL invalid-password classification without exposing secrets."""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg
from sqlalchemy.engine import make_url

from app.db.connection_failure import (
    ConnectionFailureClass,
    build_safe_connection_report,
    render_safe_connection_report,
)
from app.db.postgres_auth_probe import probe_postgres_authentication
from scripts.verify_persistent_secret_binding import (
    CANONICAL_BINDING,
    DATABASE_KEY,
    parse_binding_text,
)


def verify_synthetic_wrong_password(
    binding_path: Path = CANONICAL_BINDING,
    *,
    host_override: str | None = None,
    port_override: int | None = None,
) -> int:
    parsed = parse_binding_text(binding_path.read_text(encoding="utf-8"))
    database_url = parsed.values.get(DATABASE_KEY)
    if not database_url:
        print("connection=NOT_RUN")
        print("sqlstate=NONE")
        print("condition=none")
        print("normalized_class=UNKNOWN_CONNECTION_FAILURE")
        print("driver_exception_type=NONE")
        print("wrapper_exception_type=NONE")
        print("pool_disabled=YES")
        print("retries=0")
        return 1

    url = make_url(database_url)
    current_password = url.password or ""
    synthetic_password = secrets.token_urlsafe(32)
    while synthetic_password == current_password:
        synthetic_password = secrets.token_urlsafe(32)

    probe = probe_postgres_authentication(
        host=host_override or url.host or "",
        port=port_override or url.port or 5432,
        database=url.database or "",
        username=url.username or "",
        password=synthetic_password,
        timeout_seconds=3,
    )
    exception: BaseException | None = None
    if probe.sqlstate is not None:
        exception_type = psycopg.errors.lookup(probe.sqlstate)
        exception = exception_type()

    report = build_safe_connection_report(
        exception,
        pool_disabled=True,
        retries=0,
    )
    print(render_safe_connection_report(report))
    return (
        0
        if probe.connection == "DENIED"
        and report.normalized_class
        == ConnectionFailureClass.AUTHENTICATION_FAILED.value
        and report.sqlstate == "28P01"
        and report.condition == "invalid_password"
        else 1
    )


def main(argv: list[str] | None = None) -> int:
    try:
        parser = argparse.ArgumentParser(
            description="Safely prove PostgreSQL invalid-password SQLSTATE."
        )
        parser.add_argument("--host")
        parser.add_argument("--port", type=int)
        args = parser.parse_args(argv)
        return verify_synthetic_wrong_password(
            host_override=args.host,
            port_override=args.port,
        )
    except BaseException:
        print("connection=NOT_RUN")
        print("sqlstate=NONE")
        print("condition=none")
        print("normalized_class=UNKNOWN_CONNECTION_FAILURE")
        print("driver_exception_type=NONE")
        print("wrapper_exception_type=NONE")
        print("pool_disabled=YES")
        print("retries=0")
        return 1


if __name__ == "__main__":
    sys.exit(main())
