from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine

from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.schema_compatibility import (
    BASE_READONLY_CAPABILITIES,
    ReadonlySchemaCapability,
    ReadonlySchemaCapabilityBridge,
    ReadonlySchemaCapabilityResult,
    inspect_readonly_schema_capabilities,
)


def _url(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.skip(f"{name} is not configured")
    return value


@pytest.mark.parametrize(
    ("variable", "revision", "parallel"),
    (
        ("READONLY_DUAL_SCHEMA_0016_URL", "0016_control_mobile_device_security", False),
        ("READONLY_DUAL_SCHEMA_0017_URL", "0017_parallel_trade_profiles", True),
    ),
)
def test_exact_postgres_schema_capabilities(variable, revision, parallel):
    engine = create_engine(_url(variable))
    try:
        with engine.connect() as connection:
            result = inspect_readonly_schema_capabilities(connection)
    finally:
        engine.dispose()
    assert result.compatible is True
    assert result.revision == revision
    assert result.has(ReadonlySchemaCapability.PARALLEL_TRADE_PROFILES) is parallel
    assert BASE_READONLY_CAPABILITIES <= result.capabilities


@pytest.mark.parametrize(
    ("variable", "mutation", "issue"),
    (
        (
            "READONLY_DUAL_SCHEMA_0016_URL",
            "ALTER TABLE paper_orders DROP COLUMN reason_code CASCADE",
            "MISSING_COLUMN:paper_orders.reason_code",
        ),
        (
            "READONLY_DUAL_SCHEMA_0017_URL",
            "ALTER TABLE online_pipeline_results DROP COLUMN profile_mode",
            "PARTIAL_0017_PROFILE_COLUMNS",
        ),
        (
            "READONLY_DUAL_SCHEMA_0017_URL",
            "DROP INDEX ix_online_pipeline_profile_boundary",
            "MISSING_PROFILE_BOUNDARY_INDEX",
        ),
        (
            "READONLY_DUAL_SCHEMA_0016_URL",
            "UPDATE alembic_version SET version_num='0015_trading_universe_activation'",
            "UNSUPPORTED_REVISION:0015_trading_universe_activation",
        ),
    ),
)
def test_negative_schema_states_fail_closed(variable, mutation, issue):
    engine = create_engine(_url(variable))
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.exec_driver_sql(mutation)
            result = inspect_readonly_schema_capabilities(connection)
            transaction.rollback()
    finally:
        engine.dispose()
    assert result.compatible is False
    assert issue in result.issues


def test_0016_projection_never_builds_profile_column_predicate():
    bridge = ReadonlySchemaCapabilityBridge()
    bridge.activate(ReadonlySchemaCapabilityResult(
        True, "0016_control_mobile_device_security", BASE_READONLY_CAPABILITIES
    ))
    adapter = SqlAlchemyReadAdapter(lambda: None, schema_capabilities=bridge)
    assert adapter._default_profile_predicates() == ()


def test_0017_projection_builds_bounded_sql_profile_predicate():
    bridge = ReadonlySchemaCapabilityBridge()
    bridge.activate(ReadonlySchemaCapabilityResult(
        True,
        "0017_parallel_trade_profiles",
        BASE_READONLY_CAPABILITIES | {ReadonlySchemaCapability.PARALLEL_TRADE_PROFILES},
    ))
    adapter = SqlAlchemyReadAdapter(lambda: None, schema_capabilities=bridge)
    predicates = adapter._default_profile_predicates()
    assert len(predicates) == 1
    assert "trade_profile_id" in str(predicates[0])
    assert "trade-15m-v1" in str(predicates[0].compile(compile_kwargs={"literal_binds": True}))


def test_bridge_rejects_incompatible_and_conflicting_activation():
    bridge = ReadonlySchemaCapabilityBridge()
    with pytest.raises(RuntimeError, match="READONLY_SCHEMA_CAPABILITY_CHECK_FAILED"):
        bridge.activate(ReadonlySchemaCapabilityResult(False, None, issues=("MISSING_TABLE:x",)))
    bridge.activate(ReadonlySchemaCapabilityResult(
        True, "0016_control_mobile_device_security", BASE_READONLY_CAPABILITIES
    ))
    with pytest.raises(RuntimeError, match="READONLY_SCHEMA_CAPABILITY_CHANGED"):
        bridge.activate(ReadonlySchemaCapabilityResult(
            True,
            "0017_parallel_trade_profiles",
            BASE_READONLY_CAPABILITIES | {ReadonlySchemaCapability.PARALLEL_TRADE_PROFILES},
        ))
