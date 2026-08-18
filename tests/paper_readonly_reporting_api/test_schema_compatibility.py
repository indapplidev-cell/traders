from __future__ import annotations

import pytest
from pathlib import Path

from app.server_api.schema_compatibility import (
    PAPER_REQUIRED_SCHEMA_OBJECTS,
    revision_is_supported,
)


@pytest.mark.parametrize(
    ("revision", "expected"),
    (
        ("0015_trading_universe_activation", True),
        ("0016_control_mobile_device_security", True),
        ("0014_paper_canary_selection_policy", False),
        ("0017_parallel_trade_profiles", True),
        ("0016_corrupt_metadata", False),
    ),
)
def test_explicit_linear_compatibility_range(revision, expected):
    assert revision_is_supported((revision,)) is expected


@pytest.mark.parametrize(
    "revisions",
    ((), ("0016_control_mobile_device_security", "0015_trading_universe_activation")),
)
def test_missing_or_multiple_heads_fail_closed(revisions):
    assert revision_is_supported(revisions) is False


def test_required_object_inventory_is_explicit_and_excludes_unrelated_0016_tables():
    assert PAPER_REQUIRED_SCHEMA_OBJECTS == (
        "alembic_version",
        "paper_account_baselines",
        "paper_positions",
        "paper_orders",
        "paper_fills",
        "paper_exit_evaluation_cursors",
        "paper_exit_decisions",
        "paper_journal_entries",
    )
    assert "control_mobile_devices" not in PAPER_REQUIRED_SCHEMA_OBJECTS
    assert "control_mobile_replay_nonces" not in PAPER_REQUIRED_SCHEMA_OBJECTS


def test_readonly_image_packages_the_lineage_metadata_used_by_runtime_guard():
    dockerfile = (Path(__file__).resolve().parents[2] / "Dockerfile").read_text(
        encoding="utf-8"
    )
    readonly_stage = dockerfile.split("FROM python:3.11-slim AS readonly-api", 1)[1].split(
        "FROM python:3.11-slim AS operator-control-api", 1
    )[0]
    assert "COPY alembic.ini ./" in readonly_stage
    assert "COPY alembic ./alembic" in readonly_stage
