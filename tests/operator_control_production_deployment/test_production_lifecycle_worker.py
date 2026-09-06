from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

from app.engine_market_data.candle import Candle
from app.engine_safety.paper_production_control import PersistentState
from app.engine_paper.controlled_worker import PaperLifecycleState
from app.operator_control.production_lifecycle_worker import (
    DEFAULT_POLL_SECONDS,
    ProductionPaperFirstCanaryLifecycleWorker,
    _entry_fill_window_missed,
    _fill_candle,
    lifecycle_poll_seconds,
    _id as lifecycle_id,
)
from app.operator_control.production_executor import ExistingCanaryRuntimeReadiness
from app.operator_control.production_executor import _id as executor_id


class _Lock:
    @contextmanager
    def acquire(self, canary_id):
        assert canary_id
        yield True


class _Store:
    def __init__(self, current=None):
        self.value = current
        self.refreshed = None

    def current(self):
        return self.value

    def get(self, _canary_id):
        return self.value

    def refresh_terminal(self, canary_id, **values):
        self.refreshed = (canary_id, values)
        return SimpleNamespace(state=SimpleNamespace(value="COMPLETED"))


def test_closed_candle_conversion_preserves_exact_one_minute_boundary():
    source = Candle(
        symbol="BTCUSDT", timeframe="1m", open_time_ms=60_000,
        close_time_ms=119_999, open="100", high="102", low="99", close="101",
        volume="3", is_closed=True, source="production-db",
    )
    converted = _fill_candle(source)
    assert converted.open_time_ms == 60_000
    assert converted.close_boundary_ms == 120_000
    assert converted.observed_closed_until_ms == 120_000
    assert converted.is_closed is True


def test_entry_fill_window_missed_detects_temporal_regression():
    candle = SimpleNamespace(close_boundary_ms=120_000)
    timely = SimpleNamespace(updated_at=datetime.fromtimestamp(119.999, timezone.utc))
    late = SimpleNamespace(updated_at=datetime.fromtimestamp(120.001, timezone.utc))

    assert _entry_fill_window_missed(timely, candle) is False
    assert _entry_fill_window_missed(late, candle) is True


def test_invalid_lifecycle_poll_override_falls_back(monkeypatch):
    monkeypatch.setenv("TRADERS_FIRST_CANARY_LIFECYCLE_POLL_SECONDS", "1")
    assert lifecycle_poll_seconds() == DEFAULT_POLL_SECONDS
    monkeypatch.setenv("TRADERS_FIRST_CANARY_LIFECYCLE_POLL_SECONDS", "15")
    assert lifecycle_poll_seconds() == 15.0


def test_continuous_runtime_ids_do_not_claim_first_canary_identity():
    for identity in (
        executor_id("request", "entry-order", continuous=True),
        lifecycle_id("cycle", "position", continuous=True),
    ):
        assert identity.startswith("paper:continuous:")
        assert "first-canary" not in identity
    assert lifecycle_id("historical", "position").startswith("paper:first-canary:")


def test_worker_without_linked_command_is_strict_zero_action():
    subject = ProductionPaperFirstCanaryLifecycleWorker(
        control=object(), canary_store=_Store(), graph_loader=object(),
        lifecycle_worker=object(), market_data=object(), mutation_safety_gate=object(),
        runtime_readiness=lambda: object(), lock=_Lock(),
        readonly_base_url="http://readonly-api:8765",
    )
    assert subject.run_once() == "NO_COMMAND_READY"


def test_open_position_exit_ignores_entry_approval_and_generation_change(monkeypatch):
    canary = SimpleNamespace(
        canary_id="canary:supervised", command_id="command:supervised",
        command_count=1, max_new_commands=1, max_open_positions=1,
        authority_mode="CONTINUOUS", current_control_generation=12,
        arming_generation=1, arming_transition_id="transition:old",
        environment="PRODUCTION", mode="PAPER", position_count=1,
        state=SimpleNamespace(value="POSITION_OPEN"),
    )
    graph = SimpleNamespace(
        command=SimpleNamespace(symbol="ETHUSDT", risk_decision_id="risk:1"),
        positions=(SimpleNamespace(position_id="position:supervised"),),
    )
    state = SimpleNamespace(
        state=PersistentState.CONTINUOUS_ARMED, generation=13,
        transition_id="transition:new",
    )
    result = SimpleNamespace(
        outcome=SimpleNamespace(value="CYCLE_COMPLETE"), reason_code="NO_TRIGGER",
        initial_lifecycle_state=PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
        final_lifecycle_state=PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
        stages_completed=1, stage_trace=(), position_id="position:supervised",
    )

    class Gate:
        @contextmanager
        def authorize_mutation(self, *_args, **_kwargs):
            yield

    subject = ProductionPaperFirstCanaryLifecycleWorker(
        control=SimpleNamespace(read_authoritative=lambda: state),
        canary_store=_Store(canary),
        graph_loader=SimpleNamespace(load=lambda _command_id: graph),
        lifecycle_worker=SimpleNamespace(run_cycle=lambda _cycle: result),
        market_data=object(), mutation_safety_gate=Gate(),
        runtime_readiness=lambda: ExistingCanaryRuntimeReadiness(
            market_data_ready=True, approval_source_ready=False,
            wal_ready=True, pitr_ready=True, live_disabled=True,
        ),
        lock=_Lock(), readonly_base_url="http://readonly-api:8765",
    )
    monkeypatch.setattr(
        "app.operator_control.production_lifecycle_worker.classify_paper_lifecycle_state",
        lambda _graph: PaperLifecycleState.POSITION_OPEN_CURSOR_READY,
    )
    monkeypatch.setattr(subject, "_current_exit_policy", lambda _command: (object(), "READY"))
    monkeypatch.setattr(subject, "_snapshot", lambda *_args, **_kwargs: ((object(),), "READY"))
    monkeypatch.setattr(subject, "_exit_cycle", lambda *_args, **_kwargs: (object(), "READY"))

    assert subject.run_once().startswith("CYCLE_COMPLETE:POSITION_OPEN_CURSOR_READY")


def test_finalization_disables_before_sealing_healthy_report(monkeypatch):
    calls = []

    class _Control:
        def transition(self, target, **values):
            calls.append((target, values))
            return SimpleNamespace(state=PersistentState.DISABLED, generation=7)

    class _Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return self.payload

    responses = iter((
        _Response(b'{"data":{"total_fees":"0.02","net_pnl":"0.10","roi_percent":"0.1"}}'),
        _Response(b'{"data":{"paper_reconciliation":{"status":"HEALTHY"},'
                  b'"accounting_reconciliation":{"status":"HEALTHY"}}}'),
    ))
    monkeypatch.setattr(
        "app.operator_control.production_lifecycle_worker.urllib.request.urlopen",
        lambda *_args, **_kwargs: next(responses),
    )
    store = _Store()
    subject = ProductionPaperFirstCanaryLifecycleWorker(
        control=_Control(), canary_store=store, graph_loader=object(),
        lifecycle_worker=object(), market_data=object(), mutation_safety_gate=object(),
        runtime_readiness=lambda: object(), lock=_Lock(),
        readonly_base_url="http://readonly-api:8765",
    )
    canary = SimpleNamespace(
        canary_id="6f9858cd-f6b1-4c7f-810c-fccc1065bb9d",
        command_id="command:1", position_id="position:1",
    )
    armed = SimpleNamespace(state=PersistentState.ARMED, generation=6)
    assert subject._finalize(canary, armed) == "FINALIZED:COMPLETED"
    assert calls[0][0] is PersistentState.DISABLED
    assert store.refreshed[1]["report_available"] is True
    assert store.refreshed[1]["paper_reconciliation_status"] == "HEALTHY"
    assert store.refreshed[1]["accounting_reconciliation_status"] == "HEALTHY"
    assert isinstance(store.refreshed[1]["checked_at"], datetime)
    assert store.refreshed[1]["checked_at"].tzinfo is timezone.utc
