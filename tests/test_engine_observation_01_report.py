from app.engine_observation.observation_report import render_markdown


def test_report_separates_operational_and_research_results():
    report = {"summary": {"verdict": "OBSERVATION_PASSED", "start_utc": "a", "end_utc": "b",
        "freshness_skip_count": 0, "error_count": 0, "stale_reservation_count": 0,
        "failures": [], "recommended_next_stage": "B"}, "coverage": {"by_symbol": {}},
        "funnel": {}, "reasons": {}, "latency": {}, "integrity": {}, "safety": {},
        "runtime": {}, "sync_state": {}}
    text = render_markdown(report)
    assert "Operational blockers" in text
    assert "Research observations" in text
    assert "NO_PLAN" in text
