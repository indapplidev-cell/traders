import json

from app.engine_observation.scalping_prospective_collector import PROBABILITY_OUTCOME_SEMANTICS
from app.engine_paper.scalping_policy_v2 import evaluate_expectancy
from app.engine_paper.scalping_statistics import PostgresPaperOutcomeStatisticsSource


def _evidence(root, count):
    segment = "pg-e2e-set2"
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "segments": [{"observation_segment_id": segment, "homogeneity_identity": {
            "parameter_set_id": "scalping-v2-set-2",
            "outcome_semantics_version": PROBABILITY_OUTCOME_SEMANTICS,
        }}],
        "parts": [{"kind": "outcomes", "observation_segment_id": segment,
                   "path": "outcomes.jsonl"}],
    }), encoding="utf-8")
    (root / "outcomes.jsonl").write_text("\n".join(json.dumps({
        "completed_at": f"2026-09-08T20:{index:02d}:00Z",
        "baseline_outcome": "TP_FIRST" if index < 14 else "SL_FIRST",
        "frozen_opportunity": {
            "symbol": "ETHUSDT", "setup_type": "SCALP_BREAKOUT",
            "direction": "BULLISH", "regime": "UP", "cost_bucket": "MEDIUM",
        },
    }) for index in range(count)) + "\n", encoding="utf-8")


def test_postgres_plus_durable_evidence_threshold_and_parent(
    natural_e2e_sessions, tmp_path,
):
    _evidence(tmp_path, 19)
    source = PostgresPaperOutcomeStatisticsSource(
        natural_e2e_sessions, prospective_outcome_directory=tmp_path,
    )
    before = source.resolve(
        symbol="ADAUSDT", setup_type="SCALP_BREAKOUT", direction="BULLISH",
        regime="UP", cost_bucket="MEDIUM", parameter_set_id="scalping-v2-set-2",
    )
    assert before.parents[0].samples == 19
    assert not evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=before.exact,
        parent_buckets=before.parents, minimum_samples=20,
    ).admitted

    _evidence(tmp_path, 20)
    after = source.resolve(
        symbol="ADAUSDT", setup_type="SCALP_BREAKOUT", direction="BULLISH",
        regime="UP", cost_bucket="MEDIUM", parameter_set_id="scalping-v2-set-2",
    )
    decision = evaluate_expectancy(
        net_win_bps=100, net_loss_bps=40, bucket=after.exact,
        parent_buckets=after.parents, minimum_samples=20,
    )
    assert decision.fallback_level == "setup_direction_regime"
    assert decision.sample_size == 20
    assert source.resolve(
        symbol="ADAUSDT", setup_type="SCALP_BREAKOUT", direction="BULLISH",
        regime="UP", cost_bucket="MEDIUM", parameter_set_id="scalping-v2-set-1",
    ).outcome_count == 0
