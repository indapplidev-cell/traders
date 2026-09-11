import pytest

from traders_ml.parameter_sweep.artifact_v2 import build_opportunity_funnel


def _result(index, status, trades, rejection):
    return {
        "config_index": index, "config_id": f"c{index}",
        "overrides": {"stop_max_bps": 50 + index},
        "evaluation_status": status, "performance_class": "INSUFFICIENT_SAMPLE",
        "trade_count": trades, "key_rejection_distribution": rejection,
    }


def test_funnel_has_cross_artifact_parity_and_no_null_metadata():
    results = [
        _result(0, "REJECTED", 0, {"REJECT_STOP_MAX_BPS": 2}),
        _result(1, "ACCEPTED", 1, {"PASSED": 1, "REJECT_STOP_MAX_BPS": 1}),
    ]
    artifact = build_opportunity_funnel(
        results, counterfactual_count=1,
        counterfactual_examples=[{
            "opportunity_id": "o1", "baseline_disposition": "HISTORICALLY_REJECTED",
            "counterfactual_config": "c1", "counterfactual_disposition": "SIMULATED_TRADE",
            "reason_changed": "REJECT_STOP_MAX_BPS->TARGET",
        }],
    )
    assert len(artifact["CONFIG_RESULTS"]) == len(results)
    assert artifact["AGGREGATE_FUNNEL"] == {"PASSED": 1, "REJECT_STOP_MAX_BPS": 3}
    assert artifact["COUNTERFACTUAL_REJECTED_OPPORTUNITIES_SIMULATED"] == 1
    for source, funnel in zip(results, artifact["CONFIG_RESULTS"], strict=True):
        assert funnel["status"] == source["evaluation_status"]
        assert funnel["validation_trade_count"] == source["trade_count"]
        assert funnel["rejection_distribution"] == source["key_rejection_distribution"]
        assert all(value is not None for value in funnel.values())


def test_incomplete_result_fails_closed():
    with pytest.raises(ValueError, match="FUNNEL_ARTIFACT_INCOMPLETE"):
        build_opportunity_funnel([{}], counterfactual_count=0, counterfactual_examples=[])
