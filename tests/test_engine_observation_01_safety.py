from app.engine_observation.safety_auditor import audit_safety
from tests.engine_observation_01_helpers import result, run


def test_runtime_forbidden_key_and_counter_are_violations():
    r = run(order_approved=True)
    audit = audit_safety([r], [result(r, paper_payload_json={"order_id": "real-1"})])
    assert audit["violation_count"] >= 2
