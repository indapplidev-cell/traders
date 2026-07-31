from __future__ import annotations

from dataclasses import replace
from threading import Barrier, Thread

import pytest

from app.engine_paper.controlled_runtime_canary import (
    PaperControlledRuntimeCanaryFaultPoint,
    PaperControlledRuntimeCanaryOutcome,
    PaperControlledRuntimeCanaryStage,
)
from tests.paper_controlled_runtime_canary.conftest import build_canary


class CancelOnCall:
    def __init__(self, call_number):
        self.call_number = call_number
        self.calls = 0

    def is_cancelled(self):
        self.calls += 1
        return self.calls >= self.call_number


@pytest.mark.parametrize("cancel_call", (1, 2, 3, 4, 5))
@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_cancellation_at_each_precommit_boundary_has_zero_worker_calls(
    cancel_call, stage
):
    authority = CancelOnCall(cancel_call)
    request, service, worker, _, _ = build_canary(
        stage, cancellation_authority=authority
    )
    result = service.run(request)
    assert (
        result.outcome
        is PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_BEFORE_MUTATION
    )
    assert worker.calls == 0
    assert result.worker_invocations == 0
    assert result.cancellation_outcome == "CANCELLED_BEFORE_MUTATION"


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_cancellation_after_worker_commit_reports_durable_stage(stage):
    authority = CancelOnCall(6)
    request, service, worker, _, _ = build_canary(
        stage, cancellation_authority=authority
    )
    result = service.run(request)
    assert (
        result.outcome
        is PaperControlledRuntimeCanaryOutcome.CANARY_CANCELLED_AFTER_COMMITTED_STAGE
    )
    assert worker.calls == 1
    assert result.worker_invocations == 1
    assert result.mutation_budget_result == "PASS"
    assert result.postflight_lifecycle_state is not None


_PRE_WORKER_FAULTS = (
    PaperControlledRuntimeCanaryFaultPoint.BEFORE_CONFIGURATION_VALIDATION,
    PaperControlledRuntimeCanaryFaultPoint.AFTER_CONFIGURATION_VALIDATION,
    PaperControlledRuntimeCanaryFaultPoint.BEFORE_ISOLATED_TARGET_VALIDATION,
    PaperControlledRuntimeCanaryFaultPoint.AFTER_TARGET_VALIDATION,
    PaperControlledRuntimeCanaryFaultPoint.BEFORE_DRY_RUN,
    PaperControlledRuntimeCanaryFaultPoint.AFTER_DRY_RUN,
    PaperControlledRuntimeCanaryFaultPoint.BEFORE_FINGERPRINT_CHECK,
    PaperControlledRuntimeCanaryFaultPoint.AFTER_FINGERPRINT_CHECK,
    PaperControlledRuntimeCanaryFaultPoint.BEFORE_WORKER_INVOCATION,
)


@pytest.mark.parametrize("fault_point", _PRE_WORKER_FAULTS)
def test_each_pre_worker_fault_has_zero_worker_invocation(fault_point):
    def inject(point):
        if point is fault_point:
            raise RuntimeError("injected")

    request, service, worker, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
        fault_injector=inject,
    )
    result = service.run(request)
    assert result.outcome is not PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED
    assert worker.calls == 0
    assert result.worker_invocations == 0
    assert result.mutating_stage_invocations == 0


@pytest.mark.parametrize(
    "fault_point",
    (
        PaperControlledRuntimeCanaryFaultPoint.AFTER_WORKER_RETURN_BEFORE_POSTFLIGHT,
        PaperControlledRuntimeCanaryFaultPoint.DURING_POSTFLIGHT_READ,
        PaperControlledRuntimeCanaryFaultPoint.AFTER_POSTFLIGHT_BEFORE_RESULT,
    ),
)
def test_each_post_worker_fault_reports_no_retry_and_one_durable_call(fault_point):
    def inject(point):
        if point is fault_point:
            raise RuntimeError("injected")

    request, service, worker, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE,
        fault_injector=inject,
    )
    result = service.run(request)
    assert (
        result.outcome
        is PaperControlledRuntimeCanaryOutcome.CANARY_POSTFLIGHT_READ_FAILED
    )
    assert worker.calls == 1
    assert result.worker_invocations == 1


def test_graph_change_after_dry_run_stops_before_worker():
    holder = {}

    def inject(point):
        if point is PaperControlledRuntimeCanaryFaultPoint.AFTER_DRY_RUN:
            holder["loader"].graph = holder["after"]

    request, service, worker, loader, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY,
        fault_injector=inject,
    )
    holder["loader"] = loader
    holder["after"] = worker.after_graph
    result = service.run(request)
    assert (
        result.outcome
        is PaperControlledRuntimeCanaryOutcome.CANARY_GRAPH_CHANGED_AFTER_DRY_RUN
    )
    assert worker.calls == 0


@pytest.mark.parametrize("stage", tuple(PaperControlledRuntimeCanaryStage))
def test_two_concurrent_identical_requests_produce_one_material_stage(stage):
    request, service, worker, _, _ = build_canary(stage)
    barrier = Barrier(3)
    results = []

    def invoke():
        barrier.wait()
        results.append(service.run(request))

    threads = [Thread(target=invoke), Thread(target=invoke)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=5)
    assert len(results) == 2
    assert worker.calls == 1
    assert sum(item.worker_invocations for item in results) == 1
    assert {
        item.outcome for item in results
    } <= {
        PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_COMPLETED,
        PaperControlledRuntimeCanaryOutcome.CANARY_ALREADY_ADVANCED,
        PaperControlledRuntimeCanaryOutcome.CANARY_DRY_RUN_NOT_READY,
    }


def test_result_is_bounded_and_contains_no_orm_or_traceback():
    request, service, _, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_CLOSE
    )
    result = service.run(request)
    assert len(result.entity_summary) <= 16
    assert not hasattr(result, "__dict__")
    assert "traceback" not in repr(result).lower()
    assert "database_url" not in repr(result).lower()


def test_cycle_authority_cannot_request_more_than_one_stage():
    request, service, worker, _, _ = build_canary(
        PaperControlledRuntimeCanaryStage.EXECUTE_ENTRY
    )
    cycle = replace(request.cycle_request, max_stages=2)
    result = service.run(replace(request, cycle_request=cycle))
    assert result.outcome is PaperControlledRuntimeCanaryOutcome.CANARY_STAGE_LIMIT_INVALID
    assert worker.calls == 0
