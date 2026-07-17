from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from app.engine_execution import ExecutionIntentBuilder, ExecutionMode, InMemoryIdempotencyRegistry
from app.engine_execution.idempotency import build_idempotency_key


def args(payload, mode="DRY_RUN"):
    return (payload["strategy_decision"], payload["risk_decision"],
            payload["setup_context"], mode, payload["source_window"])


def test_idempotency_ignores_timestamp_and_metadata(payload_copy):
    first_payload = payload_copy()
    second_payload = payload_copy()
    second_payload["setup_context"]["metadata"] = {"different": [1, 2, 3]}
    first = ExecutionIntentBuilder(
        clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
    ).build(*args(first_payload))
    second = ExecutionIntentBuilder(
        clock=lambda: datetime(2026, 1, 2, tzinfo=timezone.utc),
    ).build(*args(second_payload))
    assert first.created_at_utc != second.created_at_utc
    assert first.idempotency_key == second.idempotency_key


def test_idempotency_mapping_order_and_enum_serialization_are_stable():
    fields = {
        "symbol": "BTCUSDT", "source_timeframe": "15m",
        "source_closed_until_ms": 100, "setup_id": "setup:1",
        "strategy_decision_id": "strategy:1", "risk_decision_id": "risk:1",
        "execution_mode": ExecutionMode.DRY_RUN,
    }
    reversed_fields = dict(reversed(tuple(fields.items())))
    reversed_fields["execution_mode"] = "DRY_RUN"
    assert build_idempotency_key(fields) == build_idempotency_key(reversed_fields)


def test_idempotency_changes_with_window_and_mode(payload_copy):
    original = payload_copy()
    changed = deepcopy(original)
    new_close = original["source_window"]["closed_until_ms"] + 900_000
    changed["source_window"]["closed_until_ms"] = new_close
    changed["strategy_decision"]["closed_until_ms"] = new_close
    changed["risk_decision"]["closed_until_ms"] = new_close
    first = ExecutionIntentBuilder().build(*args(original, "DRY_RUN"))
    window_changed = ExecutionIntentBuilder().build(*args(changed, "DRY_RUN"))
    mode_changed = ExecutionIntentBuilder().build(*args(original, "PAPER"))
    assert len({first.idempotency_key, window_changed.idempotency_key, mode_changed.idempotency_key}) == 3


def test_registry_marks_only_one_concurrent_build_as_new(approved_payload):
    registry = InMemoryIdempotencyRegistry()
    builder = ExecutionIntentBuilder(registry=registry)
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: builder.build(*args(approved_payload)).status.value, range(2)))
    assert sorted(statuses) == ["DUPLICATE", "READY"]


def test_registry_duplicate_contract_is_thread_safe():
    registry = InMemoryIdempotencyRegistry()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: registry.register("same-key"), range(2)))
    assert sorted(results) == [False, True]
