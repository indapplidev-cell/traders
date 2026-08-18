from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.server_api.schema_compatibility import inspect_required_paper_schema


ROLE = "mobile_security_contract_test"
DEVICE_ID = "f3dd84a0-2278-4e27-8d40-aed4494744a1"


@pytest.fixture(scope="module")
def isolated_mobile_pg16():
    raw = os.environ.get("MOBILE_SECURITY_TEST_DATABASE_URL")
    if not raw:
        pytest.skip("MOBILE_SECURITY_TEST_DATABASE_URL is not configured")
    engine = create_engine(raw, hide_parameters=True)
    with engine.connect() as connection:
        assert str(connection.execute(text("SHOW server_version_num")).scalar_one()).startswith("16")
    import app.config.settings as settings

    original = settings.get_settings
    settings.get_settings = lambda: SimpleNamespace(database_url=raw)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        connection.exec_driver_sql("CREATE SCHEMA public")
    command.upgrade(Config("alembic.ini"), "0016_control_mobile_device_security")
    with engine.begin() as connection:
        connection.exec_driver_sql(f'DROP ROLE IF EXISTS "{ROLE}"')
        connection.exec_driver_sql(
            f'CREATE ROLE "{ROLE}" NOLOGIN NOSUPERUSER NOCREATEDB '
            "NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        )
        connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{ROLE}"')
        connection.exec_driver_sql(
            f'GRANT SELECT ON TABLE "control_mobile_devices" TO "{ROLE}"'
        )
        connection.exec_driver_sql(
            f'GRANT INSERT ON TABLE "control_mobile_replay_nonces" TO "{ROLE}"'
        )
        connection.execute(text(
            "INSERT INTO control_mobile_devices "
            "(device_id,public_key_spki,public_key_fingerprint,algorithm,key_version,"
            "enabled,label,created_at,revoked_at) VALUES "
            "(:device,:spki,:fingerprint,'ECDSA_P256_SHA256',1,true,NULL,:now,NULL)"
        ), {
            "device": DEVICE_ID,
            "spki": b"x" * 80,
            "fingerprint": "a" * 64,
            "now": datetime.now(timezone.utc),
        })
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'DROP OWNED BY "{ROLE}"')
            connection.exec_driver_sql(f'DROP ROLE IF EXISTS "{ROLE}"')
        engine.dispose()
        settings.get_settings = original


def _as_role(engine, statement: str, parameters=None):
    with engine.begin() as connection:
        connection.exec_driver_sql(f'SET LOCAL ROLE "{ROLE}"')
        result = connection.execute(text(statement), parameters or {})
        return result.all() if result.returns_rows else ()


def test_real_0016_required_object_contract_and_negative_mutations(isolated_mobile_pg16):
    engine = isolated_mobile_pg16
    with engine.connect() as connection:
        assert inspect_required_paper_schema(connection).compatible
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.exec_driver_sql(
            "ALTER TABLE paper_account_baselines DROP COLUMN semantic_version"
        )
        result = inspect_required_paper_schema(connection)
        assert not result.compatible
        assert "MISSING_COLUMN:paper_account_baselines.semantic_version" in result.issues
        transaction.rollback()
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.exec_driver_sql("DROP TABLE paper_journal_entries")
        result = inspect_required_paper_schema(connection)
        assert not result.compatible
        assert "MISSING_TABLE:paper_journal_entries" in result.issues
        transaction.rollback()


def test_exact_runtime_operations_succeed_and_replay_is_atomic(isolated_mobile_pg16):
    engine = isolated_mobile_pg16
    assert len(_as_role(
        engine,
        "SELECT device_id FROM control_mobile_devices WHERE device_id=:device",
        {"device": DEVICE_ID},
    )) == 1
    now = datetime.now(timezone.utc)
    values = {
        "device": DEVICE_ID,
        "nonce": "A" * 22,
        "issued": now,
        "expires": now + timedelta(days=1),
        "request": "request-contract-0001",
        "accepted": now,
    }
    _as_role(
        engine,
        "INSERT INTO control_mobile_replay_nonces "
        "(device_id,nonce,issued_at,expires_at,request_id,action,accepted_at) "
        "VALUES (:device,:nonce,:issued,:expires,:request,'ARM',:accepted)",
        values,
    )
    with pytest.raises(IntegrityError):
        _as_role(
            engine,
            "INSERT INTO control_mobile_replay_nonces "
            "(device_id,nonce,issued_at,expires_at,request_id,action,accepted_at) "
            "VALUES (:device,:nonce,:issued,:expires,:request,'ARM',:accepted)",
            values,
        )


@pytest.mark.parametrize(
    "statement",
    (
        "SELECT * FROM control_mobile_replay_nonces",
        "INSERT INTO control_mobile_devices (device_id) VALUES ('blocked')",
        "UPDATE control_mobile_devices SET enabled=false",
        "DELETE FROM control_mobile_replay_nonces",
        "SELECT * FROM paper_positions",
        "ALTER TABLE control_mobile_devices ADD COLUMN forbidden integer",
        "CREATE TABLE forbidden_runtime_table (id integer)",
    ),
)
def test_unneeded_dml_unrelated_reads_and_ddl_are_denied(
    isolated_mobile_pg16, statement
):
    with pytest.raises(DBAPIError):
        _as_role(isolated_mobile_pg16, statement)


def test_role_has_no_elevation_membership_or_ownership(isolated_mobile_pg16):
    with isolated_mobile_pg16.connect() as connection:
        row = connection.execute(text(
            "SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls "
            "FROM pg_roles WHERE rolname=:role"
        ), {"role": ROLE}).one()
        memberships = connection.execute(text(
            "SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member "
            "WHERE r.rolname=:role"
        ), {"role": ROLE}).scalar_one()
        ownership = connection.execute(text(
            "SELECT count(*) FROM pg_class c JOIN pg_roles r ON r.oid=c.relowner "
            "WHERE r.rolname=:role"
        ), {"role": ROLE}).scalar_one()
    assert tuple(row) == (False, False, False, False, False)
    assert memberships == ownership == 0
