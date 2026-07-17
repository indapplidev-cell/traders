from __future__ import annotations

from app.engine_execution import ExecutionIntentBuilder, ExecutionMode, InMemoryIdempotencyRegistry


def build(payload, mode="DRY_RUN", registry=None):
    return ExecutionIntentBuilder(registry=registry).build(
        payload["strategy_decision"], payload["risk_decision"], payload["setup_context"],
        mode, payload["source_window"],
    )


def test_approved_strategy_and_risk_create_ready_intent(approved_payload):
    intent = build(approved_payload)
    assert intent.status.value == "READY"
    assert intent.reason_codes == ("EXECUTION_INTENT_READY",)


def test_rejected_strategy_is_not_ready(payload_copy):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = "REJECTED"
    intent = build(payload)
    assert intent.status.value == "REJECTED"
    assert "STRATEGY_NOT_APPROVED" in intent.reason_codes


def test_rejected_risk_is_not_ready(payload_copy):
    payload = payload_copy()
    payload["risk_decision"]["risk_status"] = "REJECTED"
    intent = build(payload)
    assert "RISK_NOT_APPROVED" in intent.reason_codes


def test_live_is_always_disabled(approved_payload):
    intent = build(approved_payload, ExecutionMode.LIVE)
    assert intent.status.value == "DISABLED"
    assert "LIVE_EXECUTION_DISABLED" in intent.reason_codes


def test_paper_and_dry_run_are_allowed(payload_copy):
    assert build(payload_copy(), "PAPER").status.value == "READY"
    assert build(payload_copy(), "DRY_RUN").status.value == "READY"


def test_non_positive_quantity_is_rejected(payload_copy):
    for quantity in ("0", "-0.1"):
        payload = payload_copy()
        payload["setup_context"]["quantity"] = quantity
        assert "INVALID_QUANTITY" in build(payload).reason_codes


def test_nan_and_infinity_are_rejected(payload_copy):
    for field in ("reference_price", "stop_price", "target_price"):
        for invalid in ("NaN", "Infinity", "-Infinity"):
            payload = payload_copy()
            payload["setup_context"][field] = invalid
            assert "INVALID_PRICE" in build(payload).reason_codes


def test_wrong_stop_for_long_and_short(payload_copy):
    long_payload = payload_copy()
    long_payload["setup_context"]["stop_price"] = "101"
    assert "INVALID_STOP_PLACEMENT" in build(long_payload).reason_codes

    short_payload = payload_copy()
    for section in ("strategy_decision", "risk_decision", "setup_context"):
        short_payload[section]["side"] = "SELL"
    short_payload["setup_context"].update(stop_price="99", target_price="90")
    assert "INVALID_STOP_PLACEMENT" in build(short_payload).reason_codes


def test_wrong_target_for_long_and_short(payload_copy):
    long_payload = payload_copy()
    long_payload["setup_context"]["target_price"] = "99"
    assert "INVALID_TARGET_PLACEMENT" in build(long_payload).reason_codes

    short_payload = payload_copy()
    for section in ("strategy_decision", "risk_decision", "setup_context"):
        short_payload[section]["side"] = "SELL"
    short_payload["setup_context"].update(stop_price="110", target_price="101")
    assert "INVALID_TARGET_PLACEMENT" in build(short_payload).reason_codes


def test_symbol_and_side_mismatches_are_rejected(payload_copy):
    symbol_payload = payload_copy()
    symbol_payload["risk_decision"]["symbol"] = "ETHUSDT"
    assert "SYMBOL_MISMATCH" in build(symbol_payload).reason_codes
    side_payload = payload_copy()
    side_payload["risk_decision"]["side"] = "SELL"
    assert "SIDE_MISMATCH" in build(side_payload).reason_codes


def test_unclosed_or_missing_window_is_rejected(payload_copy):
    payload = payload_copy()
    payload["source_window"]["is_closed"] = False
    assert "SOURCE_WINDOW_NOT_CLOSED" in build(payload).reason_codes
    payload = payload_copy()
    payload["source_window"] = {}
    assert "MISSING_SOURCE_WINDOW" in build(payload).reason_codes


def test_idempotency_is_deterministic_and_duplicate_is_marked(payload_copy):
    registry = InMemoryIdempotencyRegistry()
    first = build(payload_copy(), registry=registry)
    second = build(payload_copy(), registry=registry)
    assert first.idempotency_key == second.idempotency_key
    assert first.execution_intent_id == second.execution_intent_id
    assert second.status.value == "DUPLICATE"
    assert second.reason_codes == ("DUPLICATE_EXECUTION_INTENT",)


def test_legacy_project_approval_names_are_supported(payload_copy):
    payload = payload_copy()
    payload["strategy_decision"]["decision_status"] = "ALLOW_RESEARCH_TRADE_PLAN"
    payload["risk_decision"]["risk_status"] = "RISK_PRE_APPROVED_RESEARCH"
    assert build(payload).status.value == "READY"
