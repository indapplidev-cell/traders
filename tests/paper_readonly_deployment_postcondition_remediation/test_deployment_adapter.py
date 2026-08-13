from __future__ import annotations

import json
import subprocess

import pytest

from app.engine_paper.production_preparation_backend import (
    READONLY_EXPECTED_GET_ROUTES,
    READONLY_LEGACY_ROUTES,
    READONLY_PAPER_ROUTES,
    READONLY_STATIC_PAPER_HTTP_PATHS,
    PaperPreparationAdapterError,
    PaperPreparationDeploymentAdapter,
    ReadonlyRuntimeAcceptance,
)


IDENTITY = "sha256:" + "a" * 64
OTHER_IDENTITY = "sha256:" + "b" * 64


def acceptance(
    *,
    identity: str = IDENTITY,
    healthy: bool = True,
    routes=frozenset(READONLY_EXPECTED_GET_ROUTES),
    writes: int = 0,
    legacy_statuses=None,
    paper_statuses=None,
) -> ReadonlyRuntimeAcceptance:
    return ReadonlyRuntimeAcceptance(
        identity,
        healthy,
        frozenset(routes),
        writes,
        legacy_statuses or (200,) * len(READONLY_LEGACY_ROUTES),
        paper_statuses or (200,) * len(READONLY_STATIC_PAPER_HTTP_PATHS),
    )


def marker_payload(identity: str = IDENTITY) -> dict[str, object]:
    return {
        "deployment": "NARROW",
        "service": "readonly-api",
        "schema": 2,
        "source_identity": identity,
        "runtime_health": "PASS",
        "get_routes": len(READONLY_EXPECTED_GET_ROUTES),
        "write_routes": 0,
        "legacy_endpoints": len(READONLY_LEGACY_ROUTES),
        "paper_endpoints": len(READONLY_PAPER_ROUTES),
    }


def adapter(tmp_path, probe, **kwargs):
    return PaperPreparationDeploymentAdapter(
        tmp_path,
        source_identity_provider=lambda: IDENTITY,
        runtime_probe=lambda _: probe[0],
        **kwargs,
    )


def test_stale_nine_route_runtime_overrides_ready_marker_then_current_runtime_is_accepted(tmp_path):
    marker = tmp_path / "readonly-api.narrow.json"
    marker.write_text(
        '{"deployment":"NARROW","service":"readonly-api","write_routes":0}',
        encoding="utf-8",
    )
    stale = acceptance(
        routes=frozenset(READONLY_LEGACY_ROUTES),
        paper_statuses=(404,) * len(READONLY_STATIC_PAPER_HTTP_PATHS),
    )
    probe = [stale]
    deployment = adapter(tmp_path, probe)

    assert len(stale.get_routes) == 9
    assert stale.write_route_count == 0
    assert len(READONLY_PAPER_ROUTES) == 9
    assert not deployment.readonly_api_narrow_ready()

    probe[0] = acceptance()
    result = deployment.deploy_readonly_api_narrow()
    assert result.changed and result.ready
    assert deployment.readonly_api_narrow_ready()
    published = json.loads(marker.read_text(encoding="utf-8"))
    assert published == marker_payload()


class Runner:
    def __init__(self, *, fail_build=False, fail_start=False):
        self.calls = []
        self.fail_build = fail_build
        self.fail_start = fail_start

    def __call__(self, command, **kwargs):
        self.calls.append((tuple(command), kwargs))
        failed = (self.fail_build and "build" in command) or (self.fail_start and "up" in command)
        return subprocess.CompletedProcess(command, 1 if failed else 0, stdout="", stderr="")


def docker_adapter(tmp_path, probe, runner):
    compose = tmp_path / "compose.yaml"
    compose.write_text("services: {readonly-api: {image: isolated}}\n", encoding="utf-8")
    return PaperPreparationDeploymentAdapter(
        tmp_path / "state",
        driver="DOCKER_COMPOSE_NARROW",
        compose_file=compose,
        command_runner=runner,
        source_identity_provider=lambda: IDENTITY,
        runtime_probe=lambda _: probe[0],
    )


def test_current_image_is_built_then_only_readonly_is_force_recreated_before_marker(tmp_path):
    runner = Runner()
    probe = [acceptance()]
    deployment = docker_adapter(tmp_path, probe, runner)

    result = deployment.deploy_readonly_api_narrow()

    assert result.changed
    commands = [call[0] for call in runner.calls]
    assert len(commands) == 2
    assert commands[0][-2:] == ("build", "readonly-api")
    assert "--no-deps" in commands[1] and "--force-recreate" in commands[1]
    assert "--wait" in commands[1] and commands[1][-1] == "readonly-api"
    assert all(call[1]["env"]["TRADERS_READONLY_SOURCE_IDENTITY"] == IDENTITY for call in runner.calls)
    assert (tmp_path / "state/readonly-api.narrow.json").is_file()


@pytest.mark.parametrize(
    ("failure", "reason"),
    (("build", "READONLY_CURRENT_IMAGE_BUILD_FAILED"),
     ("start", "READONLY_NARROW_DEPLOYMENT_FAILED")),
)
def test_build_and_start_fail_closed_without_ready_marker(tmp_path, failure, reason):
    runner = Runner(fail_build=failure == "build", fail_start=failure == "start")
    deployment = docker_adapter(tmp_path, [acceptance()], runner)
    with pytest.raises(PaperPreparationAdapterError, match=reason):
        deployment.deploy_readonly_api_narrow()
    assert not (tmp_path / "state/readonly-api.narrow.json").exists()


@pytest.mark.parametrize(
    "bad",
    (
        acceptance(identity=OTHER_IDENTITY),
        acceptance(healthy=False),
        acceptance(routes=READONLY_LEGACY_ROUTES),
        acceptance(writes=1),
        acceptance(paper_statuses=(200, 200, 404, 200, 200, 200, 200)),
        acceptance(paper_statuses=(200, 200, 500, 200, 200, 200, 200)),
        acceptance(legacy_statuses=(200,) * 8 + (404,)),
    ),
)
def test_runtime_identity_health_routes_paper_and_legacy_fail_closed(tmp_path, bad):
    deployment = docker_adapter(tmp_path, [bad], Runner())
    with pytest.raises(PaperPreparationAdapterError, match="READONLY_RUNTIME_ACCEPTANCE_FAILED"):
        deployment.deploy_readonly_api_narrow()
    assert not (tmp_path / "state/readonly-api.narrow.json").exists()


def test_stale_marker_cannot_override_runtime_and_marker_write_failure_is_not_ready(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir()
    marker = state / "readonly-api.narrow.json"
    marker.write_text(json.dumps(marker_payload(OTHER_IDENTITY)), encoding="utf-8")
    deployment = docker_adapter(tmp_path, [acceptance()], Runner())

    assert not deployment.readonly_api_narrow_ready()
    monkeypatch.setattr(
        deployment,
        "_publish",
        lambda *_: (_ for _ in ()).throw(PaperPreparationAdapterError("MARKER_WRITE_FAILED")),
    )
    with pytest.raises(PaperPreparationAdapterError, match="MARKER_WRITE_FAILED"):
        deployment.deploy_readonly_api_narrow()
    assert not deployment.readonly_api_narrow_ready()


def test_completed_replay_performs_no_build_recreate_or_marker_mutation(tmp_path):
    runner = Runner()
    deployment = docker_adapter(tmp_path, [acceptance()], runner)
    first = deployment.deploy_readonly_api_narrow()
    before = (tmp_path / "state/readonly-api.narrow.json").read_bytes()
    runner.calls.clear()

    replay = deployment.deploy_readonly_api_narrow()

    assert first.changed and not replay.changed and replay.ready
    assert runner.calls == []
    assert (tmp_path / "state/readonly-api.narrow.json").read_bytes() == before


def test_old_schema_marker_is_bookkeeping_only_even_with_healthy_runtime(tmp_path):
    (tmp_path / "readonly-api.narrow.json").write_text(
        '{"deployment":"NARROW","service":"readonly-api","write_routes":0}',
        encoding="utf-8",
    )
    assert not adapter(tmp_path, [acceptance()]).readonly_api_narrow_ready()


def test_accepted_deployed_runtime_can_publish_marker_without_build_or_recreate(tmp_path):
    runner = Runner()
    deployment = docker_adapter(tmp_path, [acceptance(identity=OTHER_IDENTITY)], runner)

    result = deployment.accept_deployed_readonly_api_narrow()

    assert result.changed and result.ready
    assert runner.calls == []
    assert json.loads((tmp_path / "state/readonly-api.narrow.json").read_text()) == (
        marker_payload(OTHER_IDENTITY)
    )
    assert deployment.readonly_api_narrow_ready()


@pytest.mark.parametrize(
    "bad",
    (
        acceptance(healthy=False),
        acceptance(routes=READONLY_LEGACY_ROUTES),
        acceptance(writes=1),
        acceptance(paper_statuses=(200, 200, 500, 200, 200, 200, 200)),
        acceptance(legacy_statuses=(200,) * 8 + (500,)),
    ),
)
def test_marker_only_acceptance_fails_closed_before_marker_write(tmp_path, bad):
    runner = Runner()
    deployment = docker_adapter(tmp_path, [bad], runner)

    with pytest.raises(PaperPreparationAdapterError, match="READONLY_RUNTIME_ACCEPTANCE_FAILED"):
        deployment.accept_deployed_readonly_api_narrow()

    assert runner.calls == []
    assert not (tmp_path / "state/readonly-api.narrow.json").exists()
