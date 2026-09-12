from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
import yaml

from app.config.yaml_authority import (
    RESEARCH_PARAMETERS,
    VALIDATION_SAMPLE_POLICY,
    load_validation_sample_policy,
)
from traders_ml.parameter_sweep.symbol_authority_audit import build_symbol_runtime_authority_audit
from traders_ml.parameter_sweep.universe import validate_parameter_sweep_symbol
from traders_ml.parameter_sweep.controller import ParameterSweepController
from traders_ml.parameter_sweep.validation_ranking import (
    CANONICAL_RANKING_COMPARATOR,
    POSITIVE_INFINITY_MARKER,
    ValidationRankingError,
    _write_outputs,
    build_validation_rankings,
    profit_factor_ranking_semantics,
    validation_eligibility,
    validation_policy_payload,
)


def _row(
    config_id: str, signature: str, *, trades: int = 20, periods: int = 3,
    wins: int = 12, losses: int = 8, net_pnl: float = 2.0,
    profit_factor: float | None = 1.5, expectancy=None,
) -> dict[str, object]:
    return {
        "config_id": config_id, "behavioral_signature": signature,
        "validation_trade_count": trades, "trade_count": trades,
        "independent_period_count": periods,
        "independent_period_unit": "UTC_CALENDAR_DAY",
        "independent_period_buckets": [f"2026-09-{day:02d}" for day in range(1, periods + 1)],
        "symbol_coverage": 1, "symbol_coverage_pass": True,
        "minimum_slice_count": 2, "setup_coverage": 1, "regime_coverage": 1,
        "evaluation_status": "ACCEPTED", "wins": wins, "losses": losses,
        "neutrals": max(0, trades - wins - losses), "net_pnl": net_pnl,
        "expectancy_R": expectancy, "profit_factor": profit_factor,
        "max_drawdown": 0.5, "parameters": {"min_net_edge_bps": float(config_id.strip("abc") or 1)},
    }


def _metadata() -> dict[str, object]:
    return {
        "symbol": "DOGEUSDT", "profile": "trade-5m-v2",
        "dataset_fingerprint": "dataset", "calibration_split_fingerprint": "calibration",
        "validation_split_fingerprint": "validation",
        "validation_policy_fingerprint": "validation-policy",
        "ranking_policy_fingerprint": "ranking-policy",
        "parameter_registry_fingerprint": "registry",
        "range_handoff_fingerprint": "range", "expanded_search_fingerprint": "expanded",
        "adaptive_handoff_fingerprint": "adaptive", "adaptive_clusters_fingerprint": "clusters",
        "adaptive_results_fingerprint": "results", "source_history_start": "2026-09-01T00:00:00+00:00",
        "source_history_end": "2026-09-02T00:00:00+00:00", "source_history_actual_days": 1.0,
        "cross_symbol_rows": 0, "reconstructed_rows_used": 0,
    }


def _symbol_audit() -> dict[str, object]:
    return {
        "symbol_authority_source": "app.trading_universe.domain:trading-universe-v2",
        "RUNTIME_SYMBOL_HARDCODES": 0, "RUNTIME_SYMBOL_DEFAULTS": 0,
        "RUNTIME_SYMBOL_BRANCHES": 0,
    }


def test_eligibility_is_partitioned_before_ranking_even_with_infinite_pf():
    zero_loss = _row("a1", "sig-a", trades=1, periods=1, wins=1, losses=0, net_pnl=1.0, profit_factor=None)
    eligible = _row("b2", "sig-b", trades=21, periods=4)
    ranked = build_validation_rankings([zero_loss, eligible], VALIDATION_SAMPLE_POLICY)
    assert [row["config_id"] for row in ranked["eligible_numeric"]] == ["b2"]
    assert [row["config_id"] for row in ranked["descriptive_numeric"]] == ["a1"]
    assert ranked["descriptive_numeric"][0]["profit_factor_ranking_value"] == POSITIVE_INFINITY_MARKER


def test_zero_eligible_is_valid_and_handoff_list_is_empty(tmp_path: Path):
    ranked = build_validation_rankings([_row("a1", "sig", trades=1, periods=1)], VALIDATION_SAMPLE_POLICY)
    result = _write_outputs(
        output=tmp_path, rankings=ranked, metadata=_metadata(),
        policy_payload=validation_policy_payload(VALIDATION_SAMPLE_POLICY), symbol_audit=_symbol_audit(),
    )
    assert result["status"]["ELIGIBLE_NUMERIC_CONFIGS"] == 0
    assert result["handoff"]["eligible_behavioral_candidates"] == []
    assert result["handoff"]["holdout_reads"] == 0


def test_behavioral_duplicates_count_as_one_candidate():
    rows = [_row(f"a{index}", "same") for index in range(1, 4)]
    ranked = build_validation_rankings(rows, VALIDATION_SAMPLE_POLICY)
    assert len(ranked["eligible_numeric"]) == 3
    assert len(ranked["eligible_behavioral"]) == 1
    assert len(ranked["eligible_behavioral"][0]["member_config_ids"]) == 3


def test_ineligible_duplicate_cannot_enter_eligible_cluster():
    eligible = _row("b2", "same")
    ineligible = _row("a1", "same", trades=1, periods=1, wins=1, losses=0, profit_factor=None)
    ranked = build_validation_rankings([ineligible, eligible], VALIDATION_SAMPLE_POLICY)
    assert ranked["eligible_behavioral"][0]["representative_config_id"] == "b2"
    assert ranked["eligible_behavioral"][0]["member_config_ids"] == ["b2"]
    assert ranked["descriptive_behavioral"][0]["member_config_ids"] == ["a1"]


def test_pf_storage_is_not_mutated_by_positive_zero_loss_surrogate():
    row = _row("a1", "sig", trades=1, periods=1, wins=1, losses=0, net_pnl=1.0, profit_factor=None)
    ranked = build_validation_rankings([row], VALIDATION_SAMPLE_POLICY)
    projected = ranked["descriptive_numeric"][0]
    assert row["profit_factor"] is None
    assert projected["stored_profit_factor"] is None
    assert projected["profit_factor_available"] is False
    assert projected["profit_factor_ranking_value"] == POSITIVE_INFINITY_MARKER


def test_other_missing_pf_keeps_zero_sentinel():
    row = _row("a1", "sig", trades=0, periods=0, wins=0, losses=0, net_pnl=0.0, profit_factor=None)
    numeric, serialized, reason = profit_factor_ranking_semantics(row)
    assert numeric == serialized == 0
    assert reason == "OTHER_MISSING_PROFIT_FACTOR_ZERO_SENTINEL"


def test_missing_expectancy_remains_not_available():
    ranked = build_validation_rankings([_row("a1", "sig", expectancy=None)], VALIDATION_SAMPLE_POLICY)
    assert ranked["eligible_numeric"][0]["expectancy_r"] is None


def test_gate_authority_fixture_changes_eligibility_without_code_change(tmp_path: Path):
    authority = RESEARCH_PARAMETERS.model_dump(mode="python")
    authority["ranking"]["validation_minimum_trades"] = 21
    authority["ranking"]["minimum_independent_periods"] = 4
    path = tmp_path / "research.yaml"
    path.write_text(yaml.safe_dump(authority), encoding="utf-8")
    policy = load_validation_sample_policy(path)
    record = validation_eligibility(_row("a1", "sig", trades=20, periods=3), policy)
    assert record["validation_eligible"] is False
    assert record["required_validation_trade_count"] == 21
    assert record["required_independent_period_count"] == 4


def test_missing_canonical_gate_key_fails_closed():
    row = _row("a1", "sig")
    del row["setup_coverage"]
    with pytest.raises(ValidationRankingError, match="FAIL_CLOSED_MISSING_CANONICAL_FIELD_SETUP_COVERAGE"):
        validation_eligibility(row, VALIDATION_SAMPLE_POLICY)


def test_missing_canonical_yaml_gate_key_fails_closed_without_fallback(tmp_path: Path):
    authority = RESEARCH_PARAMETERS.model_dump(mode="python")
    del authority["ranking"]["validation_minimum_trades"]
    path = tmp_path / "missing-gate.yaml"
    path.write_text(yaml.safe_dump(authority), encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid authoritative YAML"):
        load_validation_sample_policy(path)


def test_holdout_neighbor_is_not_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "HOLDOUT_RESULTS.json").write_text("must-not-be-read", encoding="utf-8")
    reads: list[str] = []
    original = Path.read_text

    def watched(path: Path, *args, **kwargs):
        if "HOLDOUT" in path.name:
            reads.append(str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", watched)
    build_validation_rankings([_row("a1", "sig")], VALIDATION_SAMPLE_POLICY)
    assert reads == []


@pytest.mark.parametrize("symbol", ["DOGEUSDT", "LINKUSDT"])
def test_same_validation_ranking_symbol_path_supports_two_symbols(symbol: str):
    assert validate_parameter_sweep_symbol(symbol) == symbol


def test_runtime_symbol_forensic_remains_zero():
    audit = build_symbol_runtime_authority_audit()
    assert audit["RUNTIME_SYMBOL_HARDCODES"] == 0
    assert audit["RUNTIME_SYMBOL_DEFAULTS"] == 0
    assert audit["RUNTIME_SYMBOL_BRANCHES"] == 0


def test_same_inputs_are_deterministic_and_no_freeze_is_written(tmp_path: Path):
    rows = [_row("a1", "one"), _row("b2", "two", trades=1, periods=1)]
    first = build_validation_rankings(deepcopy(rows), VALIDATION_SAMPLE_POLICY)
    second = build_validation_rankings(deepcopy(rows), VALIDATION_SAMPLE_POLICY)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    _write_outputs(
        output=tmp_path, rankings=first, metadata=_metadata(),
        policy_payload=validation_policy_payload(VALIDATION_SAMPLE_POLICY), symbol_audit=_symbol_audit(),
    )
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    _write_outputs(
        output=tmp_path, rankings=second, metadata=_metadata(),
        policy_payload=validation_policy_payload(VALIDATION_SAMPLE_POLICY), symbol_audit=_symbol_audit(),
    )
    assert before == {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert not list(tmp_path.glob("*FINALIST*"))
    assert not list(tmp_path.glob("*HOLDOUT*"))


def test_status_preserves_scope_and_canonical_comparator(tmp_path: Path):
    rankings = build_validation_rankings([_row("a1", "sig")], VALIDATION_SAMPLE_POLICY)
    status = _write_outputs(
        output=tmp_path, rankings=rankings, metadata=_metadata(),
        policy_payload=validation_policy_payload(VALIDATION_SAMPLE_POLICY), symbol_audit=_symbol_audit(),
    )["status"]
    assert status["CANONICAL_RANKING_COMPARATOR"] == CANONICAL_RANKING_COMPARATOR
    assert status["FINALIST_FREEZE_EXECUTED"] is False
    assert status["ADAPTIVE_REFINEMENT_EXECUTED"] is False
    assert status["EXPANDED_SEARCH_RERUN"] is False
    assert status["PROMOTION_ELIGIBLE"] is False
    assert status["LIVE_STATE"] is False
    assert status["BINANCE_ORDER_CALLS"] == status["PRODUCTION_MUTATIONS"] == 0


def test_existing_gui_projection_reads_validation_ranking_summary(tmp_path: Path):
    output = tmp_path / "validation"
    rankings = build_validation_rankings([
        _row("a1", "eligible"),
        _row("b2", "descriptive", trades=1, periods=1),
    ], VALIDATION_SAMPLE_POLICY)
    _write_outputs(
        output=output, rankings=rankings, metadata=_metadata(),
        policy_payload=validation_policy_payload(VALIDATION_SAMPLE_POLICY), symbol_audit=_symbol_audit(),
    )
    controller = ParameterSweepController(Path("unused.yaml"), tmp_path)
    controller.state.output_directory = str(output)
    controller.drain_events()
    assert controller.state.research_phase == "VALIDATION_RANKING"
    assert controller.state.validation_ranking_eligible_numeric == 1
    assert controller.state.validation_ranking_eligible_behavioral == 1
    assert controller.state.validation_ranking_descriptive_behavioral == 1
    assert controller.state.validation_ranking_top_eligible == "a1"
    assert controller.state.validation_ranking_top_descriptive == "b2"
