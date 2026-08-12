from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.db.paper_models import (
    PaperExecutionCommandRecord,
    PaperExitDecisionRecord,
    PaperExitEvaluationCursorRecord,
    PaperFillRecord,
    PaperJournalEntryRecord,
    PaperOrderEventRecord,
    PaperOrderRecord,
    PaperPositionRecord,
)
from app.engine_paper import operator_bounded_runtime_runner as operator
from app.engine_paper.controlled_runtime_sequence_canary import (
    PaperControlledRuntimeBoundedSequenceOutcome,
)
from app.engine_paper.controlled_runtime_canary import (
    TASK_ID as SINGLE_CYCLE_TASK_ID,
    canary_ownership_marker,
)
from app.engine_safety import PaperPositionState
from tests.paper_controlled_runtime_sequence_canary.test_postgres_sequence import (
    _all_cycles,
    _request,
    _seed_prefix,
)
from tests.paper_operator_bounded_runtime_runner.test_contract_and_cli import (
    _iso,
    _write,
    configuration_mapping,
    request_mapping,
)
from tests.paper_repository.conftest import (  # noqa: F401
    paper_session_factory,
    repository_postgres_engine,
)


class _ResolvedRequestResolver:
    def __init__(self, sequence_service, sequence_request, *, cleanup=True):
        self.sequence_service = sequence_service
        database_name = "paper_test_single_cycle_canary_01"
        role_name = "paper_canary_01_role"
        run_id = sequence_request.plan.sequence_run_id
        target = replace(
            sequence_request.plan.target_identity,
            task_id=SINGLE_CYCLE_TASK_ID,
            database_name=database_name,
            database_role_name=role_name,
            ownership_marker=canary_ownership_marker(
                SINGLE_CYCLE_TASK_ID, run_id, database_name, role_name
            ),
        )
        self.sequence_request = replace(
            sequence_request,
            plan=replace(sequence_request.plan, target_identity=target),
            arming=replace(sequence_request.arming, target_identity=target),
        )
        self.cleanup_result = cleanup
        self.resolve_calls = 0
        self.build_calls = 0
        self.cleanup_calls = 0
        self.last_sequence_result = None

    def resolve(self, target_identity, *, deadline):
        self.resolve_calls += 1

        def build(configuration, manifest, cancellation):
            self.build_calls += 1
            assert configuration.configuration_id == self.sequence_request.configuration.configuration_id
            return replace(self.sequence_request, cancellation_authority=cancellation)

        def cleanup():
            self.cleanup_calls += 1
            return self.cleanup_result

        resolver = self

        class CapturingService:
            def run(self, request):
                resolver.last_sequence_result = resolver.sequence_service.run(request)
                return resolver.last_sequence_result

        return operator.PaperOperatorResolvedIsolatedTarget(
            target_identity=target_identity,
            task_owned=True,
            migration_head="0013_paper_first_canary_correlation",
            sequence_service=CapturingService(),
            request_builder=build,
            cleanup=cleanup,
        )


def _operator_files(tmp_path: Path, sequence_request):
    stages = tuple(step.expected_stage for step in sequence_request.plan.ordered_step_plans)
    config = configuration_mapping(
        configuration_id=sequence_request.configuration.configuration_id
    )
    manifest = request_mapping(stages=stages)
    manifest.update(
        request_id=sequence_request.request_id,
        sequence_id=sequence_request.plan.sequence_run_id,
        configuration_id=sequence_request.configuration.configuration_id,
        correlation_id=sequence_request.plan.correlation_id,
    )
    acknowledgement = manifest["acknowledgement"]
    acknowledgement.update(
        request_id=sequence_request.request_id,
        sequence_id=sequence_request.plan.sequence_run_id,
        configuration_id=sequence_request.configuration.configuration_id,
        exact_ordered_stage_list=[stage.value for stage in stages],
        exact_max_step_count=len(stages),
        expires_at=_iso(sequence_request.plan.expires_at),
    )
    manifest["created_at"] = _iso(sequence_request.plan.created_at)
    manifest["evaluated_at"] = _iso(sequence_request.evaluated_at)
    manifest["expires_at"] = _iso(sequence_request.plan.expires_at)
    return (
        _write(tmp_path / "operator-config.json", config),
        _write(tmp_path / "operator-request.json", manifest),
    )


def _runner(resolver, now):
    return operator.PaperOperatorControlledBoundedRuntimeRunner(
        resolver, clock=lambda: now
    )


@pytest.mark.parametrize("length", (1, 2, 3, 4, 5))
def test_operator_runner_postgres_explicit_prefixes(
    clean_paper_factory, tmp_path, length
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"operator-prefix-{length}")
    sequence_service, sequence_request = _request(
        factory, cycles, stop=length, suffix=f"operator-prefix-{length}"
    )
    paths = _operator_files(tmp_path, sequence_request)
    resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    result = _runner(resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    )
    assert result.exit_code is operator.PaperOperatorRuntimeExitCode.COMPLETED, resolver.last_sequence_result
    assert result.requested_step_count == result.completed_step_count == length
    assert result.worker_invocation_count == length
    assert resolver.resolve_calls == resolver.build_calls == resolver.cleanup_calls == 1


@pytest.mark.parametrize("prefix", (1, 2, 3, 4))
def test_operator_runner_postgres_partial_resume(
    clean_paper_factory, tmp_path, prefix
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, f"operator-resume-{prefix}")
    _seed_prefix(factory, cycles, prefix)
    sequence_service, sequence_request = _request(
        factory, cycles, suffix=f"operator-resume-{prefix}"
    )
    paths = _operator_files(tmp_path, sequence_request)
    resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    result = _runner(resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    )
    assert result.exit_code is operator.PaperOperatorRuntimeExitCode.COMPLETED
    assert result.worker_invocation_count == 5 - prefix
    assert result.durable_prefix_length == 5


def test_operator_runner_postgres_targeted_subsequence(
    clean_paper_factory, tmp_path
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "operator-targeted")
    _seed_prefix(factory, cycles, 2)
    sequence_service, sequence_request = _request(
        factory, cycles, start=2, stop=4, suffix="operator-targeted"
    )
    paths = _operator_files(tmp_path, sequence_request)
    resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    result = _runner(resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    )
    assert result.exit_code == 0
    assert result.requested_step_count == result.worker_invocation_count == 2


def test_operator_runner_cli_full_five_step_exact_graph(
    clean_paper_factory, tmp_path, capsys
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "operator-full-five")
    sequence_service, sequence_request = _request(
        factory, cycles, suffix="operator-full-five"
    )
    config_path, request_path = _operator_files(tmp_path, sequence_request)
    resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    argv = (
        "--config", str(config_path), "--request", str(request_path),
        "--operator-controlled-bounded-run", "--summary-format", "json",
    )
    code = operator.main(
        argv, runner=_runner(resolver, sequence_request.evaluated_at)
    )
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.count("\n") == 1
    assert captured.err == ""
    assert resolver.resolve_calls == resolver.build_calls == resolver.cleanup_calls == 1
    with factory() as session:
        counts = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                PaperExecutionCommandRecord, PaperOrderRecord, PaperFillRecord,
                PaperPositionRecord, PaperExitEvaluationCursorRecord,
                PaperExitDecisionRecord, PaperOrderEventRecord,
                PaperJournalEntryRecord,
            )
        )
        position = session.scalar(select(PaperPositionRecord))
    assert counts == (1, 2, 2, 1, 1, 1, 8, 12)
    assert position is not None
    assert position.state == PaperPositionState.CLOSED.value
    assert position.realized_pnl is not None


def test_operator_runner_postgres_completed_replay_new_process(
    clean_paper_factory, tmp_path
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "operator-replay")
    sequence_service, sequence_request = _request(
        factory, cycles, suffix="operator-replay"
    )
    paths = _operator_files(tmp_path, sequence_request)
    first_resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    assert _runner(first_resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    ).worker_invocation_count == 5
    replay_resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    replay = _runner(replay_resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    )
    assert replay.exit_code == 0
    assert replay.worker_invocation_count == 0
    assert replay.durable_prefix_length == 5


def test_operator_runner_postgres_concurrent_process_equivalents(
    clean_paper_factory, tmp_path
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "operator-concurrent")
    sequence_service, sequence_request = _request(
        factory, cycles, suffix="operator-concurrent"
    )
    paths = _operator_files(tmp_path, sequence_request)

    def run_once(_):
        resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
        return _runner(resolver, sequence_request.evaluated_at).run(
            operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(pool.map(run_once, range(2)))
    assert sorted(result.worker_invocation_count for result in results) == [0, 5]
    assert all(result.exit_code == 0 for result in results)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PaperFillRecord)) == 2
        assert session.scalar(select(func.count()).select_from(PaperPositionRecord)) == 1


def test_operator_runner_postgres_ambiguous_resume_zero_worker(
    clean_paper_factory, tmp_path
):
    factory = clean_paper_factory
    _, cycles = _all_cycles(factory, "operator-ambiguous")
    _seed_prefix(factory, cycles, 2)
    sequence_service, sequence_request = _request(
        factory, cycles, suffix="operator-ambiguous"
    )
    corrupted_entry = replace(cycles[1], entry_fill_id="fill:operator:missing")
    sequence_request = replace(
        sequence_request,
        ordered_cycle_requests=(cycles[0], corrupted_entry, *cycles[2:]),
    )
    paths = _operator_files(tmp_path, sequence_request)
    resolver = _ResolvedRequestResolver(sequence_service, sequence_request)
    result = _runner(resolver, sequence_request.evaluated_at).run(
        operator.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)
    )
    assert result.exit_code is operator.PaperOperatorRuntimeExitCode.RESUME_STATE_AMBIGUOUS
    assert result.worker_invocation_count == 0
    assert result.sequence_outcome == PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_RESUME_STATE_AMBIGUOUS.value
