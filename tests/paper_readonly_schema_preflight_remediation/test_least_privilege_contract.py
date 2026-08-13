from __future__ import annotations

import pytest

from app.engine_paper.production_preparation import (
    READONLY_ACCEPTED_GRANTS,
    READONLY_BASELINE_GRANTS,
    READONLY_GRANTS,
    classify_database_privilege_drift,
    required_database_privileges_present,
)


def _rows(grants):
    return tuple(
        (grant.table, operation, "NO")
        for grant in grants
        for operation in grant.operations
    )


def test_schema_preflight_contract_requires_exact_select_only():
    by_table = {grant.table: grant.operations for grant in READONLY_GRANTS}

    assert by_table["alembic_version"] == ("SELECT",)
    assert required_database_privileges_present(
        (("alembic_version", "SELECT", "NO"),),
        tuple(grant for grant in READONLY_GRANTS if grant.table == "alembic_version"),
    )


def test_existing_readonly_and_paper_reporting_selects_are_preserved():
    accepted = _rows(READONLY_ACCEPTED_GRANTS)
    tables = {table for table, operation, grantable in accepted
              if operation == "SELECT" and grantable == "NO"}

    assert {grant.table for grant in READONLY_BASELINE_GRANTS} <= tables
    assert {grant.table for grant in READONLY_GRANTS} <= tables
    assert not classify_database_privilege_drift(accepted, READONLY_ACCEPTED_GRANTS)


@pytest.mark.parametrize("operation", [
    "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER",
])
def test_schema_preflight_write_and_table_ddl_privileges_are_rejected(operation):
    rows = _rows(READONLY_ACCEPTED_GRANTS) + (("alembic_version", operation, "NO"),)

    assert classify_database_privilege_drift(rows, READONLY_ACCEPTED_GRANTS)


def test_schema_preflight_grant_option_and_elevation_are_rejected():
    accepted = _rows(READONLY_ACCEPTED_GRANTS)

    assert classify_database_privilege_drift(
        accepted + (("alembic_version", "SELECT", "YES"),),
        READONLY_ACCEPTED_GRANTS,
    )
    assert classify_database_privilege_drift(
        accepted, READONLY_ACCEPTED_GRANTS, ownership=1,
    )
    assert classify_database_privilege_drift(
        accepted, READONLY_ACCEPTED_GRANTS, memberships=1,
    )
    assert classify_database_privilege_drift(
        accepted, READONLY_ACCEPTED_GRANTS, non_table_acl=1,
    )
