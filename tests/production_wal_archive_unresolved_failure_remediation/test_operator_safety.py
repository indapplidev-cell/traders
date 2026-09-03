from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import production_backup
from scripts import production_wal_archive_remediation as remediation


def test_remediation_source_has_no_protected_binding_or_forbidden_inspection() -> None:
    source = Path(remediation.__file__).read_text(encoding="utf-8")
    for forbidden in (
        ".env.production.local", "DATABASE_URL", "TRADERS_ML_POSTGRES_PASSWORD",
        "TRADERS_READONLY_API_DATABASE_URL", "docker compose config", ".Config.Env",
        ".ContainerConfig.Env", "printenv", "docker exec env", "postgresql://",
    ):
        assert forbidden not in source


def test_retry_timeout_is_bounded() -> None:
    with pytest.raises(production_backup.OperationFailure, match="INVALID_BOUNDED_RETRY_TIMEOUT"):
        remediation.bounded_retry(Path("unused"), timeout_seconds=601)


def test_fixed_inspection_directories_only() -> None:
    with pytest.raises(production_backup.OperationFailure, match="UNAPPROVED"):
        remediation._container_names("/etc", "*")


def test_no_restart_recreate_or_switch_commands_in_remediator() -> None:
    source = Path(remediation.__file__).read_text(encoding="utf-8")
    assert "pg_switch_wal" not in source
    assert "docker compose down" not in source
    assert '"restart"' not in source
    assert '"rm", "-f", CONTAINER' not in source


def test_host_ack_helper_preserves_validated_protocol_and_daemon_is_bounded() -> None:
    command = remediation.HOST_ACK_ARCHIVE_COMMAND
    assert "/var/lib/postgresql/wal_export/%f" in command
    assert "cmp -s" in command and ".ack" in command and "300" in command
    with pytest.raises(production_backup.OperationFailure, match="INVALID_ACK_DAEMON_INTERVAL"):
        remediation.run_host_ack_daemon(Path("unused"), interval_seconds=31)


def test_daemon_state_publication_retries_transient_permission_error(
    tmp_path, monkeypatch
) -> None:
    calls = 0

    def transient_write(_path, _payload):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise PermissionError(5, "access denied")

    monkeypatch.setattr(remediation, "atomic_json_write", transient_write)
    monkeypatch.setattr(remediation.time, "sleep", lambda _seconds: None)

    assert remediation._publish_daemon_state(
        tmp_path / "state.json", {}, attempts=3, retry_seconds=0.01
    )
    assert calls == 3


def test_daemon_state_publication_exhaustion_does_not_terminate_owner(
    tmp_path, monkeypatch
) -> None:
    def denied(_path, _payload):
        raise PermissionError(5, "access denied")

    monkeypatch.setattr(remediation, "atomic_json_write", denied)
    monkeypatch.setattr(remediation.time, "sleep", lambda _seconds: None)

    assert not remediation._publish_daemon_state(
        tmp_path / "state.json", {}, attempts=2, retry_seconds=0.01
    )


def test_daemon_cycle_publishes_post_sync_zero_backlog(monkeypatch) -> None:
    before = type("Snapshot", (), {
        "export_backlog_count": 1,
        "pending_archive_status_count": 1,
    })()
    after = type("Snapshot", (), {
        "export_backlog_count": 0,
        "pending_archive_status_count": 0,
    })()
    monkeypatch.setattr(remediation, "capture_snapshot", lambda _root: before)
    monkeypatch.setattr(
        remediation, "sync_wal", lambda _root: {"published_segment_count": 1}
    )
    monkeypatch.setattr(
        remediation,
        "bounded_retry",
        lambda _root, timeout_seconds: (after, 0),
    )

    payload = remediation._host_ack_daemon_cycle(Path("unused"), process_id=4321)

    assert payload["process_id"] == 4321
    assert payload["published_segment_count_last_cycle"] == 1
    assert payload["export_backlog_count"] == 0
    assert payload["pending_archive_status_count"] == 0


def test_daemon_lock_recovers_only_proven_dead_owner(tmp_path, monkeypatch) -> None:
    lock = tmp_path / "wal_ack_daemon.pid"
    lock.write_text("4321", encoding="ascii")
    monkeypatch.setattr(remediation, "_process_is_alive", lambda _pid: False)

    descriptor = remediation._acquire_daemon_lock(lock)
    try:
        assert descriptor >= 0
        assert lock.read_text(encoding="ascii") == str(remediation.os.getpid())
    finally:
        remediation.os.close(descriptor)


def test_windows_daemon_docker_calls_do_not_create_console(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(remediation.os, "name", "nt")
    monkeypatch.setattr(remediation.subprocess, "run", fake_run)

    assert remediation._run(["docker", "version"]) == "ok"
    assert production_backup.run(["docker", "version"]).stdout == "ok"
    assert calls[0]["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert calls[1]["creationflags"] == subprocess.CREATE_NO_WINDOW


def test_daemon_lock_never_replaces_live_owner(tmp_path, monkeypatch) -> None:
    lock = tmp_path / "wal_ack_daemon.pid"
    lock.write_text("4321", encoding="ascii")
    monkeypatch.setattr(remediation, "_process_is_alive", lambda _pid: True)

    with pytest.raises(production_backup.OperationFailure, match="ACK_DAEMON_ALREADY_RUNNING"):
        remediation._acquire_daemon_lock(lock)
    assert lock.read_text(encoding="ascii") == "4321"


def test_windows_autostart_is_bounded_and_verified(tmp_path, monkeypatch) -> None:
    archive = tmp_path / "wal_archive"
    archive.mkdir()
    python = tmp_path / "python.exe"
    python.write_bytes(b"")
    (tmp_path / "pythonw.exe").write_bytes(b"")
    calls: list[list[str]] = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(remediation.os, "name", "nt")
    monkeypatch.setattr(remediation, "SAFE_ROOT", tmp_path)
    monkeypatch.setattr(remediation.sys, "executable", str(python))
    monkeypatch.setattr(remediation.subprocess, "run", fake_run)

    assert remediation.install_windows_daemon_autostart(tmp_path, interval_seconds=3)
    assert calls[0][0:4] == ["schtasks.exe", "/Create", "/TN", remediation.WINDOWS_AUTOSTART_TASK]
    assert calls[1] == ["schtasks.exe", "/Query", "/TN", remediation.WINDOWS_AUTOSTART_TASK]
    assert "ONLOGON" in calls[0]
    assert "LIMITED" in calls[0]


def test_windows_autostart_falls_back_to_current_user_startup(tmp_path, monkeypatch) -> None:
    archive = tmp_path / "wal_archive"
    archive.mkdir()
    python = tmp_path / "python.exe"
    python.write_bytes(b"")
    (tmp_path / "pythonw.exe").write_bytes(b"")
    appdata = tmp_path / "appdata"
    startup = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup.mkdir(parents=True)

    monkeypatch.setattr(remediation.os, "name", "nt")
    monkeypatch.setattr(remediation, "SAFE_ROOT", tmp_path)
    monkeypatch.setattr(remediation.sys, "executable", str(python))
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(
        remediation.subprocess, "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 5, "", "denied"),
    )

    assert remediation.install_windows_daemon_autostart(tmp_path, interval_seconds=3)
    launcher = startup / remediation.WINDOWS_STARTUP_LAUNCHER
    content = launcher.read_text(encoding="utf-8")
    assert "pythonw.exe" in content
    assert "production_wal_archive_remediation.py" in content
    assert "--interval-seconds 3" in content
    assert "WScript.Shell" in content


def test_remediator_does_not_depend_on_paper_foundation_or_market_data_adapter() -> None:
    """Keep the WAL repair isolated without relying on a stale Git baseline.

    The original assertion compared the entire current repository with the
    historical remediation commit.  Legitimate later PAPER work therefore
    made this test fail even when the WAL remediator itself stayed isolated.
    """

    source = Path(remediation.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "app.engine_paper.domain",
        "app.engine_paper.repository",
        "app.engine_paper.controlled_worker",
        "app.engine_paper.production_market_data",
        "alembic.versions.0009_",
        "alembic.versions.0010_",
        "alembic.versions.0011_",
    ):
        assert forbidden not in source


@pytest.mark.parametrize(("existing", "incoming", "expected_error"), (
    (b"same", b"same", None),
    (b"original", b"different", "WAL_ARCHIVE_CONFLICT"),
))
def test_duplicate_archive_is_idempotent_only_for_identical_bytes(
    tmp_path, monkeypatch, existing, incoming, expected_error
) -> None:
    wal = "000000010000000000000001"
    archive = tmp_path / "wal_archive"
    archive.mkdir()
    (archive / wal).write_bytes(existing)
    monkeypatch.setattr(production_backup, "validate_root", lambda _root: None)

    def fake_run(command, **_kwargs):
        if command[:3] == ["docker", "cp", f"{production_backup.CONTAINER}:/var/lib/postgresql/wal_export/{wal}"]:
            Path(command[-1]).write_bytes(incoming)
            return subprocess.CompletedProcess(command, 0, "", "")
        if "last_archived_wal" in " ".join(command):
            return subprocess.CompletedProcess(command, 0, "\n", "")
        if "for f in" in " ".join(command):
            return subprocess.CompletedProcess(command, 0, wal + "\n", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(production_backup, "run", fake_run)
    if expected_error:
        with pytest.raises(production_backup.OperationFailure, match=expected_error):
            production_backup.sync_wal(tmp_path)
        assert (archive / wal).read_bytes() == existing
    else:
        result = production_backup.sync_wal(tmp_path)
        assert result["published_segment_count"] == 1
        assert (archive / wal).read_bytes() == existing
