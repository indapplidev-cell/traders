from __future__ import annotations

import csv
import importlib.util
import inspect
import json
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/engine_trend_24_scoring_redesign_setup_viability_filter.py"
SPEC = importlib.util.spec_from_file_location("engine_trend_24", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.fixture(scope="module")
def candidates():
    return json.loads((audit.DEFAULT_INPUT / "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json").read_text(encoding="utf-8"))["candidates"]


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("engine_trend_24")
    result = audit.run(audit.DEFAULT_INPUT, audit.DEFAULT_AUDIT_23, output)
    return output, result


def test_score_v2_and_filter_are_deterministic(candidates):
    candidate = candidates[0]
    assert audit.evaluate_candidate(candidate) == audit.evaluate_candidate(deepcopy(candidate))


def test_score_and_filter_do_not_use_forbidden_outcome_fields(candidates):
    candidate = deepcopy(candidates[0])
    before = audit.evaluate_candidate(candidate)
    candidate["outcome"] = {
        "label_status": "TP_BEFORE_SL", "net_return_pct": 999, "gross_return_pct": 1000,
        "mfe": 10**9, "mae": 0, "bars_to_tp": 1, "bars_to_sl": None, "bars_to_outcome": 1,
    }
    after = audit.evaluate_candidate(candidate)
    assert before == after
    feature_names = set(audit.default_config()["declared_pre_entry_features"])
    assert feature_names.isdisjoint(audit.FORBIDDEN_FEATURE_NAMES)
    score_source = inspect.getsource(audit.score_features) + inspect.getsource(audit.filter_features)
    assert "candidate[" not in score_source


def test_invalid_geometry_is_fail(candidates):
    candidate = deepcopy(candidates[0])
    candidate["stop_price"] = candidate["entry_price"]
    result = audit.evaluate_candidate(candidate)
    assert result["filter_pass"] is False
    assert "INVALID_SETUP_GEOMETRY" in result["fail_reasons"]


def test_rr_below_1_5_is_fail(candidates):
    candidate = deepcopy(candidates[0]); candidate["planned_rr"] = 1.49
    result = audit.evaluate_candidate(candidate)
    assert result["filter_pass"] is False
    assert "RR_BELOW_1_5" in result["fail_reasons"]


def test_stop_too_tight_is_fail(candidates):
    candidate = deepcopy(candidates[0])
    atr = candidate["technical_confirmation"]["values"]["atr14"]
    candidate["stop_price"] = candidate["entry_price"] + 0.5 * atr
    candidate["invalidation_price"] = candidate["entry_price"] + 0.4 * atr
    result = audit.evaluate_candidate(candidate)
    assert result["filter_pass"] is False
    assert "TOO_TIGHT_STOP" in result["fail_reasons"]


def test_high_rr_alone_does_not_boost_score(candidates):
    candidate = deepcopy(next(c for c in candidates if 2 <= c["planned_rr"] <= 3.5))
    optimal = audit.evaluate_candidate(candidate)["components"]["risk_adjusted_rr_score"]
    candidate["planned_rr"] = 9.0
    high = audit.evaluate_candidate(candidate)["components"]["risk_adjusted_rr_score"]
    assert high < optimal


def test_main_entry_not_maximum_only_because_of_rr(candidates):
    evaluations = {c["candidate_id"]: audit.evaluate_candidate(c) for c in candidates}
    main = evaluations["ET-HED-0001"]
    assert main["components"]["risk_adjusted_rr_score"] < 80
    assert main["score_v2"] < max(item["score_v2"] for item in evaluations.values())


def test_validation_metrics_are_separate_from_train(generated):
    _, result = generated
    metrics = result["metrics"]
    train = metrics["train_design"]
    validation = metrics["out_of_time_validation"]
    assert train["all"]["candidates"] + validation["all"]["candidates"] == 449
    assert train["all"]["candidates"] > 0 and validation["all"]["candidates"] > 0
    assert metrics["split_definition"]["validation_start"] == "2025-11-01T00:00:00Z"


def test_ambiguous_outcomes_excluded_from_clean_metrics(candidates):
    result = audit.performance(candidates)
    assert result["clean_candidates"] == 444
    assert result["ambiguous_intracandle"] == 3
    assert result["neither_expired"] == 2
    assert result["tp_before_sl"] + result["sl_before_tp"] == result["clean_candidates"]


def test_final_status_is_never_profitable_system_validated(generated):
    output, result = generated
    assert result["decision"]["final_status"] != "PROFITABLE_SYSTEM_VALIDATED"
    decision = json.loads((output / "ENGINE_TREND_24_DECISION_RECORD.json").read_text(encoding="utf-8"))
    assert decision["profitable_system_validated"] is False


def test_artifact_manifest_contains_all_created_files(generated):
    output, _ = generated
    manifest = json.loads((output / "ENGINE_TREND_24_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
    assert set(manifest["created_files"]) == set(audit.OUTPUT_FILES)
    assert all((output / name).is_file() for name in audit.OUTPUT_FILES)
    for artifact in manifest["artifacts"]:
        payload = (output / artifact["file"]).read_bytes()
        assert len(payload) == artifact["bytes"]
        assert audit.hashlib.sha256(payload).hexdigest() == artifact["sha256"]


def test_score_results_cover_every_candidate_and_csvs_are_readable(generated):
    output, result = generated
    with (output / "ENGINE_TREND_24_SCORE_V2_RESULTS.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == result["processed"] == 449
    assert {row["filter_pass"] for row in rows} <= {"PASS", "FAIL"}
    for name in audit.OUTPUT_FILES:
        if name.endswith(".csv"):
            with (output / name).open(encoding="utf-8", newline="") as handle:
                assert list(csv.DictReader(handle))
