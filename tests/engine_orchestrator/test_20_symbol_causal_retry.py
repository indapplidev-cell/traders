from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.engine_orchestrator.orchestrator_config import OrchestratorConfig
from app.engine_orchestrator.orchestrator_daemon import OrchestratorDaemon
from app.engine_orchestrator.orchestrator_status import FinalResult, PipelineStatus
from app.engine_orchestrator.pipeline_result import PipelineResult
from app.engine_orchestrator.pipeline_result_store import ClaimedWindow
from app.engine_orchestrator.freshness_gate import FreshnessClassification
from app.trading_universe.domain import SCALPING_TRADING_UNIVERSE


BOUNDARY = 1_900_000_000_000
NOW = datetime.fromtimestamp((BOUNDARY + 35_000) / 1000, timezone.utc)


class Detector:
    def __init__(self):
        self.completed = set()
        self.reserved = set()

    def get_unprocessed_closed_windows(self, symbol):
        if symbol in self.completed or symbol in self.reserved:
            return []
        return [SimpleNamespace(timeframe="5m", closed_until_ms=BOUNDARY)]


class Gate:
    def __init__(self):
        self.preflight_calls = {symbol: 0 for symbol in SCALPING_TRADING_UNIVERSE.symbols}

    def check(self, symbol, *_args, **_kwargs):
        self.preflight_calls[symbol] += 1
        index = SCALPING_TRADING_UNIVERSE.symbols.index(symbol)
        waiting = index >= 12 and self.preflight_calls[symbol] == 1
        classification = (
            FreshnessClassification.WAITING_RETRYABLE.value
            if waiting else FreshnessClassification.READY.value
        )
        return SimpleNamespace(
            status="BOUNDARY_NOT_READY" if waiting else "READY",
            classification=classification,
            reasons=("5m:WAITING",) if waiting else (),
            reason_code="WAITING_FOR_REQUIRED_BOUNDARY" if waiting else None,
            waiting_timeframes=("5m",) if waiting else (),
            payload=lambda: {},
        )


class Store:
    def __init__(self, detector):
        self.detector = detector
        self.claims = {}
        self.finished = []
        self.waiting = []

    def claim_due_waiting(self, **_kwargs):
        due, self.waiting = tuple(self.waiting), []
        return due

    def reserve(self, symbol, timeframe, closed_until_ms, **kwargs):
        run_id = f"run:{symbol}"
        self.claims[run_id] = ClaimedWindow(
            run_id, symbol, timeframe, closed_until_ms,
            kwargs["freshness_deadline_at"], 0, False, "trade-5m-v2",
        )
        self.detector.reserved.add(symbol)
        return run_id

    def get_claim(self, run_id):
        return self.claims[run_id]

    def mark_running(self, *_args, **_kwargs):
        return True

    def mark_waiting(self, claim, **_kwargs):
        self.waiting.append(ClaimedWindow(
            claim.run_id, claim.symbol, claim.primary_timeframe,
            claim.closed_until_ms, claim.freshness_deadline_at,
            claim.freshness_attempt_count + 1, True, claim.trade_profile_id,
        ))
        return True

    def finish(self, run_id, result, **_kwargs):
        self.finished.append(result.symbol)
        self.detector.completed.add(result.symbol)
        self.detector.reserved.discard(result.symbol)
        return True

    def get_latest(self, *_args, **_kwargs):
        return None


class Runner:
    def run(self, symbol, closed_until_ms):
        return PipelineResult(
            symbol=symbol, primary_timeframe="5m",
            closed_until_ms=closed_until_ms,
            trade_profile_id="trade-5m-v2",
            runtime_parameter_set_id="scalping-v2-set-2",
            status=PipelineStatus.COMPLETED.value,
            final_result=FinalResult.NO_ACTION.value,
            final_reason="TEST_TERMINAL",
        )


class Health:
    def build(self, **_kwargs):
        return {}

    def write(self, _payload):
        return None


def test_exact_20_partial_boundary_retries_before_blocking_maintenance(tmp_path):
    symbols = SCALPING_TRADING_UNIVERSE.symbols
    assert len(symbols) == 20
    detector = Detector()
    store = Store(detector)
    maintenance = []
    daemon = OrchestratorDaemon(
        OrchestratorConfig(
            symbols=symbols, trade_profile_id="trade-5m-v2",
            primary_timeframe="5m", required_timeframes=("5m",),
            minimum_windows={"5m": 1},
            poll_interval_seconds=10,
            freshness_retry_interval_seconds=5,
            health_report_path=tmp_path / "health.json",
        ),
        detector, Gate(), Runner(), store,
        health_reporter=Health(),
        cycle_maintenance=lambda: maintenance.append("called"),
        clock=lambda: NOW,
    )

    first = daemon.run_cycle()
    assert len(store.finished) == 12
    assert sum(
        item.get("pipeline_status") == PipelineStatus.WAITING_FOR_REQUIRED_BOUNDARY.value
        for item in first
    ) == 8
    assert daemon._deferred_boundary_retry is True

    second = daemon.run_cycle()
    assert len(second) == 8
    assert tuple(store.finished) == symbols
    assert len(set(store.finished)) == 20
    assert maintenance == ["called"]
    assert daemon._deferred_boundary_retry is False
