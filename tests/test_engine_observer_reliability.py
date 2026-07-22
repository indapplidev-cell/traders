from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.engine_observation.observer_reliability import (
    ArtifactStore,
    ArtifactWriteError,
    CollectorResult,
    CollectorStatus,
    GapCause,
    HeartbeatState,
    InstanceLock,
    LOCK_SCHEMA,
    LockMetadataMismatch,
    MonotonicSchedule,
    ObserverAlreadyRunning,
    ObserverConfig,
    ProcessIdentity,
    ReliableObserver,
    atomic_write_json,
    audit_jsonl,
    classify_gap,
    command_hash,
    redact,
)


UTC = timezone.utc


class SuccessCollector:
    name = "success"

    def collect(self):
        return CollectorResult(self.name, CollectorStatus.SUCCESS, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", 1, {"ok": True})


class FailedCollector:
    name = "failed"

    def __init__(self, status=CollectorStatus.TIMEOUT):
        self.status = status

    def collect(self):
        return CollectorResult(self.name, self.status, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", 1, None, "TEST_FAILURE", "retryable", True)


class ExplodingCollector:
    name = "exploding"

    def collect(self):
        raise RuntimeError("password=do-not-persist")


class FakeInspector:
    def __init__(self, identity: ProcessIdentity):
        self.identity = identity

    def inspect(self, pid: int) -> ProcessIdentity:
        return self.identity


def config(path: Path, *, sample=0.03, heartbeat=0.005, degraded=2) -> ObserverConfig:
    return ObserverConfig(path, sampling_interval_seconds=sample, heartbeat_interval_seconds=heartbeat,
                          allowed_jitter_seconds=sample, degraded_after_failures=degraded)


def lock_metadata(path: Path, *, pid=999999, instance="old", active=True):
    return {
        "schema_version": LOCK_SCHEMA,
        "observer_instance_id": instance,
        "os_pid": pid,
        "parent_pid": 1,
        "process_started_at_utc": "2026-01-01T00:00:00Z",
        "hostname": "test",
        "soak_directory": str(path.resolve()),
        "command_line_hash": command_hash(["observer"]),
        "active": active,
    }


def test_config_enforces_heartbeat_faster_than_sampling(tmp_path):
    with pytest.raises(ValueError, match="heartbeat_interval"):
        ObserverConfig(tmp_path, sampling_interval_seconds=30, heartbeat_interval_seconds=11)


def test_first_instance_acquires_and_releases_lock(tmp_path):
    lock = InstanceLock(tmp_path / "observer.lock", lock_metadata(tmp_path, instance="new"))
    lock.acquire()
    assert lock.handle is not None
    lock.release()
    saved = json.loads((tmp_path / "observer.lock").read_text())
    assert saved["active"] is False


def test_second_instance_is_rejected_while_os_lock_is_held(tmp_path):
    first = InstanceLock(tmp_path / "observer.lock", lock_metadata(tmp_path, instance="one"))
    first.acquire()
    try:
        second = InstanceLock(tmp_path / "observer.lock", lock_metadata(tmp_path, instance="two"))
        with pytest.raises(ObserverAlreadyRunning):
            second.acquire()
    finally:
        first.release()


def test_stale_lock_recovers_only_when_process_absent(tmp_path):
    path = tmp_path / "observer.lock"
    path.write_text(json.dumps(lock_metadata(tmp_path)), encoding="utf-8")
    lock = InstanceLock(path, lock_metadata(tmp_path, instance="new"), FakeInspector(ProcessIdentity(False)))
    lock.acquire()
    try:
        assert lock.recovered_metadata["observer_instance_id"] == "old"
    finally:
        lock.release()


def test_crash_leaves_active_metadata_and_restart_records_abrupt_termination(tmp_path):
    crashed = InstanceLock(tmp_path / "observer.lock", lock_metadata(tmp_path, instance="crashed"))
    crashed.acquire()
    crashed.handle.close()  # operating system releases the lock; metadata intentionally stays active
    crashed.handle = None
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()], process_inspector=FakeInspector(ProcessIdentity(False)))
    assert observer.run(maximum_samples=1) == 0
    incidents = [json.loads(line) for line in (tmp_path / "incident_log.jsonl").read_text().splitlines()]
    assert any(item.get("event") == "ABRUPTLY_TERMINATED" for item in incidents)


def test_live_process_metadata_is_never_replaced(tmp_path):
    path = tmp_path / "observer.lock"
    prior = lock_metadata(tmp_path)
    path.write_text(json.dumps(prior), encoding="utf-8")
    lock = InstanceLock(path, lock_metadata(tmp_path, instance="new"), FakeInspector(ProcessIdentity(True)))
    with pytest.raises(ObserverAlreadyRunning):
        lock.acquire()
    assert json.loads(path.read_text())["observer_instance_id"] == "old"


def test_lock_metadata_mismatch_fails_closed(tmp_path):
    path = tmp_path / "observer.lock"
    bad = lock_metadata(tmp_path)
    bad["schema_version"] = "UNKNOWN"
    path.write_text(json.dumps(bad), encoding="utf-8")
    lock = InstanceLock(path, lock_metadata(tmp_path, instance="new"), FakeInspector(ProcessIdentity(False)))
    with pytest.raises(LockMetadataMismatch):
        lock.acquire()


def test_atomic_heartbeat_is_complete_json(tmp_path):
    path = tmp_path / "observer_heartbeat.json"
    for sequence in range(100):
        atomic_write_json(path, {"sequence": sequence, "payload": "x" * 100})
        assert json.loads(path.read_text())["sequence"] == sequence
    assert not list(tmp_path.glob("*.tmp"))


def test_observer_writes_worker_pid_process_record_and_heartbeat(tmp_path):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()])
    assert observer.run(maximum_samples=1) == 0
    assert int((tmp_path / "observer.pid").read_text()) == os.getpid()
    process = json.loads((tmp_path / "observer_process.json").read_text())
    heartbeat = json.loads((tmp_path / "observer_heartbeat.json").read_text())
    assert process["os_pid"] == os.getpid() and process["state"] == "STOPPED"
    assert heartbeat["schema_version"] == "OBSERVER_HEARTBEAT/1.0"
    assert heartbeat["state"] == HeartbeatState.STOPPED
    assert heartbeat["observer_instance_id"] == process["observer_instance_id"]


def test_heartbeat_history_updates_during_partial_collection(tmp_path):
    observer = ReliableObserver(config(tmp_path, sample=0.06, heartbeat=0.005), [SuccessCollector(), FailedCollector()])
    assert observer.run(maximum_samples=2) == 0
    lines = (tmp_path / "heartbeat_history.jsonl").read_text().splitlines()
    assert len(lines) >= 3
    assert all(json.loads(line)["schema_version"] for line in lines)
    sample = json.loads((tmp_path / "observations.jsonl").read_text().splitlines()[1])
    assert sample["status"] == "PARTIAL"


def test_degraded_after_configured_consecutive_failures(tmp_path):
    observer = ReliableObserver(config(tmp_path, degraded=1), [FailedCollector()])
    observer.run(maximum_samples=1)
    states = [json.loads(line)["state"] for line in (tmp_path / "heartbeat_history.jsonl").read_text().splitlines()]
    assert "DEGRADED" in states


def test_heartbeat_continues_while_bounded_collector_waits(tmp_path):
    from app.engine_observation.observer_reliability import CommandCollector
    slow = CommandCollector("slow", [sys.executable, "-c", "import time; time.sleep(1)"], timeout_seconds=0.15)
    observer = ReliableObserver(config(tmp_path, sample=0.3, heartbeat=0.01), [slow])
    assert observer.run(maximum_samples=1) == 0
    lines = (tmp_path / "heartbeat_history.jsonl").read_text().splitlines()
    assert len(lines) >= 8


def test_controlled_stop_persists_stopping_stopped_and_summary(tmp_path):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()])
    assert observer.run(maximum_samples=1) == 0
    states = [json.loads(line)["state"] for line in (tmp_path / "heartbeat_history.jsonl").read_text().splitlines()]
    assert "STARTING" in states and "STOPPING" in states and states[-1] == "STOPPED"
    summary = json.loads((tmp_path / "observer_final_state.json").read_text())
    assert summary["exit_code"] == 0 and summary["samples_successful"] == 1
    assert json.loads((tmp_path / "observer.lock").read_text())["active"] is False


def test_instance_id_changes_and_run_id_is_preserved_across_restart(tmp_path):
    one = ReliableObserver(config(tmp_path), [SuccessCollector()])
    one.run(maximum_samples=1)
    two = ReliableObserver(config(tmp_path), [SuccessCollector()])
    two.run(maximum_samples=1)
    assert one.instance_id != two.instance_id
    assert one.run_id == two.run_id
    assert (tmp_path / "observer_restart_report.md").exists()
    finals = [json.loads(line) for line in (tmp_path / "observer_final_states.jsonl").read_text().splitlines()]
    assert {item["observer_instance_id"] for item in finals} == {one.instance_id, two.instance_id}


def test_monotonic_schedule_has_no_cumulative_drift():
    schedule = MonotonicSchedule(10, 100, datetime(2026, 1, 1, tzinfo=UTC))
    assert schedule.advance_after(103).next_due_monotonic == 110
    assert schedule.advance_after(117).next_due_monotonic == 120
    assert schedule.advance_after(129).next_due_monotonic == 130


def test_overrun_skips_missed_slots_without_burst():
    schedule = MonotonicSchedule(10, 100, datetime(2026, 1, 1, tzinfo=UTC))
    advance = schedule.advance_after(135)
    assert advance.missed_interval_count == 3
    assert advance.next_due_monotonic == 140


def test_wall_clock_adjustment_does_not_change_monotonic_due():
    schedule = MonotonicSchedule(10, 100, datetime(2026, 1, 1, tzinfo=UTC))
    due = schedule.advance_after(101)
    assert due.next_due_monotonic == 110
    assert due.next_due_utc == datetime(2026, 1, 1, 0, 0, 10, tzinfo=UTC)


@pytest.mark.parametrize(("kwargs", "expected"), [
    ({"monotonic_elapsed": 120, "wall_elapsed": 120}, GapCause.SYSTEM_SUSPEND),
    ({"monotonic_elapsed": 10, "wall_elapsed": 3600}, GapCause.HOST_CLOCK_ADJUSTMENT),
    ({"monotonic_elapsed": 10, "wall_elapsed": 10, "collector_overrun": True}, GapCause.COLLECTOR_OVERRUN),
    ({"monotonic_elapsed": 10, "wall_elapsed": 10, "controlled_restart": True}, GapCause.CONTROLLED_RESTART),
])
def test_gap_classification_is_typed(kwargs, expected):
    assert classify_gap(**kwargs) == expected


def test_one_collector_exception_does_not_stop_loop_and_is_redacted(tmp_path):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector(), ExplodingCollector()])
    assert observer.run(maximum_samples=2) == 0
    records = [json.loads(line) for line in (tmp_path / "observations.jsonl").read_text().splitlines()]
    samples = [item for item in records if item["record_type"] == "ObserverSample"]
    assert len(samples) == 2 and all(item["status"] == "PARTIAL" for item in samples)
    assert "do-not-persist" not in (tmp_path / "observations.jsonl").read_text()


def test_jsonl_one_utf8_newline_terminated_object_per_line(tmp_path):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()])
    observer.run(maximum_samples=2)
    for name in ArtifactStore.COMPATIBLE_JSONL:
        raw = (tmp_path / name).read_bytes()
        assert raw.endswith(b"\n")
        for line in raw.splitlines():
            value = json.loads(line.decode("utf-8"))
            assert "schema_version" in value and "observer_instance_id" in value


def test_audit_reports_zero_corruption_and_duplicates(tmp_path):
    ReliableObserver(config(tmp_path), [SuccessCollector()]).run(maximum_samples=2)
    audit = audit_jsonl(tmp_path)
    assert audit["corrupt_lines"] == 0
    assert audit["duplicate_identities"] == 0


def test_old_jsonl_record_remains_readable_by_additive_parser(tmp_path):
    (tmp_path / "observations.jsonl").write_text('{"observed_at":"2026-01-01T00:00:00Z","event":"OLD"}\n', encoding="utf-8")
    ReliableObserver(config(tmp_path), [SuccessCollector()]).run(maximum_samples=1)
    values = [json.loads(line) for line in (tmp_path / "observations.jsonl").read_text().splitlines()]
    assert values[0]["event"] == "OLD"
    assert any(item.get("record_type") == "ObserverSample" for item in values)


def test_sequence_identity_is_strictly_increasing_per_instance(tmp_path):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()])
    observer.run(maximum_samples=3)
    values = [json.loads(line) for line in (tmp_path / "observations.jsonl").read_text().splitlines()]
    sequences = [item["sample_sequence"] for item in values if item["record_type"] == "ObserverSample"]
    assert sequences == [1, 2, 3]


def test_gap_record_has_exact_missed_count_and_maximum(tmp_path):
    observer = ReliableObserver(config(tmp_path, sample=10, heartbeat=1), [SuccessCollector()])
    observer.start()
    try:
        previous = datetime(2026, 1, 1, tzinfo=UTC)
        observer._record_gap(4, previous, datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC), 2, GapCause.COLLECTOR_OVERRUN)
        event = json.loads((tmp_path / "incident_log.jsonl").read_text().splitlines()[-1])
        assert event["missed_interval_count"] == 2
        assert event["actual_gap_seconds"] == 30
        assert event["cause_code"] == "COLLECTOR_OVERRUN"
        assert observer.counters.max_sampling_gap_seconds == 30
    finally:
        observer.request_stop()
        observer._finalize("TEST", 0)


@pytest.mark.parametrize("value", [
    {"POSTGRES_PASSWORD": "secret"},
    {"nested": [{"authorization": "Bearer abc.def"}]},
    "postgresql://user:secret@localhost/db",
    "Authorization: Bearer abcdef",
    "password=hunter2",
])
def test_redaction_removes_credentials(value):
    rendered = json.dumps(redact(value))
    for secret in ("secret", "abc.def", "abcdef", "hunter2"):
        assert secret not in rendered
    assert "REDACTED" in rendered


def test_command_timeout_isolated(tmp_path):
    from app.engine_observation.observer_reliability import CommandCollector
    collector = CommandCollector("timeout", [sys.executable, "-c", "import time; time.sleep(2)"], timeout_seconds=0.01)
    result = collector.collect()
    assert result.status == CollectorStatus.TIMEOUT
    assert result.retryable is True


def test_cli_second_process_is_rejected_and_owner_continues(tmp_path):
    script = Path(__file__).parents[1] / "scripts" / "engine_observer_reliability.py"
    owner = subprocess.Popen([sys.executable, str(script), "--soak-directory", str(tmp_path), "--no-docker",
                              "--sampling-interval-seconds", "0.3", "--heartbeat-interval-seconds", "0.05",
                              "--maximum-runtime-seconds", "5"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(100):
            if (tmp_path / "observer.lock").exists() and (tmp_path / "observer_heartbeat.json").exists():
                break
            threading.Event().wait(0.01)
        second = subprocess.run([sys.executable, str(script), "--soak-directory", str(tmp_path), "--no-docker",
                                 "--sampling-interval-seconds", "0.3", "--heartbeat-interval-seconds", "0.05",
                                 "--maximum-samples", "1"], capture_output=True, text=True, timeout=5)
        assert second.returncode == 4
        assert "ACTIVE_OBSERVER_LOCK" in second.stderr
        assert owner.poll() is None
    finally:
        subprocess.run([sys.executable, str(script), "--soak-directory", str(tmp_path), "--request-stop"], check=True, capture_output=True)
        owner.wait(timeout=5)


def test_stop_request_file_causes_clean_stop(tmp_path):
    script = Path(__file__).parents[1] / "scripts" / "engine_observer_reliability.py"
    owner = subprocess.Popen([sys.executable, str(script), "--soak-directory", str(tmp_path), "--no-docker",
                              "--sampling-interval-seconds", "0.3", "--heartbeat-interval-seconds", "0.05"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for _ in range(100):
        if (tmp_path / "observer_heartbeat.json").exists():
            break
        threading.Event().wait(0.01)
    stop = subprocess.run([sys.executable, str(script), "--soak-directory", str(tmp_path), "--request-stop"], capture_output=True, text=True, timeout=5)
    assert stop.returncode == 0
    assert owner.wait(timeout=5) == 0
    assert json.loads((tmp_path / "observer_heartbeat.json").read_text())["state"] == "STOPPED"


def test_database_collector_failure_is_typed_and_redacted():
    from app.engine_observation.observer_reliability import ReadOnlyDatabaseCollector
    result = ReadOnlyDatabaseCollector("postgresql://user:topsecret@127.0.0.1:1/missing", timeout_seconds=0.1).collect()
    assert result.status in {CollectorStatus.TIMEOUT, CollectorStatus.UNAVAILABLE}
    assert "topsecret" not in (result.error_message_redacted or "")


def test_fatal_internal_artifact_error_exits_nonzero_and_releases_lock(tmp_path, monkeypatch):
    observer = ReliableObserver(config(tmp_path), [SuccessCollector()])
    def fail_append(*args, **kwargs):
        raise ArtifactWriteError("synthetic write failure")
    monkeypatch.setattr(observer.store, "append", fail_append)
    assert observer.run(maximum_samples=1) == 2
    assert json.loads((tmp_path / "observer.lock").read_text())["active"] is False
    fallback = list(observer.config.fallback_directory.glob(f"observer_failure_{observer.instance_id}.json"))
    assert fallback


def test_no_database_schema_or_migration_file_is_introduced():
    root = Path(__file__).parents[1]
    changed = subprocess.run(["git", "diff", "--name-only", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.splitlines()
    assert not any(path.startswith("alembic/") for path in changed)
