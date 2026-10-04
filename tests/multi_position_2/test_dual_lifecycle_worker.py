from types import SimpleNamespace

from app.operator_control.production_lifecycle_worker import (
    ProductionPaperFirstCanaryLifecycleWorker,
)


def test_worker_processes_both_rehydrated_lifecycles_independently(monkeypatch) -> None:
    first = SimpleNamespace(canary_id="a", lifecycle_slot=1)
    second = SimpleNamespace(canary_id="b", lifecycle_slot=2)
    worker = object.__new__(ProductionPaperFirstCanaryLifecycleWorker)
    worker._canary_store = SimpleNamespace(
        supervised_all=lambda: (first, second)
    )
    observed = []

    def run_one(canary):
        observed.append(canary.canary_id)
        return f"PROCESSED_{canary.canary_id.upper()}"

    monkeypatch.setattr(worker, "_run_one", run_one)

    assert worker.run_once() == (
        "slot=1:PROCESSED_A | slot=2:PROCESSED_B"
    )
    assert observed == ["a", "b"]
