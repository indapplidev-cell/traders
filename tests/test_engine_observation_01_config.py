from datetime import datetime, timezone
import pytest

from app.engine_observation.observation_config import ObservationConfig


def test_last_hours_ends_on_last_closed_boundary():
    config = ObservationConfig(last_hours=24)
    start, end = config.interval(datetime(2026, 7, 16, 12, 14, tzinfo=timezone.utc))
    assert end.isoformat() == "2026-07-16T12:00:00+00:00"
    assert (end - start).total_seconds() == 86400


def test_explicit_interval_requires_boundaries():
    with pytest.raises(ValueError):
        ObservationConfig(start_utc=datetime(2026, 7, 16, 0, 1, tzinfo=timezone.utc),
                          end_utc=datetime(2026, 7, 17, tzinfo=timezone.utc), last_hours=None)
