from datetime import timedelta
from app.engine_observation.window_coverage_auditor import expected_boundaries
from tests.engine_observation_01_helpers import START


def test_exact_24h_and_half_open_semantics():
    values = expected_boundaries(START, START + timedelta(hours=24))
    assert len(values) == 96
    assert values[0] == int(START.timestamp() * 1000)
    assert values[-1] == int((START + timedelta(hours=23, minutes=45)).timestamp() * 1000)
