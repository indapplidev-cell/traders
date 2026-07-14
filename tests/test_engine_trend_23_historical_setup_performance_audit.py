from __future__ import annotations

import csv
import importlib.util
import json
import math
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/engine_trend_23_historical_setup_performance_audit.py"
SPEC = importlib.util.spec_from_file_location("engine_trend_23_audit", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


@pytest.fixture(scope="module")
def source_candidates():
    path = audit.DEFAULT_INPUT / "HISTORICAL_ENTRY_DISCOVERY_RESULTS.json"
    return json.loads(path.read_text(encoding="utf-8"))["candidates"]


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    output = tmp_path_factory.mktemp("engine_trend_23")
    summary = audit.run(audit.DEFAULT_INPUT, output)
    return output, summary


def test_candidate_count_and_unique_ids(source_candidates):
    assert len(source_candidates) == 449
    ids = [candidate["candidate_id"] for candidate in source_candidates]
    assert len(ids) == len(set(ids))


def test_clean_metrics_exclude_ambiguous_and_expired_from_binary_counts(source_candidates):
    result = audit.metrics(source_candidates)
    assert result["clean_candidates"] == 444
    assert result["tp_before_sl"] == 143
    assert result["sl_before_tp"] == 301
    assert result["ambiguous_intracandle"] == 3
    assert result["neither_expired"] == 2
    assert result["return_observations_including_expired_marks"] == 446


def test_profit_factor_uses_positive_and_negative_available_returns(source_candidates):
    returns = [audit.net(candidate) for candidate in source_candidates if audit.finite_number(audit.net(candidate))]
    expected = sum(value for value in returns if value > 0) / abs(sum(value for value in returns if value < 0))
    assert audit.metrics(source_candidates)["profit_factor"] == pytest.approx(expected)
    assert expected == pytest.approx(0.5566821144)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(1.5, "1.5-<2"), (1.9999, "1.5-<2"), (2.0, "2-<3"), (3.0, "3-<5"), (5.0, "5-8"), (8.0, "5-8"), (8.0001, ">8")],
)
def test_rr_bucket_assignment(value, expected):
    assert audit.rr_bucket(value) == expected


def test_quality_decile_assignment_is_equal_count_and_deterministic(source_candidates):
    clean = sorted(
        (candidate for candidate in source_candidates if audit.outcome(candidate) in audit.CLEAN_LABELS),
        key=lambda candidate: (candidate["quality_score"], audit.entry_dt(candidate), candidate["candidate_id"]),
    )
    assigned = [audit.quantile_bucket(clean, index) for index in range(len(clean))]
    assert assigned == [audit.quantile_bucket(clean, index) for index in range(len(clean))]
    assert min(assigned) == 1
    assert max(assigned) == 10
    assert max(assigned.count(decile) for decile in range(1, 11)) - min(assigned.count(decile) for decile in range(1, 11)) <= 1


def test_failure_bucket_assignment_is_deterministic(source_candidates):
    failures = [candidate for candidate in source_candidates if audit.outcome(candidate) != audit.WIN]
    first = [audit.failure_bucket(candidate) for candidate in failures]
    second = [audit.failure_bucket(candidate) for candidate in failures]
    assert first == second
    assert set(first) <= {
        "TOO_TIGHT_STOP", "TARGET_TOO_FAR", "LATE_ENTRY_AFTER_EXHAUSTION", "WEAK_CONFIRMATION_VOLUME",
        "BOLLINGER_EXTENSION_RISK", "RANGE_CONFLICT_IGNORED", "REVERSAL_RISK_IGNORED",
        "CHOPPY_SIDEWAYS_CONTEXT", "TREND_TOO_OLD", "RETEST_TOO_SHALLOW", "RETEST_TOO_DEEP",
        "LOW_RR_DESPITE_PASS", "HIGH_RR_LOW_PROBABILITY", "OTHER",
    }


def test_summary_can_never_claim_profitable_system_validated(generated):
    output, summary = generated
    forbidden = "PROFITABLE_SYSTEM_VALIDATED"
    assert summary["final_status"] != forbidden
    decision = json.loads((output / "ENGINE_TREND_23_DECISION_RECORD.json").read_text(encoding="utf-8"))
    assert decision["final_status"] != forbidden
    assert decision["profitable_system_validated"] is False


def test_artifact_manifest_contains_every_created_file_and_valid_hashes(generated):
    output, _ = generated
    manifest = json.loads((output / "ENGINE_TREND_23_ARTIFACT_MANIFEST.json").read_text(encoding="utf-8"))
    assert set(manifest["created_files"]) == set(audit.OUTPUT_FILES)
    assert all((output / name).is_file() for name in audit.OUTPUT_FILES)
    for artifact in manifest["artifacts"]:
        payload = (output / artifact["file"]).read_bytes()
        assert len(payload) == artifact["bytes"]
        assert audit.hashlib.sha256(payload).hexdigest() == artifact["sha256"]


def test_generated_csvs_are_readable_and_integrity_passes(generated):
    output, summary = generated
    assert summary["integrity_check"]["status"] == "PASS"
    for name in audit.OUTPUT_FILES:
        if name.endswith(".csv"):
            with (output / name).open(encoding="utf-8", newline="") as handle:
                assert list(csv.DictReader(handle))
