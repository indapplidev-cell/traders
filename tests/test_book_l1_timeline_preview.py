from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.multi_symbol_preview import DEFAULT_MULTI_SYMBOLS
from app.market_reader.timeline_interactive import prompt_timeline_config
from app.market_reader.timeline_preview import (
    TimelinePreviewConfig,
    TimelinePreviewResult,
    TimelinePreviewRunner,
    TimelinePreviewTableFormatter,
    TimelineSymbolRow,
    TimelineWindowSnapshot,
    build_window_labels,
    classify_timeline_stability,
    summarize_timeline_result,
)


def test_timeline_preview_config_defaults() -> None:
    config = TimelinePreviewConfig()

    assert config.symbols == DEFAULT_MULTI_SYMBOLS
    assert config.interval == "15m"
    assert config.window_size == 300
    assert config.window_count == 4
    assert config.min_candles == 50
    assert config.required_candles == 1200


def test_window_count_validation() -> None:
    with pytest.raises(ValueError):
        TimelinePreviewConfig(window_count=1)

    assert TimelinePreviewConfig(window_count=2).window_count == 2
    assert TimelinePreviewConfig(window_count=6).window_count == 6

    with pytest.raises(ValueError):
        TimelinePreviewConfig(window_count=7)


def test_build_window_labels() -> None:
    assert build_window_labels(2) == ("W-1", "Current")
    assert build_window_labels(3) == ("W-2", "W-1", "Current")
    assert build_window_labels(4) == ("W-3", "W-2", "W-1", "Current")


def test_classify_timeline_stability() -> None:
    assert classify_timeline_stability(("FLAT", "FLAT", "FLAT", "FLAT")) == "STABLE"
    assert classify_timeline_stability(("FLAT", "FLAT", "UP", "UP")) == "CHANGING"
    assert classify_timeline_stability(("DOWN", "FLAT", "UP", "UNKNOWN")) == "UNSTABLE"
    assert classify_timeline_stability(()) == "ERROR"


def test_runner_requests_window_size_times_window_count_candles() -> None:
    repository = FakeRepository({"BTCUSDT": _make_candles(20)})
    runner = TimelinePreviewRunner(
        candle_repository=repository,
        market_reader=FakeReader(["FLAT", "FLAT", "UP", "UP"]),
    )

    runner.run(TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3))

    assert repository.calls == [("BTCUSDT", "15m", 20)]


def test_runner_splits_candles_into_non_overlapping_windows() -> None:
    reader = FakeReader(["FLAT", "FLAT", "UP", "UP"])
    runner = TimelinePreviewRunner(
        candle_repository=FakeRepository({"BTCUSDT": _make_candles(20)}),
        market_reader=reader,
    )

    result = runner.run(TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3))

    assert result.rows[0].status == "OK"
    assert [window.window_label for window in result.rows[0].windows] == ["W-3", "W-2", "W-1", "Current"]
    assert reader.windows[0].first_open_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert reader.windows[0].last_open_time == datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc)
    assert reader.windows[1].first_open_time == datetime(2026, 1, 1, 1, 15, tzinfo=timezone.utc)
    assert reader.windows[3].last_open_time == datetime(2026, 1, 1, 4, 45, tzinfo=timezone.utc)
    assert all(current.first_open_time > previous.last_open_time for previous, current in zip(reader.windows, reader.windows[1:]))


def test_runner_analyzes_each_window_through_fake_market_reader() -> None:
    reader = FakeReader(["FLAT", "FLAT", "UP", "UP"])
    runner = TimelinePreviewRunner(
        candle_repository=FakeRepository({"BTCUSDT": _make_candles(20)}),
        market_reader=reader,
    )

    result = runner.run(TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3))

    assert len(reader.windows) == 4
    assert result.rows[0].regimes == ("FLAT", "FLAT", "UP", "UP")
    assert result.rows[0].current_confidence == 0.74


def test_runner_marks_insufficient_data_without_failing_other_symbols() -> None:
    runner = TimelinePreviewRunner(
        candle_repository=FakeRepository({"BTCUSDT": _make_candles(19)}),
        market_reader=FakeReader(["FLAT", "FLAT", "UP", "UP"]),
    )

    result = runner.run(TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3))

    row = result.rows[0]
    assert row.status == "INSUFFICIENT_DATA"
    assert row.regimes == ("UNKNOWN", "UNKNOWN", "UNKNOWN", "UNKNOWN")
    assert row.last_transition == "ERROR"
    assert row.current_confidence == 0.0
    assert row.warning == "required 20 candles, found 19."
    assert "BTCUSDT: required 20 candles, found 19." in result.warnings


def test_one_symbol_error_does_not_break_remaining_symbols() -> None:
    repository = FakeRepository(
        {
            "BTCUSDT": _make_candles(20),
            "ETHUSDT": RuntimeError("repository failed"),
            "SOLUSDT": _make_candles(20),
        }
    )
    runner = TimelinePreviewRunner(
        candle_repository=repository,
        market_reader=FakeReader(["FLAT", "UP", "UP", "UP", "DOWN", "FLAT", "FLAT", "FLAT"]),
    )

    result = runner.run(
        TimelinePreviewConfig(
            symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
            window_size=5,
            window_count=4,
            min_candles=3,
        )
    )

    assert [row.status for row in result.rows] == ["OK", "ERROR", "OK"]
    assert result.rows[0].last_transition == "NO_CHANGE"
    assert result.rows[1].last_transition == "ERROR"
    assert result.rows[2].last_transition == "NO_CHANGE"


def test_transitions_are_calculated_between_adjacent_windows() -> None:
    runner = TimelinePreviewRunner(
        candle_repository=FakeRepository({"BTCUSDT": _make_candles(20)}),
        market_reader=FakeReader(["FLAT", "UP", "UP", "UNKNOWN"]),
    )

    result = runner.run(TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3))

    row = result.rows[0]
    assert row.transitions == ("FLAT_TO_UP", "NO_CHANGE", "TO_UNKNOWN")
    assert row.last_transition == "TO_UNKNOWN"


def test_table_formatter_contains_expected_columns() -> None:
    report = TimelinePreviewTableFormatter().format_result(
        TimelinePreviewResult(
            config=TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3),
            rows=(_row("BTCUSDT", ("FLAT", "FLAT", "UP", "UP"), ("NO_CHANGE", "FLAT_TO_UP", "NO_CHANGE")),),
        )
    )

    assert "Symbol" in report
    assert "Status" in report
    assert "Current" in report
    assert "Stability" in report
    assert "Last Change" in report
    assert "Safety" in report


def test_summary_counts_current_regimes_and_stability() -> None:
    result = TimelinePreviewResult(
        config=TimelinePreviewConfig(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")),
        rows=(
            _row("BTCUSDT", ("FLAT", "FLAT", "UP", "UP"), ("NO_CHANGE", "FLAT_TO_UP", "NO_CHANGE")),
            _row("ETHUSDT", ("DOWN", "FLAT", "FLAT", "UNKNOWN"), ("DOWN_TO_FLAT", "NO_CHANGE", "TO_UNKNOWN")),
            _row("SOLUSDT", ("FLAT", "FLAT", "FLAT", "FLAT"), ("NO_CHANGE", "NO_CHANGE", "NO_CHANGE")),
        ),
    )

    summary = summarize_timeline_result(result)

    assert summary["current_UP"] == 1
    assert summary["current_FLAT"] == 1
    assert summary["current_UNKNOWN"] == 1
    assert summary["stability_CHANGING"] == 1
    assert summary["stability_UNSTABLE"] == 1
    assert summary["stability_STABLE"] == 1


def test_safety_is_always_fail_closed() -> None:
    row = _row("BTCUSDT", ("FLAT", "FLAT", "UP", "UP"), ("NO_CHANGE", "FLAT_TO_UP", "NO_CHANGE"))

    assert row.trade_signal == "NOT_EVALUATED"
    assert row.safe_for_runtime_trading is False
    assert "trade_signal: NOT_EVALUATED" in TimelinePreviewTableFormatter().format_safety()
    assert "safe_for_runtime_trading: false" in TimelinePreviewTableFormatter().format_safety()


def test_non_interactive_cli_mode_does_not_call_input(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummySessionContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    class DummyRepository:
        def __init__(self, session: object) -> None:
            captured["session"] = session

    class DummyRunner:
        def __init__(self, *, candle_repository: object, market_reader: object | None = None) -> None:
            captured["repository"] = candle_repository
            captured["market_reader"] = market_reader

        def run(self, config: TimelinePreviewConfig) -> TimelinePreviewResult:
            captured["config"] = config
            return TimelinePreviewResult(
                config=config,
                rows=(_row("BTCUSDT", ("FLAT", "FLAT", "UP", "UP"), ("NO_CHANGE", "FLAT_TO_UP", "NO_CHANGE")),),
            )

    def fail_input(prompt: str = "") -> str:
        raise AssertionError("input() must not be called in non-interactive mode")

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)
    monkeypatch.setattr("builtins.input", fail_input)

    import app.market_reader.timeline_preview as timeline_preview_module

    monkeypatch.setattr(timeline_preview_module, "TimelinePreviewRunner", DummyRunner)

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-timeline-preview",
            "--symbols",
            "BTCUSDT,ETHUSDT,SOLUSDT",
            "--interval",
            "15m",
            "--window-size",
            "300",
            "--window-count",
            "4",
            "--min-candles",
            "50",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "BOOK-L1 Market Regime Timeline Preview" in result.stdout
    config = captured["config"]
    assert isinstance(config, TimelinePreviewConfig)
    assert config.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert config.interval == "15m"
    assert config.window_size == 300
    assert config.window_count == 4
    assert config.min_candles == 50


def test_show_details_adds_reason_codes() -> None:
    result = TimelinePreviewResult(
        config=TimelinePreviewConfig(symbols=("BTCUSDT",), window_size=5, window_count=4, min_candles=3),
        rows=(_row("BTCUSDT", ("FLAT", "FLAT", "UP", "UP"), ("NO_CHANGE", "FLAT_TO_UP", "NO_CHANGE")),),
    )

    report = TimelinePreviewTableFormatter().format_result(result, show_details=True)

    assert "BTCUSDT timeline details" in report
    assert "W-3:" in report
    assert "Current:" in report
    assert "FLAT_REASON" in report
    assert "UP_REASON" in report


def test_interactive_enter_selects_defaults() -> None:
    prompts: list[str] = []

    config = prompt_timeline_config(
        input_func=_input_from(["", "", "", "", ""]),
        output_func=prompts.append,
    )

    assert config == TimelinePreviewConfig()
    assert any("Enter without input = option 1" in prompt for prompt in prompts)


class FakeRepository:
    def __init__(self, candles_by_symbol: dict[str, list[Any] | Exception]) -> None:
        self.candles_by_symbol = candles_by_symbol
        self.calls: list[tuple[str, str, int]] = []

    def get_last_n(self, *, symbol: str, interval: str, limit: int) -> list[Any]:
        self.calls.append((symbol, interval, limit))
        value = self.candles_by_symbol.get(symbol, [])
        if isinstance(value, Exception):
            raise value
        return list(value)[-limit:]


class FakeReader:
    def __init__(self, regimes: list[str]) -> None:
        self.regimes = list(regimes)
        self.windows: list[Any] = []

    def analyze(self, window: Any) -> SimpleNamespace:
        self.windows.append(window)
        regime = self.regimes.pop(0)
        return SimpleNamespace(
            symbol=window.symbol,
            interval=window.interval,
            market_regime=regime,
            directional_bias="BULLISH" if regime == "UP" else "NEUTRAL",
            confidence=0.74,
            trend_strength="MODERATE" if regime in {"UP", "DOWN"} else "NONE",
            reason_codes=(f"{regime}_REASON",),
            trade_signal="NOT_EVALUATED",
            safe_for_runtime_trading=False,
        )


def _make_candles(count: int) -> list[SimpleNamespace]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles: list[SimpleNamespace] = []
    for index in range(count):
        base = 100.0 + index
        candles.append(
            SimpleNamespace(
                open_time=start + timedelta(minutes=15 * index),
                open=base,
                high=base + 1.0,
                low=base - 1.0,
                close=base + 0.5,
                volume=1000.0,
            )
        )
    return candles


def _row(symbol: str, regimes: tuple[str, ...], transitions: tuple[str, ...]) -> TimelineSymbolRow:
    windows = tuple(
        TimelineWindowSnapshot(
            symbol=symbol,
            window_label=label,
            market_regime=regime,
            directional_bias="BULLISH" if regime == "UP" else "NEUTRAL",
            confidence=0.74 if regime != "UNKNOWN" else 0.41,
            trend_strength="MODERATE" if regime in {"UP", "DOWN"} else "NONE",
            trade_signal="NOT_EVALUATED",
            safe_for_runtime_trading=False,
            candle_count=5,
            first_open_time="2026-06-10T14:15:00+00:00",
            last_open_time="2026-06-10T15:15:00+00:00",
            reason_codes=(f"{regime}_REASON",),
        )
        for label, regime in zip(build_window_labels(len(regimes)), regimes)
    )
    return TimelineSymbolRow(
        symbol=symbol,
        status="OK",
        windows=windows,
        regimes=regimes,
        transitions=transitions,
        last_transition=transitions[-1],
        stability=classify_timeline_stability(regimes),
        current_confidence=windows[-1].confidence,
        current_trend_strength=windows[-1].trend_strength,
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
    )


def _input_from(values: list[str]):
    answers = iter(values)

    def input_func(prompt: str = "") -> str:
        return next(answers)

    return input_func
