from dataclasses import replace
import pytest
from app.engine_safety.readiness_domains import live_durability_ready
from app.operator_control.production_executor import ExistingCanaryRuntimeReadiness
from app.engine_safety.paper_production_control import MutationPrerequisites

@pytest.mark.parametrize("wal,pitr", [(False,False),(True,False),(False,True),(True,True)])
def test_recovery_independent_paper_and_closed_live(wal,pitr):
    r=ExistingCanaryRuntimeReadiness(database_durability_ready=True,paper_mutation_ready=True,wal_ready=wal,pitr_ready=pitr)
    assert r.persistence_ready_for("trade-5m-v2")
    assert r.persistence_ready_for("trade-15m-v1") == (wal and pitr)
    assert not live_durability_ready(True,wal,pitr,False)
    assert live_durability_ready(True,wal,pitr,True) == (wal and pitr)
    assert not replace(r,database_durability_ready=False).persistence_ready_for("trade-5m-v2")
    assert not replace(r,snapshot_authoritative=False).persistence_ready_for("trade-5m-v2")
    assert MutationPrerequisites(True,True,False,True,True,paper_durability_pass=True).passed
    assert not MutationPrerequisites(True,True,True,True,True,paper_durability_pass=False).passed
    assert not MutationPrerequisites(True,True,False,True,True).passed


@pytest.mark.parametrize("failed", range(7))
def test_actual_database_predicate_failure_blocks(failed):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from app.engine_safety.readiness_domains import observe_database
    row=[True]*7
    row[failed]=False
    session=SimpleNamespace(execute=lambda _:SimpleNamespace(one=lambda:row))
    observed=observe_database(lambda:nullcontext(session))
    assert observed.runtime_ready and not observed.durability_ready

def test_database_connection_failure_blocks():
    from app.engine_safety.readiness_domains import observe_database
    def unavailable(): raise OSError("unavailable")
    assert not observe_database(unavailable).durability_ready


def test_core_storage_failure_is_not_cleared_by_successful_read():
    from contextlib import nullcontext
    from types import SimpleNamespace
    from app.engine_safety.readiness_domains import observe_database,record_transaction_failure,record_transaction_success
    session=SimpleNamespace(execute=lambda _:SimpleNamespace(one=lambda:[True]*7))
    record_transaction_success()
    assert observe_database(lambda:nullcontext(session)).durability_ready
    record_transaction_failure(SimpleNamespace(sqlstate="53100"))
    assert not observe_database(lambda:nullcontext(session)).durability_ready
    record_transaction_success()
    assert observe_database(lambda:nullcontext(session)).durability_ready
