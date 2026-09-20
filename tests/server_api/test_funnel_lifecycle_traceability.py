from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.engine_paper.empirical_regime import normalize_empirical_regime
from app.server_api.funnel_export import build_export_record
from tests.server_api.test_funnel_export import _pair


NOW = datetime(2030, 3, 17, 18, 0, tzinfo=timezone.utc)


def _record(outcome: dict[str, object]):
    run, result = _pair(profile="trade-5m-v2")
    return build_export_record(
        run, result, generated_at_ms=int(NOW.timestamp() * 1000),
        from_ms=run.closed_until_ms - 1, to_ms=run.closed_until_ms + 1,
        outcome=outcome,
    )


def test_plan_without_command_has_machine_readable_terminal_reason():
    row = _record({
        "plan_terminal_state": "COMMAND_BLOCKED",
        "plan_terminal_reason": "MAX_OPEN_POSITIONS_REACHED",
        "last_lifecycle_event_at": NOW,
    })
    assert row["paper_outcome"]["plan_terminal_state"] == "COMMAND_BLOCKED"
    assert row["paper_outcome"]["plan_terminal_reason"] == "MAX_OPEN_POSITIONS_REACHED"
    assert row["paper_outcome"]["command_id"] is None
    assert row["timestamps"]["last_lifecycle_event_at"] == NOW.isoformat()


def test_command_without_position_has_exact_reason_and_timestamps():
    row = _record({
        "plan_terminal_state": "COMMAND_CREATED",
        "plan_terminal_reason": "COMMAND_CREATED",
        "command_id": "command-1",
        "command_status": "FAILED",
        "command_terminal_reason": "PAPER_SAFETY_SOURCE_STALE",
        "position_not_open_reason": "PAPER_SAFETY_SOURCE_STALE",
        "command_created_at": NOW,
        "command_updated_at": NOW,
    })
    assert row["paper_outcome"]["command_status"] == "FAILED"
    assert row["paper_outcome"]["position_not_open_reason"] == "PAPER_SAFETY_SOURCE_STALE"
    assert row["timestamps"]["command_created_at"] == NOW.isoformat()


@pytest.mark.parametrize("reason", (
    "STOP_LOSS", "TAKE_PROFIT", "NET_PNL_PROTECTION", "MAX_HOLD_TIME",
))
def test_closed_position_never_projects_exit_not_reached(reason: str):
    row = _record({
        "command_id": "command-1", "position_id": "position-1",
        "position_status": "CLOSED", "exit_status": "REACHED",
        "exit_reason": reason, "exit_decision_at": NOW, "exit_fill_at": NOW,
        "position_closed_at": NOW,
        "net_pnl_protection_triggered": reason == "NET_PNL_PROTECTION",
    })
    assert row["exit"]["status"] == "REACHED"
    assert row["exit"]["reason"] == reason
    assert row["exit"]["exit_decision_at"] == NOW.isoformat()
    assert row["exit"]["exit_fill_at"] == NOW.isoformat()
    assert row["exit"]["net_pnl_protection_triggered"] is (
        reason == "NET_PNL_PROTECTION"
    )


@pytest.mark.parametrize(
    ("source", "normalized", "why"),
    (
        ("UP", "UP", "DIRECTIONAL_REGIME_PRESERVED"),
        ("DOWN", "DOWN", "DIRECTIONAL_REGIME_PRESERVED"),
        ("FLAT", "RANGE", "ENGINE_FLAT_MAPS_TO_SCALPING_RANGE"),
        ("RANGE", "RANGE", "SCALPING_RANGE_PRESERVED"),
        ("COMPRESSION", "COMPRESSION", "SCALPING_VOLATILITY_REGIME_PRESERVED"),
        ("EXPANSION", "EXPANSION", "SCALPING_VOLATILITY_REGIME_PRESERVED"),
    ),
)
def test_supported_regime_mapping_is_explicit_and_never_defaults_unknown(
    source: str, normalized: str, why: str,
):
    mapping = normalize_empirical_regime(source)
    assert (mapping.normalized_regime, mapping.reason) == (normalized, why)
    assert mapping.version == "empirical-regime-v1"


def test_runtime_provenance_is_carried_from_decision_and_projection_images(monkeypatch):
    revision = "a" * 40
    monkeypatch.setenv("TRADERS_READONLY_SOURCE_IDENTITY", revision)
    run, result = _pair(profile="trade-5m-v2")
    result.analysis_payload_json["effective_configuration"] = {
        "source_commit": revision, "config_epoch_id": "epoch",
        "config_content_hash": "config-hash", "parameter_set_version": "v1",
    }
    row = build_export_record(
        run, result, generated_at_ms=int(NOW.timestamp() * 1000),
        from_ms=run.closed_until_ms - 1, to_ms=run.closed_until_ms + 1,
    )
    assert row["provenance"] == {
        **row["provenance"],
        "source_commit": revision,
        "runtime_revision": revision,
        "image_revision": revision,
        "projection_runtime_revision": revision,
        "revision_match": True,
    }


def test_production_compose_requires_immutable_revision_and_export_never_reads_host_git():
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    exporter = (root / "app/server_api/funnel_export.py").read_text(encoding="utf-8")
    assert "TRADERS_SCALPING_V2_SOURCE_IDENTITY?immutable source revision is required" in compose
    assert "git rev-parse" not in exporter
    assert "subprocess" not in exporter
