from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from app.engine_paper import reconciliation
from .conftest import FakeReader


def _manifest(tmp_path, **changes):
    values = {
        "target_class": "ISOLATED_POSTGRESQL_0012",
        "target_identity": "task-owned-cli-target",
        "expected_schema_head": reconciliation.EXPECTED_SCHEMA_HEAD,
    }
    values.update(changes)
    path = tmp_path / "safe-target.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_cli_executes_healthy_reconciliation_with_injected_safe_resolver(tmp_path, capsys):
    code = reconciliation.main(
        ["--target", str(_manifest(tmp_path)), "--read-only-reconcile"],
        reader_factory=lambda _request: FakeReader(),
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["outcome"] == "HEALTHY"
    assert payload["paper_table_queries"] == 8


def test_cli_without_permanent_resolver_fails_closed(tmp_path, capsys):
    code = reconciliation.main(
        ["--target", str(_manifest(tmp_path)), "--read-only-reconcile"]
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 12
    assert payload["outcome"] == "TARGET_REJECTED"


@pytest.mark.parametrize(
    "field",
    ["uri", "dsn", "password", "credential", "environment", "binding", "path"],
)
def test_target_manifest_rejects_every_secret_or_resolution_field(field, tmp_path):
    with pytest.raises(ValueError, match="TARGET_MANIFEST_FIELDS_REJECTED"):
        reconciliation.load_safe_target_manifest(_manifest(tmp_path, **{field: "forbidden"}))


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO paper_orders VALUES (1)", "UPDATE paper_orders SET state='OPEN'",
        "DELETE FROM paper_orders", "MERGE INTO paper_orders", "TRUNCATE paper_orders",
        "CREATE TABLE x(y int)", "ALTER TABLE paper_orders ADD COLUMN x int",
        "DROP TABLE paper_orders", "GRANT SELECT ON paper_orders TO x",
        "REVOKE SELECT ON paper_orders FROM x", "COPY paper_orders FROM STDIN", "CALL mutate()",
    ],
)
def test_sql_classifier_rejects_every_mutation_vocabulary(statement):
    reader = reconciliation.SqlAlchemyPaperReconciliationReader(object())
    with pytest.raises(reconciliation.ReadOnlyPolicyViolation):
        reader._execute(statement)
    assert reader.business_mutations + reader.schema_mutations == 1


def test_contracts_are_immutable(reconcile_request):
    with pytest.raises(FrozenInstanceError):
        reconcile_request.request_id = "changed"


def test_reconciliation_source_has_no_orm_mutation_calls():
    source = open(reconciliation.__file__, encoding="utf-8").read()
    assert "session.add(" not in source
    assert "session.delete(" not in source
    assert "session.flush(" not in source
    assert "session.commit(" not in source
