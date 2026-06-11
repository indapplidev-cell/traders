import json

from app.audit.final_readiness_reporter import FinalReadinessReporter


def test_final_readiness_reporter_builds_full_report() -> None:
    reporter = FinalReadinessReporter()

    payload = reporter.build_full_report()

    assert payload["audit_name"] == "traders_ml_final_standalone_readiness_audit"
    assert payload["status"] == "READY_STANDALONE"
    assert payload["components"]
    assert payload["safety_boundaries"]
    assert payload["capabilities"]
    assert payload["known_limits"]
    assert payload["next_steps"]


def test_final_readiness_reporter_builds_compact_summary() -> None:
    reporter = FinalReadinessReporter()

    payload = reporter.build_compact_summary()

    assert "components" not in payload
    assert payload["standalone_ml_service_ready"] is True
    assert payload["ready_component_count"] > 0
    assert payload["needs_attention_component_count"] == 0
    assert payload["traders_core_connected"] is False
    assert payload["live_trading_connected"] is False
    assert payload["orders_enabled"] is False


def test_final_readiness_reporter_json_serialization_works() -> None:
    reporter = FinalReadinessReporter()

    full_report = json.loads(reporter.full_report_to_json())
    compact_summary = json.loads(reporter.compact_summary_to_json())

    assert full_report["status"] == "READY_STANDALONE"
    assert compact_summary["status"] == "READY_STANDALONE"
