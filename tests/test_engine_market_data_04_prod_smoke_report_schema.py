from app.engine_market_data.prod_smoke import safety_counters, validate_trace_schema


def test_prod_smoke_trace_schema_accepts_complete_failure_report():
    payload = {
        "stage": "ENGINE-MARKET-DATA-04-PROD-SMOKE", "generated_at": "2026-07-15T00:00:00Z",
        "environment": {}, "preconditions": {}, "alembic": {}, "once_mode": {},
        "continuous_mode": {}, "restart_catch_up": {}, "closed_only_validation": {},
        "health_validation": {}, "runtime_independence": {}, "safety_counters": safety_counters(),
        "bug_candidates": [], "final_verdict": "PROD_SMOKE_FAILED", "recommendation": "fix blocker",
        "failure_stage": "ALEMBIC_UPGRADE",
    }
    assert validate_trace_schema(payload) == []


def test_prod_smoke_trace_rejects_success_with_nonzero_safety_counter():
    counters = safety_counters()
    counters["orders_created"] = 1
    payload = {"stage": "ENGINE-MARKET-DATA-04-PROD-SMOKE", "final_verdict": "PROD_SMOKE_PASSED",
               "safety_counters": counters}
    errors = validate_trace_schema(payload)
    assert "non-zero safety counter" in errors
