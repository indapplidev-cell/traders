from datetime import timedelta
from app.engine_observation.window_coverage_auditor import audit_coverage
from tests.engine_observation_01_helpers import START, run


def test_missing_and_duplicate_detection():
    rows = [run(0), run(0, run_id="duplicate")]
    audit = audit_coverage(rows, ("BTCUSDT",), "15m", START, START + timedelta(minutes=30))
    assert audit["aggregate"]["missing_windows"] == 1
    assert audit["aggregate"]["duplicate_windows"] == 1
