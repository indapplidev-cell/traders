from __future__ import annotations

import json
import os
from pathlib import Path
import threading

import pytest

from traders_ml.parameter_sweep.artifact_writer import (
    ArtifactWriteError, ArtifactWriter, DurableResultWriter,
    is_transient_windows_filesystem_error,
)
from traders_ml.parameter_sweep.state import StatusStore, SweepRunStatus


def _permission(code: int) -> PermissionError:
    error = PermissionError(code, "injected Windows sharing violation")
    error.winerror = code
    return error


@pytest.mark.parametrize("failures", (1, 3))
def test_status_replace_transient_failures_are_retried(tmp_path, monkeypatch, failures):
    target = tmp_path / "STATUS.json"
    real_replace = os.replace
    calls = 0

    def flaky(source, destination):
        nonlocal calls
        calls += 1
        if calls <= failures:
            raise _permission(32)
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", flaky)
    writer = ArtifactWriter(retry_delays=(0, 0, 0, 0), sleeper=lambda _: None)
    store = StatusStore(target, SweepRunStatus(run_id="status"), writer=writer)
    store.update(state="RUNNING_CONFIG")
    assert json.loads(target.read_text())["state"] == "RUNNING_CONFIG"
    assert store.last_write_warning is None


def test_status_persistent_failure_is_nonfatal_and_structured(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(_permission(5)))
    store = StatusStore(
        tmp_path / "STATUS.json", SweepRunStatus(run_id="status"),
        writer=ArtifactWriter(retry_delays=(0, 0), sleeper=lambda _: None),
    )
    store.update(state="RUNNING_CONFIG")
    assert store.status.state == "RUNNING_CONFIG"
    assert store.last_write_warning["attempts"] == 2
    assert store.last_write_warning["winerror"] == 5
    assert store.last_write_warning["operation"] == "status_replace"


@pytest.mark.parametrize("code", (5, 32, 33))
def test_windows_permission_codes_are_transient(code):
    assert is_transient_windows_filesystem_error(_permission(code))


def test_atomic_replace_reconciles_ambiguous_completion(tmp_path, monkeypatch):
    target = tmp_path / "CHECKPOINT.json"
    real_replace = os.replace
    called = False

    def completed_then_raised(source, destination):
        nonlocal called
        real_replace(source, destination)
        if not called:
            called = True
            raise _permission(32)

    monkeypatch.setattr(os, "replace", completed_then_raised)
    ArtifactWriter(retry_delays=(0, 0), sleeper=lambda _: None).atomic_json(
        target, {"evaluated_count": 7}, operation="checkpoint_replace",
    )
    assert json.loads(target.read_text()) == {"evaluated_count": 7}


@pytest.mark.parametrize("failures", (1, 3))
def test_checkpoint_replace_transient_failures_are_retried(tmp_path, monkeypatch, failures):
    target = tmp_path / "CHECKPOINT.json"
    real_replace = os.replace
    calls = 0

    def flaky(source, destination):
        nonlocal calls
        calls += 1
        if calls <= failures:
            raise _permission(33)
        real_replace(source, destination)

    monkeypatch.setattr(os, "replace", flaky)
    ArtifactWriter(retry_delays=(0, 0, 0, 0), sleeper=lambda _: None).atomic_json(
        target, {"evaluated_count": 8}, operation="checkpoint_replace",
    )
    assert json.loads(target.read_text())["evaluated_count"] == 8


def test_persistent_checkpoint_failure_preserves_previous_checkpoint(tmp_path, monkeypatch):
    target = tmp_path / "CHECKPOINT.json"
    target.write_text('{"evaluated_count": 4}', encoding="utf-8")
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(_permission(33)))
    with pytest.raises(ArtifactWriteError) as captured:
        ArtifactWriter(retry_delays=(0, 0, 0), sleeper=lambda _: None).atomic_json(
            target, {"evaluated_count": 5}, operation="checkpoint_replace",
        )
    assert json.loads(target.read_text())["evaluated_count"] == 4
    assert captured.value.as_dict()["winerror"] == 33
    assert captured.value.as_dict()["path"] == str(target)


def test_temp_unlink_permission_error_does_not_hide_primary_failure(tmp_path, monkeypatch):
    target = tmp_path / "STATUS.json"
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(ValueError("primary")))
    original_unlink = Path.unlink

    def denied_unlink(path, *args, **kwargs):
        if path.suffix == ".tmp":
            raise _permission(5)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", denied_unlink)
    with pytest.raises(ValueError, match="primary"):
        ArtifactWriter(retry_delays=(0,), sleeper=lambda _: None).atomic_json(target, {})


def test_result_writer_recovers_after_jsonl_durable_csv_failure(tmp_path):
    fields = ["result_index", "config_hash", "stage", "result_status", "validation_expectancy", "validation_drawdown", "validation_trades", "parameters_json"]
    delegate = ArtifactWriter(retry_delays=(0,), sleeper=lambda _: None)

    class FailCsvOnce(ArtifactWriter):
        def __init__(self):
            super().__init__(retry_delays=(0,), sleeper=lambda _: None)
            self.failed = False

        def atomic_text(self, path, content, *, operation="replace"):
            if path.name == "RESULTS.csv" and not self.failed:
                self.failed = True
                raise ArtifactWriteError(path, operation, 1, 32, _permission(32))
            delegate.atomic_text(path, content, operation=operation)

    item = {
        "run_id": "r", "result_index": 0, "config_hash": "h", "stage": "S1",
        "result_status": "ACCEPTED", "validation": {"trade_count": 1},
        "parameters": {"x": 1},
    }
    writer = DurableResultWriter(tmp_path, fields, writer=FailCsvOnce())
    with pytest.raises(ArtifactWriteError):
        writer.append(item)
    assert writer.append(item) is False
    assert len(writer.read_all()) == 1
    assert len((tmp_path / "RESULTS.csv").read_text().splitlines()) == 2


def test_writer_only_concurrency_stress_500_cycles(tmp_path):
    target = tmp_path / "STATUS.json"
    writer = ArtifactWriter(retry_delays=(0, 0), sleeper=lambda _: None)

    def worker(start: int) -> None:
        for index in range(start, 500, 5):
            writer.atomic_json(target, {"index": index}, operation="status_replace")

    threads = [threading.Thread(target=worker, args=(offset,)) for offset in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert isinstance(json.loads(target.read_text())["index"], int)
    assert list(tmp_path.glob("*.tmp")) == []
