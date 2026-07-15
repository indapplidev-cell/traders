from app.engine_market_data.historical_backfill_cli import run


class Bomb:
    def __getattr__(self, name):
        raise AssertionError(f"unexpected dependency access: {name}")


def test_dry_run_does_not_access_database_or_rest_and_writes_reports(tmp_path):
    json_path = tmp_path / "nested" / "report.json"
    md_path = tmp_path / "report.md"
    report = run(["--symbols", "BTCUSDT", "--timeframes", "1m", "--limit-1m", "2",
                  "--dry-run", "--report-json", str(json_path), "--report-md", str(md_path)],
                 repository=Bomb(), rest_client=Bomb(), now_ms=600_001)
    assert report.tasks_total == 1 and report.expected_candles_total == 2
    assert json_path.exists() and md_path.exists()


def test_verify_only_does_not_download():
    from engine_market_data_03_helpers import MemoryRepository, RestClient, candle
    repository = MemoryRepository([candle(540_000)])
    rest = RestClient(now_ms=600_001)
    report = run(["--symbols", "BTCUSDT", "--timeframes", "1m", "--limit-1m", "1",
                  "--verify-only"], repository=repository, rest_client=rest, now_ms=rest.now_ms)
    assert report.tasks_noop == 1 and rest.kline_calls == [] and repository.upsert_calls == 0

