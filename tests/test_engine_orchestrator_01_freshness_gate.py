from types import SimpleNamespace

from app.engine_orchestrator.freshness_gate import FreshnessGate
from tests.engine_orchestrator_01_helpers import BOUNDARY


class Repo:
    def __init__(self, bad=None): self.bad = bad
    def list_for(self, symbols, timeframes):
        return [SimpleNamespace(timeframe=tf, status="STALE" if tf == self.bad else "OK",
                                last_stored_close_boundary_ms=BOUNDARY) for tf in timeframes]


def test_gate_blocks_non_ok_lower_timeframe():
    gate = FreshnessGate(Repo("5m"), ("1m", "5m", "15m", "1h"))
    decision = gate.check("BTCUSDT", BOUNDARY)
    assert not decision.allowed
    assert "5m:STATUS_STALE" in decision.reasons
