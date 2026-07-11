from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.multi_symbol_interactive import prompt_interval, prompt_symbol_set
from app.market_reader.multi_symbol_preview import (
    DEFAULT_MULTI_SYMBOLS,
    MultiSymbolPreviewConfig,
    MultiSymbolPreviewResult,
    MultiSymbolPreviewRunner,
    MultiSymbolTableFormatter,
    SymbolPreviewRow,
    calculate_summary,
    normalize_symbol,
    parse_symbols,
)
from app.market_reader.schemas import DirectionalBias, MarketAnalysisResult, MarketRegime, TradeSignal, TrendStrength


def test_normalize_symbol_aliases() -> None:
    assert normalize_symbol("btc") == "BTCUSDT"
    assert normalize_symbol("eth") == "ETHUSDT"
    assert normalize_symbol("sol") == "SOLUSDT"
    assert normalize_symbol("btcusdt") == "BTCUSDT"


def test_parse_symbols_normalizes_comma_separated_input() -> None:
    assert parse_symbols("btc, eth, sol") == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_config_values() -> None:
    config = MultiSymbolPreviewConfig()

    assert config.symbols == DEFAULT_MULTI_SYMBOLS
    assert config.interval == "15m"
    assert config.limit == 300
    assert config.min_candles == 50


def test_table_formatter_contains_expected_columns() -> None:
    result = MultiSymbolPreviewResult(
        config=MultiSymbolPreviewConfig(symbols=("BTCUSDT",)),
        rows=(
            SymbolPreviewRow(
                symbol="BTCUSDT",
                status="OK",
                market_regime="FLAT",
                directional_bias="NEUTRAL",
                confidence=0.94,
                trend_strength="NONE",
                volatility_context="NORMAL",
                trade_signal="NOT_EVALUATED",
                safe_for_runtime_trading=False,
            ),
        ),
    )

    report = MultiSymbolTableFormatter().format_result(result)

    assert "Symbol" in report
    assert "Regime" in report
    assert "Bias" in report
    assert "Confidence" in report
    assert "Trade signal" in report
    assert "Runtime trading" in report


def test_result_summary_counts_regimes_and_errors() -> None:
    rows = (
        _row("BTCUSDT", "OK", "UP"),
        _row("ETHUSDT", "OK", "DOWN"),
        _row("SOLUSDT", "OK", "FLAT"),
        _row("BNBUSDT", "ERROR", "UNKNOWN"),
    )

    assert calculate_summary(rows) == {
        "UP": 1,
        "DOWN": 1,
        "FLAT": 1,
        "UNKNOWN": 1,
        "Errors": 1,
    }


def test_runner_keeps_other_symbols_when_one_symbol_errors() -> None:
    repository = FakeRepository(
        {
            "BTCUSDT": _make_candles(60),
            "BNBUSDT": [],
        }
    )
    runner = MultiSymbolPreviewRunner(
        candle_repository=repository,
        reader=FakeReader(),
    )

    result = runner.run(MultiSymbolPreviewConfig(symbols=("BTCUSDT", "BNBUSDT"), limit=60))

    assert [row.status for row in result.rows] == ["OK", "ERROR"]
    assert result.rows[0].market_regime == "FLAT"
    assert result.rows[1].market_regime == "UNKNOWN"
    assert result.rows[1].warning == "not enough candles or no local candles found."
    assert "BNBUSDT: not enough candles or no local candles found." in result.warnings


def test_safety_is_always_fail_closed_in_rows() -> None:
    row = _row("BTCUSDT", "OK", "FLAT")

    assert row.trade_signal == "NOT_EVALUATED"
    assert row.safe_for_runtime_trading is False


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
        def __init__(self, *, candle_repository: object, reader: object | None = None) -> None:
            captured["repository"] = candle_repository
            captured["reader"] = reader

        def run(self, config: MultiSymbolPreviewConfig) -> MultiSymbolPreviewResult:
            captured["config"] = config
            return MultiSymbolPreviewResult(
                config=config,
                rows=(
                    SymbolPreviewRow(
                        symbol="BTCUSDT",
                        status="OK",
                        market_regime="FLAT",
                        directional_bias="NEUTRAL",
                        confidence=0.94,
                        trend_strength="NONE",
                        volatility_context="NORMAL",
                        trade_signal="NOT_EVALUATED",
                        safe_for_runtime_trading=False,
                    ),
                ),
            )

    def fail_input(prompt: str = "") -> str:
        raise AssertionError("input() must not be called in non-interactive mode")

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)
    monkeypatch.setattr("builtins.input", fail_input)

    import app.market_reader.multi_symbol_preview as multi_symbol_preview_module

    monkeypatch.setattr(multi_symbol_preview_module, "MultiSymbolPreviewRunner", DummyRunner)

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-multi-preview",
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
    assert "BOOK-L1 Multi-Symbol Market Reader - Result" in result.stdout
    config = captured["config"]
    assert isinstance(config, MultiSymbolPreviewConfig)
    assert config.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    assert config.interval == "15m"
    assert config.limit == 300
    assert config.min_candles == 50


def test_enter_selects_default_in_prompt_helper() -> None:
    prompts: list[str] = []

    symbols = prompt_symbol_set(
        input_func=_input_from([""]),
        output_func=prompts.append,
    )

    assert symbols == DEFAULT_MULTI_SYMBOLS
    assert "Enter без ввода = пункт 1" in prompts[0]


def test_invalid_prompt_input_repeats_question() -> None:
    prompts: list[str] = []

    interval = prompt_interval(
        input_func=_input_from(["bad", ""]),
        output_func=prompts.append,
    )

    assert interval == "15m"
    assert any("Неверный ввод" in prompt for prompt in prompts)
    assert len([prompt for prompt in prompts if "Выбери интервал свечей" in prompt]) == 2


class FakeRepository:
    def __init__(self, candles_by_symbol: dict[str, list[Any]]) -> None:
        self.candles_by_symbol = candles_by_symbol

    def get_last_n(self, *, symbol: str, interval: str, limit: int) -> list[Any]:
        return self.candles_by_symbol.get(symbol, [])[-limit:]


class FakeReader:
    def analyze(self, window: Any) -> MarketAnalysisResult:
        return MarketAnalysisResult(
            symbol=window.symbol,
            interval=window.interval,
            market_regime=MarketRegime.FLAT,
            directional_bias=DirectionalBias.NEUTRAL,
            confidence=0.94,
            trend_strength=TrendStrength.NONE,
            reason_codes=(
                "MARKET_READER_ORCHESTRATED",
                "MARKET_REGIME_COMPOSED",
                "ATR_NORMAL_VOLATILITY",
            ),
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


def _row(symbol: str, status: str, regime: str) -> SymbolPreviewRow:
    return SymbolPreviewRow(
        symbol=symbol,
        status=status,
        market_regime=regime,
        directional_bias="NEUTRAL" if status == "OK" else "UNKNOWN",
        confidence=0.5 if status == "OK" else 0.0,
        trend_strength="NONE" if status == "OK" else "UNKNOWN",
        volatility_context="NORMAL" if status == "OK" else "N/A",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
    )


def _input_from(values: list[str]):
    answers = iter(values)

    def input_func(prompt: str = "") -> str:
        return next(answers)

    return input_func
