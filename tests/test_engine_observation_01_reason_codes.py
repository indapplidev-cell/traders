from app.engine_observation.reason_code_analyzer import analyze_reasons
from tests.engine_observation_01_helpers import result, run


def test_unknown_payload_fields_are_safe_and_reasons_extracted():
    r = run(final_reason="NO_PLAN")
    analysis = analyze_reasons([r], [result(r, analysis_payload_json={"unknown": [1, 2]},
                                            paper_payload_json={"plan_reasons": ["LOW_PLANNED_RR"]})])
    assert analysis["final"]["top"][0]["reason"] == "NO_PLAN"
    assert analysis["paper"]["top"][0]["reason"] in {"NO_VALID_PLAN", "LOW_PLANNED_RR"}
