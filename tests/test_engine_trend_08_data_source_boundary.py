from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataBatch,
    CandleDataBoundaryResult,
    CandleDataBoundaryStatus,
    CandleDataQualityFlag,
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_batch,
    run_engine_trend_from_provider,
    validate_candle_data_request,
)
from app.market_reader.engine_trend.schemas import EngineTrendRegime


def sample_rows() -> list[dict[str, object]]:
    return [
        {"timestamp": "2026-01-01T00:00:00", "open": 100, "high": 103, "low": 99, "close": 102, "volume": 1000},
        {"timestamp": "2026-01-01T00:15:00", "open": 102, "high": 106, "low": 101, "close": 105, "volume": 1200},
        {"timestamp": "2026-01-01T00:30:00", "open": 105, "high": 107, "low": 103, "close": 104, "volume": 1100},
        {"timestamp": "2026-01-01T00:45:00", "open": 104, "high": 109, "low": 104, "close": 108, "volume": 1300},
        {"timestamp": "2026-01-01T01:00:00", "open": 108, "high": 112, "low": 107, "close": 111, "volume": 1400},
        {"timestamp": "2026-01-01T01:15:00", "open": 111, "high": 113, "low": 109, "close": 110, "volume": 1000},
        {"timestamp": "2026-01-01T01:30:00", "open": 110, "high": 115, "low": 110, "close": 114, "volume": 1500},
    ]


def request(**changes: object) -> CandleDataRequest:
    values: dict[str, object] = {"symbol": "SYNTH", "interval": "15m", "limit": 7}
    values.update(changes)
    return CandleDataRequest(**values)  # type: ignore[arg-type]


def test_valid_request_has_dictionary_export() -> None:
    payload = request(start_time="a", end_time="b").to_dict()
    assert payload["symbol"] == "SYNTH"
    assert payload["source_name"] == "external_provider"


def test_request_validation() -> None:
    assert validate_candle_data_request(request(symbol="")) == ("REQUEST_SYMBOL_EMPTY",)
    assert validate_candle_data_request(request(interval="")) == ("REQUEST_INTERVAL_EMPTY",)
    assert validate_candle_data_request(request(limit=0)) == ("REQUEST_LIMIT_NOT_POSITIVE",)


def test_builds_ready_batch_with_metadata_and_export() -> None:
    batch = build_candle_data_batch(request(), sample_rows())
    assert batch.status is CandleDataBoundaryStatus.READY
    assert len(batch.candles) == 7
    assert batch.metadata["row_count"] == 7
    assert batch.metadata["candle_count"] == 7
    payload = batch.to_dict()
    assert {"request", "status", "quality_flags", "metadata"} <= payload.keys()


def test_empty_and_invalid_batches() -> None:
    empty = build_candle_data_batch(request(), [])
    assert empty.status is CandleDataBoundaryStatus.EMPTY
    assert CandleDataQualityFlag.EMPTY_BATCH in empty.quality_flags
    invalid = build_candle_data_batch(request(symbol=""), sample_rows())
    assert invalid.status is CandleDataBoundaryStatus.INVALID_REQUEST
    assert not invalid.candles


def test_bad_row_fails_normalization() -> None:
    batch = build_candle_data_batch(request(), [{"timestamp": "x"}])
    assert batch.status is CandleDataBoundaryStatus.VALIDATION_FAILED
    assert CandleDataQualityFlag.CANDLE_NORMALIZATION_FAILED in batch.quality_flags
    assert not batch.candles


def test_quality_flags_preserve_usable_candles() -> None:
    rows = sample_rows()[:2]
    rows.reverse()
    rows.append(dict(rows[-1]))
    batch = build_candle_data_batch(request(), rows, min_candle_count=4)
    assert batch.status is CandleDataBoundaryStatus.VALIDATION_FAILED
    assert CandleDataQualityFlag.MIN_CANDLE_COUNT_NOT_MET in batch.quality_flags
    assert CandleDataQualityFlag.UNSORTED_TIMESTAMPS in batch.quality_flags
    assert CandleDataQualityFlag.DUPLICATE_TIMESTAMPS in batch.quality_flags
    assert batch.errors


class FakeProvider:
    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.calls = 0

    def load_rows(self, requested: CandleDataRequest) -> tuple[dict[str, object], ...]:
        self.calls += 1
        if self.fails:
            raise RuntimeError("synthetic provider failure")
        assert requested.symbol == "SYNTH"
        return tuple(sample_rows())


def test_provider_boundary_runs_engine() -> None:
    provider = FakeProvider()
    result = run_engine_trend_from_provider(provider, request())
    assert provider.calls == 1
    assert isinstance(result, CandleDataBoundaryResult)
    assert result.engine_output.composer_output.result.market_regime in set(EngineTrendRegime)


def test_provider_failure_returns_safe_unknown() -> None:
    result = run_engine_trend_from_provider(FakeProvider(fails=True), request())
    engine_result = result.engine_output.composer_output.result
    assert result.status is CandleDataBoundaryStatus.PROVIDER_ERROR
    assert engine_result.market_regime is EngineTrendRegime.UNKNOWN
    assert engine_result.safety.safe_for_runtime_trading is False
    assert engine_result.safety.live_trading_connected is False


def test_batch_boundary_has_presentations_and_closed_safety() -> None:
    batch = build_candle_data_batch(request(), sample_rows())
    assert isinstance(batch, CandleDataBatch)
    result = run_engine_trend_from_batch(batch)
    assert result.engine_output.preview
    assert result.engine_output.json_payload
    safety = result.engine_output.composer_output.result.safety
    assert safety.safe_for_runtime_trading is False
    assert safety.live_trading_connected is False
