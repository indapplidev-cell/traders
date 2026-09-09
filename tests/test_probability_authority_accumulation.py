import json

from app.engine_observation.scalping_prospective_collector import (
    PROBABILITY_OUTCOME_SEMANTICS,
    evaluate_outcome,
)
from app.engine_paper.scalping_policy_v2 import evaluate_expectancy
from app.engine_paper.scalping_statistics import (
    load_prospective_outcomes,
    hierarchy_from_outcomes,
)
from scripts.forensic_probability_authority import classify_eta


def _write_segment(root, *, set_id="scalping-v2-set-2", count=20, wins=12):
    segment = "segment-set2"
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "segments": [{"observation_segment_id": segment, "homogeneity_identity": {
            "parameter_set_id": set_id,
            "outcome_semantics_version": PROBABILITY_OUTCOME_SEMANTICS,
        }}],
        "parts": [{"kind": "outcomes", "observation_segment_id": segment,
                   "path": "outcomes.jsonl"}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rows = []
    for index in range(count):
        rows.append(json.dumps({
            "completed_at": f"2026-09-08T{index // 60:02d}:{index % 60:02d}:00Z",
            "baseline_outcome": "TP_FIRST" if index < wins else "SL_FIRST",
            "frozen_opportunity": {
                "symbol": "BTCUSDT" if index == 0 else "ETHUSDT",
                "setup_type": "SCALP_BREAKOUT", "direction": "BULLISH",
                "regime": "UP", "cost_bucket": "MEDIUM",
            },
        }))
    (root / "outcomes.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_set_identity_and_semantics_filter_are_fail_closed(tmp_path):
    _write_segment(tmp_path, count=20)
    assert len(load_prospective_outcomes(tmp_path, parameter_set_id="scalping-v2-set-2")) == 20
    assert load_prospective_outcomes(tmp_path, parameter_set_id="scalping-v2-set-1") == ()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    manifest["segments"][0]["homogeneity_identity"]["outcome_semantics_version"] = "legacy"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert load_prospective_outcomes(tmp_path, parameter_set_id="scalping-v2-set-2") == ()


def test_loader_deduplicates_opportunity_across_lineage_segments(tmp_path):
    segments = ("segment-before-provenance", "segment-after-provenance")
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "manifest.json").write_text(json.dumps({
        "segments": [{
            "observation_segment_id": segment,
            "homogeneity_identity": {
                "parameter_set_id": "scalping-v2-set-2",
                "outcome_semantics_version": PROBABILITY_OUTCOME_SEMANTICS,
            },
        } for segment in segments],
        "parts": [{
            "kind": "outcomes",
            "observation_segment_id": segment,
            "path": f"outcomes-{index}.jsonl",
        } for index, segment in enumerate(segments)],
    }), encoding="utf-8")
    for index, segment in enumerate(segments):
        (tmp_path / f"outcomes-{index}.jsonl").write_text(json.dumps({
            "baseline_outcome": "TP_FIRST",
            "completed_at": "2026-09-09T00:00:00Z",
            "frozen_opportunity": {
                "opportunity_id": "opportunity:stable-across-segments",
                "symbol": "BTCUSDT",
                "setup_type": "SCALP_MOMENTUM_CONTINUATION",
                "direction": "BULLISH",
                "regime": "TREND",
                "cost_bucket": "LOW",
            },
            "observation_segment_id": segment,
        }) + "\n", encoding="utf-8")

    outcomes = load_prospective_outcomes(
        tmp_path, parameter_set_id="scalping-v2-set-2",
    )

    assert len(outcomes) == 1


def test_threshold_minus_one_then_threshold_and_parent_fallback(tmp_path):
    _write_segment(tmp_path, count=19, wins=12)
    rows = load_prospective_outcomes(tmp_path, parameter_set_id="scalping-v2-set-2")
    before = hierarchy_from_outcomes(
        rows, symbol="ADAUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="MEDIUM",
        parameter_set_id="scalping-v2-set-2",
    )
    insufficient = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=before.exact,
        parent_buckets=before.parents, minimum_samples=20,
    )
    assert insufficient.reason == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"
    assert insufficient.sample_size == 0
    assert insufficient.parent_sample_size == 19

    _write_segment(tmp_path, count=20, wins=13)
    rows = load_prospective_outcomes(tmp_path, parameter_set_id="scalping-v2-set-2")
    after = hierarchy_from_outcomes(
        rows, symbol="ADAUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="MEDIUM",
        parameter_set_id="scalping-v2-set-2",
    )
    authoritative = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=after.exact,
        parent_buckets=after.parents, minimum_samples=20,
    )
    assert authoritative.fallback_level == "setup_direction_regime"
    assert authoritative.sample_size == 20
    assert authoritative.p_win_conservative is not None


def test_time_stop_label_uses_net_cost_and_same_candle_is_not_authority(tmp_path):
    followup = {
        "boundary_time_ms": 1_000_000, "entry_reference": 100,
        "ttl_ms": 30_000, "time_stop_ms": 120_000,
        "direction": "LONG", "baseline_stop": 90, "baseline_target": 120,
        "effective_total_cost_bps": 30,
    }
    candles = [
        {"open_time_ms": 1_000_000, "close_time_ms": 1_059_999,
         "open": 100, "high": 101, "low": 99, "close": 100.1},
        {"open_time_ms": 1_060_000, "close_time_ms": 1_119_999,
         "open": 100.1, "high": 101, "low": 99, "close": 100.2},
    ]
    value = evaluate_outcome(followup, candles)
    assert value["baseline_outcome"] == "TIME_EXPIRED"
    assert value["gross_return_bps"] > 0
    assert value["net_return_bps"] < 0


def test_zero_accumulation_has_no_invented_probability():
    empty = hierarchy_from_outcomes(
        (), symbol="BTCUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="MEDIUM",
        parameter_set_id="scalping-v2-set-2",
    )
    decision = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=empty.exact,
        parent_buckets=empty.parents, minimum_samples=20, static_net_rr=99,
    )
    assert decision.probability is None
    assert decision.dynamic_required_net_rr is None
    assert decision.reason == "INSUFFICIENT_STATISTICAL_AUTHORITY_NO_TRADE"


def test_eta_classes_and_zero_denominator_are_explicit():
    assert classify_eta(0, 20, 0) == ("NO_OBSERVED_ACCUMULATION", None)
    assert classify_eta(18, 20, 1) == ("LT_6H", 2.0)
    assert classify_eta(20, 20, 0) == ("READY", 0.0)
