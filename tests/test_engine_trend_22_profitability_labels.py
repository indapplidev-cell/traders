"""ENGINE-TREND-22 offline profitability label-builder checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.market_reader.engine_trend.profitability_labels import (
    DEFAULT_AUDIT_COSTS,
    LabelStatus,
    build_profitability_label,
)


ROOT = Path("reports/engine_trend/engine_trend_22_profitability_label_builder")
FIXTURES = ROOT / "ENGINE_TREND_22_SYNTHETIC_FIXTURES.json"
RESULTS = ROOT / "ENGINE_TREND_22_SYNTHETIC_LABEL_RESULTS.json"
OUTPUT_SCHEMA = ROOT / "ENGINE_TREND_22_PROFITABILITY_LABEL_SCHEMA.json"
LIVE_CHECKS = ROOT / "ENGINE_TREND_22_LIVE_CASE_LABEL_CHECKS.json"
DECISION = ROOT / "ENGINE_TREND_22_DECISION_RECORD.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_rows() -> list[dict]:
    return load_json(FIXTURES)["fixtures"]


@pytest.mark.parametrize("fixture", fixture_rows(), ids=lambda row: row["fixture_id"])
def test_all_synthetic_outcomes(fixture: dict) -> None:
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert result["label_status"] == fixture["expected_label_status"]


def test_all_required_statuses_are_implemented() -> None:
    assert {status.value for status in LabelStatus} == {
        "TP_BEFORE_SL", "SL_BEFORE_TP", "NEITHER_EXPIRED",
        "AMBIGUOUS_INTRACANDLE", "INSUFFICIENT_FUTURE_DATA",
        "INVALID_SETUP_PLAN", "NO_TRADE_SKIPPED",
    }


def test_entry_and_prior_candles_are_excluded_to_prevent_leakage() -> None:
    setup = next(row["setup_plan"] for row in fixture_rows() if row["fixture_id"] == "long_tp_before_sl")
    candles = [
        {"timestamp": "2025-12-31T23:45:00Z", "high": 999.0, "low": 1.0, "close": 100.0},
        {"timestamp": "2026-01-01T00:00:00Z", "high": 999.0, "low": 1.0, "close": 100.0},
        {"timestamp": "2026-01-01T00:15:00Z", "high": 111.0, "low": 99.0, "close": 109.0},
    ]
    result = build_profitability_label(setup, candles)
    assert result["label_status"] == "TP_BEFORE_SL"
    assert result["bars_to_outcome"] == 1
    assert result["mae_abs"] == pytest.approx(1.0)


def test_no_trade_states_never_receive_win_or_loss() -> None:
    base = next(row["setup_plan"] for row in fixture_rows() if row["fixture_id"] == "no_trade_skipped")
    for status in ("NO_TRADE", "WAIT_CONFIRMATION", "INVALIDATED"):
        result = build_profitability_label({**base, "status": status}, [])
        assert result["label_status"] == "NO_TRADE_SKIPPED"
        assert result["gross_return_pct"] is None
        assert result["target_results"] == []


def test_ambiguous_intracandle_is_not_a_clean_win_or_loss() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "intracandle_ambiguous")
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert result["label_status"] == "AMBIGUOUS_INTRACANDLE"
    assert result["ambiguity_flags"] == ["TARGET_AND_STOP_TOUCHED_SAME_CANDLE"]
    assert result["exit_price"] is None
    assert result["gross_return_pct"] is None
    assert result["net_return_pct"] is None


def test_insufficient_data_keeps_observed_excursions_without_inventing_exit() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "insufficient_future_data")
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert result["label_status"] == "INSUFFICIENT_FUTURE_DATA"
    assert result["mfe_abs"] == pytest.approx(6.0)
    assert result["exit_time"] is None
    assert result["net_return_pct"] is None


def test_net_return_subtracts_deterministic_round_trip_cost() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "long_tp_before_sl")
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert DEFAULT_AUDIT_COSTS.round_trip_cost_bps == 24.0
    assert result["gross_return_pct"] == pytest.approx(10.0)
    assert result["net_return_pct"] == pytest.approx(9.76)


def test_mfe_mae_and_planned_rr_use_directional_formulas() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "short_tp_before_sl")
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert result["risk_abs"] == pytest.approx(5.0)
    assert result["reward_abs"] == pytest.approx(10.0)
    assert result["rr_planned"] == pytest.approx(2.0)
    assert result["mfe_abs"] == pytest.approx(11.0)
    assert result["mfe_r"] == pytest.approx(2.2)
    assert result["mae_abs"] == pytest.approx(2.0)
    assert result["mae_r"] == pytest.approx(0.4)


def test_multiple_targets_are_independent_and_t1_is_primary() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "multiple_targets")
    result = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
    assert result["label_status"] == "TP_BEFORE_SL"
    assert result["target_price"] == 105.0
    assert [(row["target_id"], row["label_status"]) for row in result["target_results"]] == [
        ("T1", "TP_BEFORE_SL"), ("T2", "SL_BEFORE_TP")
    ]


def test_generated_results_match_builder_and_output_schema_shape() -> None:
    schema = load_json(OUTPUT_SCHEMA)
    required = set(schema["required"])
    allowed = set(schema["properties"])
    target_required = set(schema["$defs"]["targetResult"]["required"])
    target_allowed = set(schema["$defs"]["targetResult"]["properties"])
    statuses = set(schema["$defs"]["status"]["enum"])
    stored = {row["fixture_id"]: row["label"] for row in load_json(RESULTS)["results"]}
    for fixture in fixture_rows():
        generated = build_profitability_label(fixture["setup_plan"], fixture["future_candles"])
        assert stored[fixture["fixture_id"]] == generated
        assert required <= generated.keys() <= allowed
        assert generated["label_status"] in statuses
        for target in generated["target_results"]:
            assert target_required <= target.keys() <= target_allowed
            assert target["label_status"] in statuses


def test_live_cases_are_skipped_and_real_validation_is_blocked() -> None:
    checks = load_json(LIVE_CHECKS)
    assert len(checks["cases"]) == 4
    assert all(row["label_status"] == "NO_TRADE_SKIPPED" for row in checks["cases"])
    assert all(row["profitability_metrics_counted"] is False for row in checks["cases"])
    decision = load_json(DECISION)
    assert decision["real_market_profitability_validation_status"] == "BLOCKED_NO_TRADE_CANDIDATES"
    assert decision["runtime_changed"] is False
    assert decision["trading_runtime_changed"] is False
    assert decision["thresholds_changed"] is False
    assert decision["composer_changed"] is False
    assert decision["setup_contracts_changed"] is False


def test_indicator_only_and_blocked_contract_cannot_be_labeled_as_trade() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "short_tp_before_sl")
    plan = {**fixture["setup_plan"], "setup_type": "SHORT_TREND_ONLY_CONTINUATION_CANDIDATE"}
    result = build_profitability_label(plan, fixture["future_candles"])
    assert result["label_status"] == "INVALID_SETUP_PLAN"
    assert "SETUP_CONTRACT_BLOCKED_ENGINE_TREND_20B" in result["validation_errors"]

    indicator_only = {**fixture["setup_plan"], "evidence_origin": "INDICATOR_ONLY"}
    result = build_profitability_label(indicator_only, fixture["future_candles"])
    assert "INDICATOR_ONLY_EVIDENCE_CANNOT_ORIGINATE_SETUP" in result["validation_errors"]


def test_unknown_regime_and_no_trade_contract_cannot_be_disguised_as_candidate() -> None:
    fixture = next(row for row in fixture_rows() if row["fixture_id"] == "long_tp_before_sl")
    plan = {
        **fixture["setup_plan"],
        "source_regime": "UNKNOWN",
        "setup_type": "NO_TRADE_CONTRACT",
    }
    result = build_profitability_label(plan, fixture["future_candles"])
    assert result["label_status"] == "INVALID_SETUP_PLAN"
    assert "UNKNOWN_REGIME_CANNOT_BE_TRADE_CANDIDATE" in result["validation_errors"]
    assert "NO_TRADE_CONTRACT_CANNOT_BE_TRADE_CANDIDATE" in result["validation_errors"]
