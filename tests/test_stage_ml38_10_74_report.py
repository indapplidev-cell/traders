from __future__ import annotations

from pathlib import Path


REPORT = Path("reports/stage_ml38_10_74_outcome_aware_calibration_replay_report.md")


def test_stage_ml38_10_74_report_exists_and_mentions_core_contract() -> None:
    assert REPORT.exists()
    text = REPORT.read_text(encoding="utf-8")

    assert "ML38.10.74" in text
    assert "Outcome-aware calibration replay" in text or "outcome-aware calibration replay" in text
    assert "actual_label" in text
    assert "raw probabilities" in text
    assert "calibrated probabilities" in text
    assert "accuracy" in text
    assert "accuracy_edge" in text
    assert "majority" in text
    assert "FLAT" in text
    assert "directional" in text


def test_stage_ml38_10_74_report_blocks_production_actions() -> None:
    text = REPORT.read_text(encoding="utf-8")

    assert "production_policy_allowed_now: false" in text
    assert "cascade/outcome blocked" in text
    assert "production-like recompute/tradable edge not claimed" in text
    assert "directional_confidence_floor 0.60 not implemented" in text
    assert "flat override not implemented" in text
    assert "h08 fix applied: false" in text or "h08 fix applied" in text
    assert "no commit/planning/snapshot" in text
    assert "ML38.10.75" in text
