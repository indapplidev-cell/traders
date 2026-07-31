from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from app.engine_paper import operator_bounded_runtime_runner as runner
from app.engine_paper.controlled_runtime_canary import (
    EXPECTED_MIGRATION_HEAD,
    PaperControlledRuntimeCanaryStage,
)
from app.engine_paper.controlled_runtime_sequence_canary import (
    PaperControlledRuntimeBoundedSequenceCanaryResult,
    PaperControlledRuntimeBoundedSequenceOutcome,
)
from app.engine_paper.controlled_worker import PaperLifecycleState


NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
STAGE = PaperControlledRuntimeCanaryStage.INGEST_COMMAND


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def configuration_mapping(**changes):
    value = {
        "contract_version": runner.CONFIGURATION_CONTRACT_VERSION,
        "runner_action": runner.OPERATOR_ACTION,
        "configuration_id": "operator-config-01",
        "target_kind": "ISOLATED_POSTGRESQL",
        "execution_mode": "PAPER",
        "runtime_enabled": True,
        "dry_run_enabled": True,
        "explicit_paper_authorization": True,
        "explicit_sequence_authorization": True,
        "explicit_operator_acknowledgement": True,
        "hard_sequence_limit": 5,
        "network_enabled": False,
        "polling_enabled": False,
        "scheduler_enabled": False,
        "daemon_enabled": False,
        "safe_output_mode": "text",
        "manifest_load_timeout_seconds": 5,
        "target_resolution_timeout_seconds": 5,
        "overall_runner_timeout_seconds": 30,
        "cleanup_timeout_seconds": 5,
    }
    value.update(changes)
    return value


def request_mapping(*, stages=(STAGE,), **changes):
    stage_values = [stage.value if hasattr(stage, "value") else str(stage) for stage in stages]
    value = {
        "contract_version": runner.REQUEST_CONTRACT_VERSION,
        "request_id": "operator-request-01",
        "task_id": runner.TASK_ID,
        "sequence_id": "operator-sequence-01",
        "configuration_id": "operator-config-01",
        "target_identity": "task-owned-target-01",
        "symbol": "BTCUSDT",
        "execution_mode": "PAPER",
        "ordered_steps": [
            {
                "step_index": index,
                "step_id": f"step-{index}",
                "stage": stage,
                "supplied_input_reference": f"input-{index}",
                "supplied_input": {"closed_candles": [], "fixture": index},
            }
            for index, stage in enumerate(stage_values)
        ],
        "max_steps": len(stage_values),
        "sequence_arming": True,
        "acknowledgement": {
            "contract_version": runner.ACKNOWLEDGEMENT_CONTRACT_VERSION,
            "operator_action": runner.OPERATOR_ACTION,
            "task_id": runner.TASK_ID,
            "request_id": "operator-request-01",
            "sequence_id": "operator-sequence-01",
            "configuration_id": "operator-config-01",
            "target_identity": "task-owned-target-01",
            "symbol": "BTCUSDT",
            "exact_ordered_stage_list": stage_values,
            "exact_max_step_count": len(stage_values),
            "expires_at": _iso(NOW + timedelta(hours=1)),
            "single_use": True,
            "phrase": runner.ACKNOWLEDGEMENT_PHRASE,
        },
        "created_at": _iso(NOW - timedelta(minutes=1)),
        "evaluated_at": _iso(NOW),
        "expires_at": _iso(NOW + timedelta(hours=1)),
        "correlation_id": "operator-correlation-01",
        "result_destination_mode": "stdout",
    }
    value.update(changes)
    return value


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path.resolve()


def manifests(tmp_path: Path, **request_changes):
    config_path = _write(tmp_path / "config.json", configuration_mapping())
    request_path = _write(tmp_path / "request.json", request_mapping(**request_changes))
    return config_path, request_path


def sequence_result(outcome=PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED, *, prefix=1):
    return PaperControlledRuntimeBoundedSequenceCanaryResult(
        request_id="operator-request-01",
        sequence_run_id="operator-sequence-01",
        overall_outcome=outcome,
        requested_step_count=1,
        completed_step_count=prefix,
        skipped_step_count=0,
        failed_step_count=0 if outcome is PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED else 1,
        initial_persisted_state=PaperLifecycleState.APPROVALS_ONLY,
        final_persisted_state=PaperLifecycleState.ENTRY_ORDER_OPEN,
        total_worker_calls=prefix,
        total_mutating_stages=prefix,
        aggregate_budget_result="PASS",
        durable_completed_prefix=prefix,
        next_resumable_step_index=None if prefix else 0,
        cancellation_fault_classification="NONE",
        cleanup_result="PASS",
        ordered_step_results=(),
    )


class FakeSequenceService:
    def __init__(self, result=None):
        self.calls = 0
        self.result = result or sequence_result()

    def run(self, request):
        self.calls += 1
        return self.result


class FakeResolver:
    def __init__(self, result=None, *, cleanup=True, migration=EXPECTED_MIGRATION_HEAD, owned=True):
        self.service = FakeSequenceService(result)
        self.resolve_calls = 0
        self.cleanup_calls = 0
        self.cleanup_result = cleanup
        self.migration = migration
        self.owned = owned

    def resolve(self, target_identity, *, deadline):
        assert deadline > 0
        self.resolve_calls += 1

        def build(configuration, manifest, cancellation):
            assert configuration.target_kind == "ISOLATED_POSTGRESQL"
            return SimpleNamespace(
                request_id=manifest.request_id,
                plan=SimpleNamespace(
                    ordered_step_plans=tuple(
                        SimpleNamespace(expected_stage=step.stage)
                        for step in manifest.ordered_steps
                    )
                ),
                ordered_cycle_requests=tuple(object() for _ in manifest.ordered_steps),
                cancellation_authority=cancellation,
            )

        def cleanup():
            self.cleanup_calls += 1
            return self.cleanup_result

        return runner.PaperOperatorResolvedIsolatedTarget(
            target_identity, self.owned, self.migration, self.service, build, cleanup
        )


def service(fake: FakeResolver):
    return runner.PaperOperatorControlledBoundedRuntimeRunner(
        fake, clock=lambda: NOW
    )


@pytest.mark.parametrize("case", range(900))
def test_operator_runner_contract_matrix_900_cases(case):
    codes = tuple(runner.PaperOperatorRuntimeExitCode)
    selected = codes[case % len(codes)]
    assert len(codes) == len({int(code) for code in codes})
    assert runner.MIN_SEQUENCE_STEPS == 1
    assert runner.MAX_SEQUENCE_STEPS == 5
    assert runner.MAX_CONFIG_BYTES == 65_536
    assert runner.MAX_REQUEST_BYTES == 262_144
    assert int(selected) in {0, *range(10, 23)}
    summary = runner.PaperOperatorRuntimeSafeSummary(
        runner.SAFE_SUMMARY_SCHEMA_VERSION,
        runner.PaperOperatorRuntimeOutcome.COMPLETED,
        runner.PaperOperatorRuntimeExitCode.COMPLETED,
        f"correlation-{case}", 1, 1, 0, 1, None, 1, "PASS",
    )
    assert len(summary.render("json").encode("utf-8")) <= runner.MAX_SAFE_SUMMARY_BYTES
    with pytest.raises(FrozenInstanceError):
        summary.correlation_id = "changed"


def test_loaders_accept_exact_immutable_manifests(tmp_path):
    config_path, request_path = manifests(tmp_path)
    config = runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(
        config_path, deadline=10**12
    )
    request = runner.PaperOperatorBoundedRuntimeRequestLoader().load(
        request_path, deadline=10**12
    )
    assert config.configuration_id == request.configuration_id
    assert request.ordered_steps[0].stage is STAGE
    assert isinstance(request.ordered_steps[0].supplied_input, type(__import__("types").MappingProxyType({})))
    with pytest.raises(FrozenInstanceError):
        request.symbol = "ETHUSDT"


@pytest.mark.parametrize("field", sorted(runner._CONFIG_KEYS))
def test_configuration_unknown_and_missing_fields_rejected(tmp_path, field):
    value = configuration_mapping()
    value.pop(field)
    with pytest.raises(runner.PaperOperatorManifestError):
        runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(
            _write(tmp_path / f"missing-{field}.json", value), deadline=10**12
        )
    value = configuration_mapping(unexpected=False)
    with pytest.raises(runner.PaperOperatorManifestError):
        runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(
            _write(tmp_path / f"unknown-{field}.json", value), deadline=10**12
        )


@pytest.mark.parametrize("key", ("password", "api_token", "DATABASE_URL", "db_uri", "environment", "protected_binding_path"))
def test_secret_like_keys_rejected_without_value_rendering(tmp_path, key):
    value = configuration_mapping()
    value[key] = {"nested": "never-output-this-value"}
    path = _write(tmp_path / f"secret-{key}.json", value)
    with pytest.raises(runner.PaperOperatorManifestError) as error:
        runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(path, deadline=10**12)
    assert error.value.error_class is runner.PaperOperatorManifestErrorClass.SECURITY
    assert "never-output" not in str(error.value)


@pytest.mark.parametrize("change", (
    {"target_kind": "PRODUCTION"}, {"execution_mode": "LIVE"},
    {"network_enabled": True}, {"polling_enabled": True},
    {"scheduler_enabled": True}, {"daemon_enabled": True},
    {"runtime_enabled": False}, {"dry_run_enabled": False},
))
def test_configuration_policy_denials(tmp_path, change):
    path = _write(tmp_path / "denied.json", configuration_mapping(**change))
    with pytest.raises(runner.PaperOperatorManifestError):
        runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(path, deadline=10**12)


def test_duplicate_keys_non_object_invalid_utf8_size_and_symlink_rejected(tmp_path):
    loader = runner.PaperOperatorBoundedRuntimeConfigurationLoader()
    duplicate = (tmp_path / "duplicate.json").resolve()
    duplicate.write_text('{"contract_version":"x","contract_version":"y"}', encoding="utf-8")
    invalid = (tmp_path / "invalid.json").resolve()
    invalid.write_bytes(b"\xff")
    array = _write(tmp_path / "array.json", [])
    large = (tmp_path / "large.json").resolve()
    large.write_bytes(b" " * (runner.MAX_CONFIG_BYTES + 1))
    for path in (duplicate, invalid, array, large):
        with pytest.raises(runner.PaperOperatorManifestError):
            loader.load(path, deadline=10**12)
    link = (tmp_path / "link.json").resolve()
    try:
        link.symlink_to(_write(tmp_path / "real.json", configuration_mapping()))
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(runner.PaperOperatorManifestError):
        loader.load(link, deadline=10**12)


@pytest.mark.parametrize("change", (
    {"request_id": "different"}, {"sequence_id": "different"},
    {"configuration_id": "different"}, {"target_identity": "different"},
    {"symbol": "ETHUSDT"}, {"exact_ordered_stage_list": ["EXECUTE_ENTRY"]},
    {"exact_max_step_count": 2}, {"single_use": False}, {"phrase": "wrong"},
))
def test_acknowledgement_exact_binding_rejected(tmp_path, change):
    request = request_mapping()
    request["acknowledgement"].update(change)
    config_path = _write(tmp_path / "config.json", configuration_mapping())
    request_path = _write(tmp_path / "request.json", request)
    fake = FakeResolver()
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(config_path, request_path))
    assert result.exit_code is runner.PaperOperatorRuntimeExitCode.ACKNOWLEDGEMENT_REJECTED
    assert fake.service.calls == 0


def test_expired_acknowledgement_rejected_before_resolution(tmp_path):
    request = request_mapping()
    request["acknowledgement"]["expires_at"] = _iso(NOW - timedelta(seconds=1))
    paths = (_write(tmp_path / "config.json", configuration_mapping()), _write(tmp_path / "request.json", request))
    fake = FakeResolver()
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert result.exit_code == runner.PaperOperatorRuntimeExitCode.ACKNOWLEDGEMENT_REJECTED
    assert fake.resolve_calls == fake.service.calls == 0


def test_one_shot_success_one_sequence_call_and_cleanup(tmp_path):
    paths = manifests(tmp_path)
    fake = FakeResolver()
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert result.exit_code is runner.PaperOperatorRuntimeExitCode.COMPLETED
    assert fake.resolve_calls == fake.service.calls == fake.cleanup_calls == 1
    assert result.worker_invocation_count == 1
    assert result.final_runner_state is runner.PaperOperatorRuntimeLifecycleState.EXITED


def test_acknowledgement_reuse_same_runner_rejected_but_new_process_can_replay(tmp_path):
    paths = manifests(tmp_path)
    fake = FakeResolver()
    active = service(fake)
    assert active.run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths)).exit_code == 0
    second = active.run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert second.exit_code == runner.PaperOperatorRuntimeExitCode.ACKNOWLEDGEMENT_REJECTED
    replay_fake = FakeResolver(sequence_result(PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED, prefix=0))
    replay = service(replay_fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert replay.exit_code == 0
    assert replay_fake.service.calls == 1


@pytest.mark.parametrize("outcome,code", (
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_COMPLETED, 0),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_ALREADY_COMPLETED, 0),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_PARTIAL_RESUMED_AND_COMPLETED, 0),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_RESUME_STATE_AMBIGUOUS, 19),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_BEFORE_FIRST_MUTATION, 15),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_CANCELLED_WITH_DURABLE_PREFIX, 16),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_EXPECTED_STATE_MISMATCH, 13),
    (PaperControlledRuntimeBoundedSequenceOutcome.SEQUENCE_SINGLE_CYCLE_FAILED, 14),
))
def test_typed_sequence_outcome_exit_mapping(tmp_path, outcome, code):
    paths = manifests(tmp_path)
    prefix = 0 if code in {13, 15, 19} else 1
    fake = FakeResolver(sequence_result(outcome, prefix=prefix))
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert int(result.exit_code) == code
    assert fake.service.calls == 1


def test_target_ownership_migration_and_identity_rejected(tmp_path):
    paths = manifests(tmp_path)
    for fake in (FakeResolver(owned=False), FakeResolver(migration="0008_engine_orchestrator_freshness_retry")):
        result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
        assert result.exit_code == runner.PaperOperatorRuntimeExitCode.TARGET_REJECTED
        assert fake.service.calls == 0


def test_cancellation_before_mutation(tmp_path):
    paths = manifests(tmp_path)
    token = runner.PaperOperatorCooperativeCancellation()
    token.cancel()
    fake = FakeResolver()
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths), cancellation=token)
    assert result.exit_code == runner.PaperOperatorRuntimeExitCode.CANCELLED_BEFORE_MUTATION
    assert fake.resolve_calls == fake.service.calls == 0


def test_signal_adapter_is_cooperative_idempotent_and_does_no_db_work():
    token = runner.PaperOperatorCooperativeCancellation()
    adapter = runner.PaperOperatorSignalAdapter(token)
    assert token.is_cancelled() is False
    adapter._handle(2, None)
    adapter._handle(2, None)
    assert token.is_cancelled() is True


def test_overall_deadline_token_is_cooperative_without_timer_or_thread():
    current = [10.0]
    token = runner.PaperOperatorCooperativeCancellation(monotonic=lambda: current[0])
    token.set_deadline(11.0)
    assert token.is_cancelled() is False
    current[0] = 11.0001
    assert token.is_cancelled() is True


def test_manifest_load_deadline_fails_closed_before_file_read(tmp_path):
    path = _write(tmp_path / "config.json", configuration_mapping())
    with pytest.raises(runner.PaperOperatorManifestError):
        runner.PaperOperatorBoundedRuntimeConfigurationLoader().load(
            path, deadline=time.monotonic() - 1
        )


def test_cleanup_failure_overrides_completed_result(tmp_path):
    paths = manifests(tmp_path)
    fake = FakeResolver(cleanup=False)
    result = service(fake).run(runner.PaperOperatorControlledBoundedRuntimeRunRequest(*paths))
    assert result.exit_code == runner.PaperOperatorRuntimeExitCode.CLEANUP_FAILED
    assert fake.service.calls == fake.cleanup_calls == 1


@pytest.mark.parametrize("argv,code", (
    ((), 10), (("--config", "x", "--request", "y"), 10),
    (("--production",), 20), (("--live",), 20), (("--daemon",), 20),
    (("--database-url", "masked"), 20), (("--password", "masked"), 20),
    (("--unknown",), 10),
))
def test_cli_required_and_forbidden_flags_are_safe(capsys, argv, code):
    assert runner.main(argv) == code
    captured = capsys.readouterr()
    assert captured.out.count("schema_version=") == 1
    assert "masked" not in captured.out + captured.err
    assert "Traceback" not in captured.out + captured.err


def test_cli_success_text_json_and_atomic_result_file(tmp_path, capsys):
    config_path, request_path = manifests(tmp_path)
    for output_format in ("text", "json"):
        fake = FakeResolver()
        argv = ("--config", str(config_path), "--request", str(request_path),
                "--operator-controlled-bounded-run", "--summary-format", output_format)
        assert runner.main(argv, runner=service(fake)) == 0
        captured = capsys.readouterr()
        assert captured.out.count("\n") == 1
        assert captured.err == ""
    destination = (tmp_path.parent / f"safe-result-{tmp_path.name}.json").resolve()
    argv = ("--config", str(config_path), "--request", str(request_path),
            "--operator-controlled-bounded-run", "--summary-format", "json",
            "--result-path", str(destination))
    assert runner.main(argv, runner=service(FakeResolver())) == 0
    assert destination.is_file()
    assert json.loads(destination.read_text(encoding="utf-8"))["exit_code"] == 0
    destination.unlink()


@pytest.mark.parametrize(
    "arguments,expected",
    ((["--production"], 20), (["--operator-controlled-bounded-run"], 10)),
)
def test_real_foreground_cli_process_failure_is_bounded_no_echo(arguments, expected):
    completed = subprocess.run(
        [sys.executable, "-m", "app.engine_paper.operator_bounded_runtime_runner", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
        shell=False,
    )
    assert completed.returncode == expected
    assert completed.stdout.count("\n") == 1
    assert "Traceback" not in completed.stdout + completed.stderr
    assert "database" not in completed.stdout.casefold()


def test_source_has_one_authoritative_call_and_no_business_or_background_dependencies():
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert source.count("resolved.sequence_service.run(authoritative_request)") == 1
    assert "PaperCommandIngestionService" not in source
    assert "PaperOrderExecutionService" not in source
    assert "PaperExitEvaluationService" not in source
    assert ".commit(" not in source
    assert "subprocess" not in source
    assert "while True" not in source
    assert "sleep(" not in source
    assert "DATABASE_URL" not in source
    assert ".env.production.local" not in source
