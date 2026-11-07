from __future__ import annotations

import json

import pytest

from traders_ml.parameter_sweep.full_pipeline_reuse_audit_v3 import _controls


def test_controls_cover_first_middle_last_and_a_ready_plan(tmp_path) -> None:
    source = tmp_path / "FEATURES.jsonl"
    source.write_text("".join(json.dumps({
        "boundary_ms": 300_000 * (index + 1),
        "statuses": {"paper_status": "PAPER_PLAN_READY" if index == 1 else "NO_PLAN"},
    }) + "\n" for index in range(5)), encoding="utf-8")
    assert _controls(source, expected=5, holdout_start_ms=1_800_000) == (
        300_000, 600_000, 900_000, 1_500_000)


def test_controls_reject_a_boundary_at_holdout(tmp_path) -> None:
    source = tmp_path / "FEATURES.jsonl"
    source.write_text(json.dumps({"boundary_ms": 300_000,
                                  "statuses": {"paper_status": "NO_PLAN"}}) + "\n")
    with pytest.raises(ValueError, match="NOT_CAUSAL"):
        _controls(source, expected=1, holdout_start_ms=300_000)
