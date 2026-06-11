import json

from app.audit.final_readiness_audit import (
    READY_STANDALONE,
    TRADERS_ML_READINESS_AUDIT_NAME,
    TRADERS_ML_READINESS_AUDIT_VERSION,
    build_final_readiness_audit,
)


def test_final_readiness_audit_result_is_json_safe_and_ready() -> None:
    audit_result = build_final_readiness_audit()
    payload = audit_result.to_dict()

    assert payload["audit_name"] == TRADERS_ML_READINESS_AUDIT_NAME
    assert payload["audit_version"] == TRADERS_ML_READINESS_AUDIT_VERSION
    assert payload["status"] == READY_STANDALONE
    assert payload["components"]
    assert payload["safety_boundaries"]
    assert payload["capabilities"]
    assert payload["known_limits"]
    assert payload["next_steps"]

    json.dumps(payload, ensure_ascii=False, sort_keys=True)


def test_final_readiness_audit_required_safety_flags_are_false() -> None:
    payload = build_final_readiness_audit().to_dict()
    safety_boundaries = payload["safety_boundaries"]

    required_flags = [
        "opens_trades",
        "places_orders",
        "sizes_positions",
        "uses_exchange_api",
        "traders_core_connected",
        "live_trading_connected",
        "orders_enabled",
        "database_writes_for_gate_policy",
        "database_migrations_required",
        "production_deploy_required",
    ]

    for flag in required_flags:
        assert flag in safety_boundaries
        assert safety_boundaries[flag] is False


def test_final_readiness_audit_components_have_no_missing_files() -> None:
    payload = build_final_readiness_audit().to_dict()

    for component in payload["components"].values():
        assert component["missing_files"] == []
