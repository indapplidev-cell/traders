from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from app.engine_paper.accounting import PaperAccountBaselineService, PaperAccountingError
from app.engine_paper.production_preparation import (
    READONLY_GRANTS,
    RUNTIME_GRANTS,
    PaperProductionAccountIdentityBinding,
    PaperProductionPreparationReadiness,
)
from app.engine_paper.baseline_repository import PaperAccountBaselineRepository
from app.engine_paper.accounting import PaperAccountingOutcome, PaperAccountingReconciliationService
from app.server_api.app_factory import create_app


IDENTITY = PaperProductionAccountIdentityBinding(
    "PAPER-PROD-PRIMARY", "PAPER-PROD-LIFECYCLE-01", "USDT")
NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


def test_real_pg16_0008_to_0013_preserves_existing_data_and_schema(source_contract_pg_engine):
    config = Config("alembic.ini")
    with source_contract_pg_engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO online_pipeline_runs "
            "(run_id,symbol,primary_timeframe,closed_until_ms,closed_until_utc,status,trigger_source,daemon_instance_id) "
            "VALUES ('source-contract-existing','BTCUSDT','1m',1,:at,'COMPLETED','TEST','isolated') "
            "ON CONFLICT (run_id) DO NOTHING"), {"at": NOW})
    command.upgrade(config, "0013_paper_first_canary_correlation")
    with source_contract_pg_engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0013_paper_first_canary_correlation"
        assert connection.execute(text("SELECT count(*) FROM online_pipeline_runs WHERE run_id='source-contract-existing'")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM paper_first_canary_sessions")).scalar_one() == 0
    assert "paper_first_canary_sessions" in inspect(source_contract_pg_engine).get_table_names()


def test_real_pg16_production_identity_baseline_create_get_idempotency_and_conflict(source_contract_pg_engine):
    factory = sessionmaker(bind=source_contract_pg_engine, autoflush=False, expire_on_commit=False)
    with source_contract_pg_engine.begin() as connection:
        connection.execute(text("TRUNCATE paper_account_baselines"))
    with factory.begin() as session:
        service = PaperAccountBaselineService(PaperAccountBaselineRepository(session))
        created = service.initialize(baseline_id="baseline:production-paper-v1",
            identity=IDENTITY.account_identity(), initial_balance=Decimal("100.00"), initialized_at=NOW)
    with factory.begin() as session:
        service = PaperAccountBaselineService(PaperAccountBaselineRepository(session))
        replay = service.initialize(baseline_id="baseline:replayed-request",
            identity=IDENTITY.account_identity(), initial_balance=Decimal("100.00"), initialized_at=NOW)
        assert replay == created
    with pytest.raises(PaperAccountingError):
        with factory.begin() as session:
            PaperAccountBaselineService(PaperAccountBaselineRepository(session)).initialize(
                baseline_id="baseline:conflict", identity=IDENTITY.account_identity(),
                initial_balance=Decimal("101.00"), initialized_at=NOW)
    with source_contract_pg_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM paper_account_baselines")).scalar_one() == 1


def test_real_pg16_declarative_grants_are_valid_and_idempotent(source_contract_pg_engine):
    role_runtime = "paper_source_contract_runtime"
    role_readonly = "paper_source_contract_readonly"
    with source_contract_pg_engine.begin() as connection:
        for role in (role_runtime, role_readonly):
            connection.execute(text(
                f'DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = \'{role}\') '
                f'THEN EXECUTE \'DROP OWNED BY "{role}"\'; END IF; END $$'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{role}"'))
            connection.execute(text(f'CREATE ROLE "{role}" NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS'))
        for _ in range(2):
            for grant in RUNTIME_GRANTS:
                connection.execute(text(f'GRANT {", ".join(grant.operations)} ON TABLE "{grant.table}" TO "{role_runtime}"'))
            for grant in READONLY_GRANTS:
                connection.execute(text(f'GRANT SELECT ON TABLE "{grant.table}" TO "{role_readonly}"'))
    with source_contract_pg_engine.connect() as connection:
        attrs = connection.execute(text(
            "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname IN (:runtime,:readonly) ORDER BY rolname"),
            {"runtime": role_runtime, "readonly": role_readonly}).all()
        assert len(attrs) == 2 and all(not any(row[1:]) for row in attrs)
        assert connection.execute(text(
            "SELECT has_table_privilege(:role,'paper_account_baselines','SELECT')"),
            {"role": role_runtime}).scalar_one()
        assert not connection.execute(text(
            "SELECT has_table_privilege(:role,'paper_account_baselines','INSERT,UPDATE,DELETE')"),
            {"role": role_runtime}).scalar_one()
        assert not connection.execute(text(
            "SELECT has_table_privilege(:role,'paper_orders','INSERT,UPDATE,DELETE')"),
            {"role": role_readonly}).scalar_one()
    with source_contract_pg_engine.begin() as connection:
        connection.execute(text(f'DROP OWNED BY "{role_runtime}"'))
        connection.execute(text(f'DROP OWNED BY "{role_readonly}"'))
        connection.execute(text(f'DROP ROLE "{role_runtime}"'))
        connection.execute(text(f'DROP ROLE "{role_readonly}"'))


def test_isolated_full_production_preparation_contract_remains_disabled_and_zero_trade(source_contract_pg_engine):
    factory = sessionmaker(bind=source_contract_pg_engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        repository = PaperAccountBaselineRepository(session)
        baselines = repository.list_for_identity(IDENTITY.account_identity())
        result = PaperAccountingReconciliationService(
            baseline_persistence=repository).reconcile_persisted(IDENTITY.account_identity(), ())
    assert len(baselines) == 1 and baselines[0].initial_balance == Decimal("100.00")
    assert result.outcome is PaperAccountingOutcome.HEALTHY
    assert PaperProductionPreparationReadiness(True, True, True, True, True, True, True, True).current_mutation_ready
    document = create_app().openapi()
    methods = [method for operations in document["paths"].values() for method in operations
               if method in {"get", "post", "put", "patch", "delete"}]
    assert methods.count("get") == 18 and set(methods) == {"get"}
    with source_contract_pg_engine.connect() as connection:
        for table in ("paper_execution_commands", "paper_orders", "paper_fills",
                      "paper_positions", "paper_first_canary_sessions"):
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
