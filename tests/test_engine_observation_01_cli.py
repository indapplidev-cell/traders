from scripts.engine_online_pipeline_observation import build_parser
from datetime import datetime, timezone

from app.engine_observation.observation_config import ObservationConfig
from app.engine_observation.observation_runner import ObservationRunner


def test_cli_supports_required_options():
    args = build_parser().parse_args(["--last-hours", "24", "--dry-run", "--fail-on-warning"])
    assert args.last_hours == 24 and args.dry_run and args.fail_on_warning


def test_dry_run_does_not_load_data_or_write_artifacts(tmp_path):
    class Repository:
        def check_connection_and_schema(self): return {"schema_ok": True}
        def availability(self, symbols, timeframe):
            return {"first_utc": datetime(2026, 7, 15, tzinfo=timezone.utc),
                    "latest_utc": datetime(2026, 7, 16, tzinfo=timezone.utc)}
        def load_runs(self, *args): raise AssertionError("dry-run loaded runtime rows")

    config = ObservationConfig(last_hours=24, output_dir=tmp_path / "must-not-exist")
    report = ObservationRunner(config, Repository()).run(dry_run=True,
        now=datetime(2026, 7, 16, 12, tzinfo=timezone.utc))
    assert report["artifacts_written"] is False
    assert not config.output_dir.exists()
