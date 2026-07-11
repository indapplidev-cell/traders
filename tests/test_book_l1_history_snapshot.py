from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.history_interactive import prompt_history_interval, prompt_history_symbols
from app.market_reader.history_snapshot import (
    HistorySnapshotConfig,
    HistorySnapshotResult,
    HistorySnapshotRunner,
    HistorySnapshotTableFormatter,
    RegimeTransitionRow,
    RegimeWindowSnapshot,
    classify_regime_transition,
    summarize_history_result,
)
from app.market_reader.multi_symbol_preview import DEFAULT_MULTI_SYMBOLS
from app.market_reader.schemas import DirectionalBias, MarketAnalysisResult, MarketRegime, TradeSignal, TrendStrength


def test_classify_regime_transition_cases() -> None:
    assert classify_regime_transition("FLAT", "UP") == "FLAT_TO_UP"
    assert classify_regime_transition("FLAT", "DOWN") == "FLAT_TO_DOWN"
    assert classify_regime_transition("UP", "FLAT") == "UP_TO_FLAT"
    assert classify_regime_transition("DOWN", "FLAT") == "DOWN_TO_FLAT"
    assert classify_regime_transition("UP", "DOWN") == "UP_TO_DOWN"
    assert classify_regime_transition("DOWN", "UP") == "DOWN_TO_UP"
    assert classify_regime_transition("UP", "UP") == "NO_CHANGE"
    assert classify_regime_transition("UNKNOWN", "FLAT") == "UNKNOWN_TO_FLAT"
    assert classify_regime_transition("FLAT", "UNKNOWN") == "TO_UNKNOWN"


def test_history_snapshot_config_defaults() -> None:
    config = HistorySnapshotConfig()

    assert config.symbols == DEFAULT_MULTI_SYMBOLS
    assert config.interval == "15m"
    assert config.limit == 300
    assert config.min_candles == 50


def test_runner_requests_limit_times_two_candles() -> None:
    repository = FakeRepository({"BTCUSDT": _make_candles(20)})
    runner = HistorySnapshotRunner(candle_repository=repository, market_reader=FakeReader(["FLAT", "UP"]))

    runner.run(HistorySnapshotConfig(symbols=("BTCUSDT",), limit=10, min_candles=5))

    assert repository.calls == [("BTCUSDT", "15m", 20)]


def test_runner_splits_previous_and_current_windows_without_overlap() -> None:
    reader = FakeReader(["FLAT", "UP"])
    runner = HistorySnapshotRunner(
        candle_repository=FakeRepository({"BTCUSDT": _make_candles(20)}),
        market_reader=reader,
    )

    result = runner.run(HistorySnapshotConfig(symbols=("BTCUSDT",), limit=10, min_candles=5))

    assert result.rows[0].status == "OK"
    assert reader.windows[0].first_open_time == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert reader.windows[0].last_open_time == datetime(2026, 1, 1, 2, 15, tzinfo=timezone.utc)
    assert reader.windows[1].first_open_time == datetime(2026, 1, 1, 2, 30, tzinfo=timezone.utc)
    assert reader.windows[1].last_open_time == datetime(2026, 1, 1, 4, 45, tzinfo=timezone.utc)
    assert reader.windows[1].first_open_time > reader.windows[0].last_open_time


def test_runner_marks_symbol_insufficient_data_when_limit_times_two_is_missing() -> None:
    runner = HistorySnapshotRunner(
        candle_repository=FakeRepository({"BNBUSDT": _make_candles(7)}),
        market_reader=FakeReader(["FLAT", "UP"]),
    )

    result = runner.run(HistorySnapshotConfig(symbols=("BNBUSDT",), limit=5, min_candles=3))

    row = result.rows[0]
    assert row.status == "INSUFFICIENT_DATA"
    assert row.previous_regime == "UNKNOWN"
    assert row.current_regime == "UNKNOWN"
    assert row.transition == "ERROR"
    assert row.warning == "required 10 candles, found 7."
    assert "BNBUSDT: required 10 candles, found 7." in result.warnings


def test_runner_keeps_other_symbols_when_one_symbol_errors() -> None:
    repository = FakeRepository(
        {
            "BTCUSDT": _make_candles(10),
            "ETHUSDT": RuntimeError("repository failed"),
            "SOLUSDT": _make_candles(10),
        }
    )
    runner = HistorySnapshotRunner(
        candle_repository=repository,
        market_reader=FakeReader(["FLAT", "UP", "DOWN", "FLAT"]),
    )

    result = runner.run(HistorySnapshotConfig(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"), limit=5, min_candles=3))

    assert [row.status for row in result.rows] == ["OK", "ERROR", "OK"]
    assert result.rows[0].transition == "FLAT_TO_UP"
    assert result.rows[1].transition == "ERROR"
    assert result.rows[2].transition == "DOWN_TO_FLAT"


def test_table_formatter_contains_expected_columns() -> None:
    report = HistorySnapshotTableFormatter().format_result(
        HistorySnapshotResult(
            config=HistorySnapshotConfig(symbols=("BTCUSDT",), limit=10, min_candles=5),
            rows=(_transition_row("BTCUSDT", "FLAT", "UP", "FLAT_TO_UP"),),
        )
    )

    assert "Symbol" in report
    assert "Previous" in report
    assert "Current" in report
    assert "Transition" in report
    assert "Prev Conf" in report
    assert "Curr Conf" in report
    assert "Safety" in report


def test_summary_counts_transition_types() -> None:
    result = HistorySnapshotResult(
        config=HistorySnapshotConfig(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")),
        rows=(
            _transition_row("BTCUSDT", "FLAT", "UP", "FLAT_TO_UP"),
            _transition_row("ETHUSDT", "DOWN", "FLAT", "DOWN_TO_FLAT"),
            _transition_row("SOLUSDT", "UP", "UP", "NO_CHANGE"),
            RegimeTransitionRow(
                symbol="BNBUSDT",
                status="INSUFFICIENT_DATA",
                previous_regime="UNKNOWN",
                current_regime="UNKNOWN",
                transition="ERROR",
                previous_confidence=0.0,
                current_confidence=0.0,
                current_trend_strength="UNKNOWN",
                trade_signal="NOT_EVALUATED",
                safe_for_runtime_trading=False,
            ),
        ),
    )

    summary = summarize_history_result(result)

    assert summary["FLAT_TO_UP"] == 1
    assert summary["DOWN_TO_FLAT"] == 1
    assert summary["NO_CHANGE"] == 1
    assert summary["ERROR"] == 1
    assert summary["Errors"] == 1


def test_safety_is_always_fail_closed() -> None:
    row = _transition_row("BTCUSDT", "FLAT", "UP", "FLAT_TO_UP")

    assert row.trade_signal == "NOT_EVALUATED"
    assert row.safe_for_runtime_trading is False
    assert "trade_signal: NOT_EVALUATED" in HistorySnapshotTableFormatter().format_safety()
    assert "safe_for_runtime_trading: false" in HistorySnapshotTableFormatter().format_safety()


def test_non_interactive_cli_mode_does_not_call_input(monkeypatch) -> None:
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

        def run(self, config: HistorySnapshotConfig) -> HistorySnapshotResult:
            captured["config"] = config
            return HistorySnapshotResult(
                config=config,
                rows=(_transition_row("BTCUSDT", "FLAT", "UP", "FLAT_TO_UP"),),
            )

    def fail_input(prompt: str = "") -> str:
        raise AssertionError("input() must not be called in non-interactive mode")

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)
    monkeypatch.setattr("builtins.input", fail_input)

    import app.market_reader.history_snapshot as history_snapshot_module

    monkeypatch.setattr(history_snapshot_module, "HistorySnapshotRunner", DummyRunner)

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-history-preview",
            "--symbols",
            "BTCUSDT,ETHUSDT,SOLUSDT",
            "--interval",
            "15m",
            "--limit",
            "300",
            "--min-candles",
            "50",
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "BOOK-L1 History Snapshot" in result.stdout
    config = captured["config"]
    assert isinstance(config, HistorySnapshotConfig)
    assert config.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert config.interval == "15m"
    assert config.limit == 300
    assert config.min_candles == 50


def test_show_details_adds_reason_codes() -> None:
    result = HistorySnapshotResult(
        config=HistorySnapshotConfig(symbols=("BTCUSDT",), limit=10, min_candles=5),
        rows=(_transition_row("BTCUSDT", "FLAT", "UP", "FLAT_TO_UP"),),
    )

    report = HistorySnapshotTableFormatter().format_result(result, show_details=True)

    assert "BTCUSDT details" in report
    assert "Previous window:" in report
    assert "Current window:" in report
    assert "PREVIOUS_REASON" in report
    assert "CURRENT_REASON" in report


def test_enter_selects_default_in_interactive_prompt_helpers() -> None:
    prompts: list[str] = []

    symbols = prompt_history_symbols(
        input_func=_input_from([""]),
        output_func=prompts.append,
    )
    interval = prompt_history_interval(
        input_func=_input_from([""]),
        output_func=prompts.append,
    )

    assert symbols == DEFAULT_MULTI_SYMBOLS
    assert interval == "15m"
    assert any("Enter без ввода = пункт 1" in prompt for prompt in prompts)


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

    def analyze(self, window: Any) -> MarketAnalysisResult:
        self.windows.append(window)
        regime = self.regimes.pop(0)
        bias = {
            "UP": DirectionalBias.BULLISH,
            "DOWN": DirectionalBias.BEARISH,
            "FLAT": DirectionalBias.NEUTRAL,
        }.get(regime, DirectionalBias.UNKNOWN)
        trend = TrendStrength.MODERATE if regime in {"UP", "DOWN"} else TrendStrength.NONE
        return MarketAnalysisResult(
            symbol=window.symbol,
            interval=window.interval,
            market_regime=MarketRegime(regime),
            directional_bias=bias,
            confidence=0.7,
            trend_strength=trend,
            reason_codes=(f"{regime}_REASON",),
            trade_signal=TradeSignal.NOT_EVALUATED,
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


def _transition_row(symbol: str, previous: str, current: str, transition: str) -> RegimeTransitionRow:
    previous_snapshot = RegimeWindowSnapshot(
        symbol=symbol,
        window_name="previous",
        market_regime=previous,
        directional_bias="NEUTRAL",
        confidence=0.82,
        trend_strength="NONE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        candle_count=10,
        first_open_time="2026-06-10T14:15:00+00:00",
        last_open_time="2026-06-12T17:00:00+00:00",
        reason_codes=("PREVIOUS_REASON",),
    )
    current_snapshot = RegimeWindowSnapshot(
        symbol=symbol,
        window_name="current",
        market_regime=current,
        directional_bias="BULLISH" if current == "UP" else "NEUTRAL",
        confidence=0.71,
        trend_strength="MODERATE" if current == "UP" else "NONE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        candle_count=10,
        first_open_time="2026-06-12T17:15:00+00:00",
        last_open_time="2026-06-15T20:00:00+00:00",
        reason_codes=("CURRENT_REASON",),
    )
    return RegimeTransitionRow(
        symbol=symbol,
        status="OK",
        previous_regime=previous,
        current_regime=current,
        transition=transition,
        previous_confidence=0.82,
        current_confidence=0.71,
        current_trend_strength="MODERATE" if current == "UP" else "NONE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
    )


def _input_from(values: list[str]):
    answers = iter(values)

    def input_func(prompt: str = "") -> str:
        return next(answers)

    return input_func
