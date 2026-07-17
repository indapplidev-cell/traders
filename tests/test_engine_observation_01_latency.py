from datetime import timedelta
from app.engine_observation.latency_analyzer import analyze_latency, percentile
from tests.engine_observation_01_helpers import START, run


def test_percentiles_and_negative_trigger():
    assert percentile([0, 10, 20], .5) == 10
    audit = analyze_latency([run(started_at=START - timedelta(seconds=1), finished_at=START + timedelta(seconds=1))])
    assert audit["future_boundary_processing_count"] == 1
