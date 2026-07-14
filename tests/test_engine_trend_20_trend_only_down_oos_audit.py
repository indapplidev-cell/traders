"""Regression checks for generated ENGINE-TREND-20 audit artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path("reports/engine_trend/engine_trend_20_trend_only_down_oos_audit")
AUDIT = ROOT / "ENGINE_TREND_20_TREND_ONLY_DOWN_OOS_AUDIT.json"
DATASET = ROOT / "ENGINE_TREND_20_OOS_DATASET.csv"
MANUAL = ROOT / "ENGINE_TREND_20_MANUAL_LABEL_TEMPLATE.json"
MANIFEST = ROOT / "ENGINE_TREND_20_ARTIFACT_MANIFEST.json"
DECISION = ROOT / "ENGINE_TREND_20_DECISION_RECORD.json"
MANDATORY = {
    "BTCUSDT_15m_2026_07_13_16_00",
    "SOLUSDT_15m_2026_07_08_06_00",
    "SOLUSDT_15m_2026_07_08_11_30",
    "SOLUSDT_15m_2026_07_08_18_30",
    "SOLUSDT_15m_2026_07_08_23_45",
}
REQUIRED_ARTIFACTS = {
    "ENGINE_TREND_20_TREND_ONLY_DOWN_OOS_AUDIT.md",
    "ENGINE_TREND_20_TREND_ONLY_DOWN_OOS_AUDIT.json",
    "ENGINE_TREND_20_OOS_DATASET.csv",
    "ENGINE_TREND_20_COUNTERFACTUAL_RESULTS.csv",
    "ENGINE_TREND_20_MANUAL_LABEL_TEMPLATE.json",
    "ENGINE_TREND_20_HYPOTHESIS_TRACE.json",
    "ENGINE_TREND_20_FALSE_DOWN_RISK_AUDIT.md",
    "ENGINE_TREND_20_SOLUSDT_11_30_INVALIDATION_TRACE.md",
    "ENGINE_TREND_20_ARTIFACT_MANIFEST.json",
    "ENGINE_TREND_20_DECISION_RECORD.json",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_dataset_has_seeds_unique_complete_windows() -> None:
    with DATASET.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["case_id"] for row in rows]
    assert MANDATORY <= set(ids)
    assert len(ids) == len(set(ids))
    assert len(rows) >= 30
    assert all(int(row["candles"]) == 96 for row in rows)


def test_manual_template_is_blind_and_unlabelled() -> None:
    rows = load_json(MANUAL)
    assert rows
    assert all(row["blind_chart_required"] is True for row in rows)
    assert all(row["manual_label"] is None and row["manual_notes"] is None for row in rows)
    assert all("expected_label" not in row for row in rows)


def test_counterfactual_does_not_mutate_baseline() -> None:
    cases = load_json(AUDIT)["cases"]
    included = [row for row in cases if not row["excluded_from_metrics"]]
    assert included
    assert all(row["counterfactual"]["baseline_unchanged"] for row in included)
    assert all(
        row["counterfactual"]["baseline_regime_before"]
        == row["counterfactual"]["baseline_regime_after"]
        == row["baseline_regime"]
        for row in included
    )


def test_no_manual_labels_never_ready_for_implementation() -> None:
    decision = load_json(DECISION)
    assert decision["manual_labels_status"] == "BLOCKED_MANUAL_LABELS"
    assert decision["final_status"] != "TREND_ONLY_DOWN_CONTRACT_READY_FOR_IMPLEMENTATION"
    assert decision["runtime_changed"] is False
    assert decision["trading_runtime_changed"] is False
    assert decision["thresholds_changed"] is False
    assert decision["composer_changed"] is False


def test_manifest_contains_all_required_artifacts() -> None:
    paths = {Path(item["path"]).name for item in load_json(MANIFEST)["files"]}
    assert REQUIRED_ARTIFACTS <= paths

