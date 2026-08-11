from __future__ import annotations

import itertools
import subprocess

import pytest

from scripts.security_retry_controls import (
    ContainerIdentity,
    SafeParserError,
    TrackedValue,
    ValueClass,
    PolicyResult,
    command_is_forbidden,
    compare_runtime_identities,
    inspect_container_identity,
    inspect_alembic_status,
    inspect_readonly_health_http,
    inspect_tracked_route_counts,
    parse_safe_container_record,
    render_safe_items,
    run_allowlisted_command,
)
from scripts.safe_tracked_file_inspector import main as tracked_inspector_main


FORBIDDEN_COMMANDS = (
    ("docker", "compose", "config"),
    ("docker", "compose", "config", "--environment"),
    ("docker", "exec", "env"),
    ("docker", "exec", "printenv"),
    ("docker", "inspect", "container"),
    ("docker", "inspect", "--format", "{{.Config.Env}}", "container"),
    ("docker", "inspect", "--format", "{{.ContainerConfig.Env}}", "container"),
    ("docker", "container", "inspect", "container"),
    ("docker", "container", "inspect", "--format", "{{.Config.Env}}", "container"),
    (
        "docker",
        "container",
        "inspect",
        "--format",
        "{{.ContainerConfig.Env}}",
        "container",
    ),
)
ALLOWED_COMMANDS = (
    ("docker", "ps", "--format", "{{.Names}}"),
    ("docker", "port", "container"),
    (
        "docker",
        "container",
        "inspect",
        "--format",
        "{{.Id}}|{{.Image}}|{{.RestartCount}}|{{.State.Running}}",
        "container",
    ),
)


@pytest.mark.parametrize(
    ("command", "suffix"),
    tuple(itertools.product(FORBIDDEN_COMMANDS, tuple(range(4)))),
)
def test_forbidden_runtime_inspection_commands_are_denied(
    command: tuple[str, ...],
    suffix: int,
) -> None:
    del suffix
    assert command_is_forbidden(command)
    called = False

    def runner(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError

    result = run_allowlisted_command(command, runner=runner)
    assert not result.succeeded
    assert result.error_class == "FORBIDDEN_COMMAND"
    assert not called


@pytest.mark.parametrize(
    ("command", "repeat"),
    tuple(itertools.product(ALLOWED_COMMANDS, tuple(range(8)))),
)
def test_allowlisted_runtime_inspection_commands_can_execute(
    command: tuple[str, ...],
    repeat: int,
) -> None:
    del repeat

    def runner(*_args, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="safe", stderr="")

    result = run_allowlisted_command(command, runner=runner)
    assert result.succeeded
    assert result.safe_output == "safe"


FAKE_SECRET_VARIANTS = (
    "synthetic-secret",
    "'synthetic quoted secret'",
    '"synthetic double quoted secret"',
    "unicode-\u2603-\u043f\u0440\u0438\u043c\u0435\u0440",
    "first-line\nsecond-line",
    "$(synthetic-command)",
    "`synthetic-command`",
    "percent%2Fencoded%3Avalue",
    "x" * 8192,
)


@pytest.mark.parametrize(
    ("fake_secret", "surface"),
    tuple(itertools.product(FAKE_SECRET_VARIANTS, tuple(range(8)))),
)
def test_fake_secret_never_leaks_from_safe_renderers(
    fake_secret: str,
    surface: int,
) -> None:
    items = [
        SafeParserError("compose.yaml", 0, "services.db.password", "SAFE_ERROR"),
        TrackedValue(
            "compose.yaml",
            0,
            "services.db.password",
            ValueClass.LITERAL_SECRET,
            PolicyResult.FAIL,
        ),
    ]
    if surface % 2:
        items.append(object())
    rendered = render_safe_items(items)
    assert fake_secret not in rendered
    assert "value=" not in rendered
    assert "fingerprint=" not in rendered
    assert "hash=" not in rendered


@pytest.mark.parametrize(
    "record",
    (
        "id|image|0|true|healthy",
        "id|image|1|false|NONE",
        "id|image|999|true|starting",
    ),
)
@pytest.mark.parametrize("ports", ("", "127.0.0.1:8765", "0.0.0.0:5433"))
def test_safe_container_record_accepts_only_allowlisted_fields(
    record: str,
    ports: str,
) -> None:
    parsed = parse_safe_container_record("container", record, ports)
    assert parsed is not None
    assert parsed.name == "container"


@pytest.mark.parametrize(
    "record",
    (
        "too|few|fields",
        "too|many|fields|0|true|healthy",
        "id|image|-1|true|healthy",
        "id|image|not-int|true|healthy",
        "id|image|0|maybe|healthy",
        "id|image|0|true|healthy\nSECRET=value",
    ),
)
def test_safe_container_record_rejects_malformed_output(record: str) -> None:
    assert parse_safe_container_record("container", record, "") is None


def _identity(
    name: str,
    *,
    container_id: str = "container-id",
    image_id: str = "image-id",
    restart_count: int = 0,
) -> ContainerIdentity:
    return ContainerIdentity(
        name,
        container_id,
        image_id,
        restart_count,
        True,
        "healthy",
        "",
    )


@pytest.mark.parametrize("count", tuple(range(1, 25)))
def test_runtime_identity_comparison_detects_no_restart_or_recreate(count: int) -> None:
    before = [_identity(f"container-{index}") for index in range(count)]
    after = [_identity(f"container-{index}") for index in range(count)]
    result = compare_runtime_identities(before, after)
    assert result.identities_complete
    assert result.container_ids_unchanged
    assert result.image_ids_unchanged
    assert result.restart_delta == 0


def test_safe_production_inspector_uses_fixed_narrow_templates() -> None:
    calls: list[tuple[str, ...]] = []

    def runner(command, **_kwargs):
        calls.append(tuple(command))
        if command[:2] == ["docker", "port"]:
            return subprocess.CompletedProcess(command, 0, "127.0.0.1:8765", "")
        if "{{.State.Health.Status}}" in command:
            return subprocess.CompletedProcess(command, 0, "healthy", "")
        return subprocess.CompletedProcess(
            command,
            0,
            "container-id|image-id|0|true",
            "",
        )

    result = inspect_container_identity("container", runner=runner)
    assert result is not None
    assert len(calls) == 3
    assert all(not command_is_forbidden(call) for call in calls)


@pytest.mark.parametrize("repeat", tuple(range(16)))
def test_safe_http_inspector_returns_status_only(repeat: int) -> None:
    del repeat

    class Response:
        status = 200

        def close(self) -> None:
            pass

    result = inspect_readonly_health_http(opener=lambda *_args, **_kwargs: Response())
    assert result.status == 200
    assert "http://127.0.0.1" not in result.render()


def test_safe_route_inspector_has_eighteen_source_get_and_zero_write_routes() -> None:
    result = inspect_tracked_route_counts()
    assert result.get_routes == 18
    assert result.write_routes == 0


@pytest.mark.parametrize("repeat", tuple(range(16)))
def test_safe_alembic_inspector_emits_only_revision(repeat: int) -> None:
    del repeat

    def runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            "0008_engine_orchestrator_freshness_retry (head)",
            "synthetic-secret-that-must-not-render",
        )

    result = inspect_alembic_status("container", runner=runner)
    assert result.revision == "0008_engine_orchestrator_freshness_retry"
    assert "synthetic-secret" not in result.render()


def test_tracked_inspector_denies_protected_binding_before_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    read_calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal read_calls
        read_calls += 1
        raise AssertionError

    monkeypatch.setattr("pathlib.Path.read_text", forbidden)
    monkeypatch.setattr("pathlib.Path.open", forbidden)
    assert tracked_inspector_main([".env.production.local", "--policy"]) == 2
    assert read_calls == 0
