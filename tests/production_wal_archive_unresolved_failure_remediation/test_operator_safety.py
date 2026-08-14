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


def test_foundation_and_market_data_adapter_unchanged() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", "ba8d19d099d7bafcdc3d643125898a3e7a7240c2"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    forbidden = (
        "0009_", "0010_", "0011_", "app/engine_paper/domain.py",
        "app/engine_paper/repository.py", "app/engine_paper/controlled_worker.py",
        "app/engine_paper/production_market_data.py",
    )
    assert not any(any(marker in path.replace("\\", "/") for marker in forbidden) for path in changed)


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
