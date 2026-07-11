from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.timeline_export import (
    DEFAULT_TIMELINE_EXPORT_DIR,
    DEFAULT_TIMELINE_JSON_FILENAME,
    DEFAULT_TIMELINE_MARKDOWN_FILENAME,
    TimelineExportConfig,
    TimelinePreviewExporter,
    timeline_result_to_dict,
    timeline_result_to_markdown,
)
from app.market_reader.timeline_interactive import prompt_timeline_export_choice
from app.market_reader.timeline_preview import (
    TimelinePreviewConfig,
    TimelinePreviewResult,
    TimelineSymbolRow,
    TimelineWindowSnapshot,
    build_window_labels,
    classify_timeline_stability,
)


def test_default_export_paths_are_fixed() -> None:
    config = TimelineExportConfig()

    assert config.output_dir == DEFAULT_TIMELINE_EXPORT_DIR
    assert config.output_dir / DEFAULT_TIMELINE_JSON_FILENAME == DEFAULT_TIMELINE_EXPORT_DIR / "timeline_preview.json"
    assert config.output_dir / DEFAULT_TIMELINE_MARKDOWN_FILENAME == DEFAULT_TIMELINE_EXPORT_DIR / "timeline_preview.md"


def test_export_format_all_writes_json_and_markdown(tmp_path) -> None:
    export_result = TimelinePreviewExporter().export(
        _result(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")),
        TimelineExportConfig(output_dir=tmp_path, export_format="all"),
    )

    assert (tmp_path / "timeline_preview.json").is_file()
    assert (tmp_path / "timeline_preview.md").is_file()
    assert export_result.written_files == (
        tmp_path / "timeline_preview.json",
        tmp_path / "timeline_preview.md",
    )


def test_export_format_json_writes_only_json(tmp_path) -> None:
    TimelinePreviewExporter().export(
        _result(),
        TimelineExportConfig(output_dir=tmp_path, export_format="json"),
    )

    assert (tmp_path / "timeline_preview.json").is_file()
    assert not (tmp_path / "timeline_preview.md").exists()


def test_export_format_md_writes_only_markdown(tmp_path) -> None:
    TimelinePreviewExporter().export(
        _result(),
        TimelineExportConfig(output_dir=tmp_path, export_format="md"),
    )

    assert (tmp_path / "timeline_preview.md").is_file()
    assert not (tmp_path / "timeline_preview.json").exists()


def test_second_export_overwrites_file_instead_of_appending(tmp_path) -> None:
    exporter = TimelinePreviewExporter()
    config = TimelineExportConfig(output_dir=tmp_path, export_format="json")

    exporter.export(_result(symbols=("OLDMARKER",)), config)
    first_text = (tmp_path / "timeline_preview.json").read_text(encoding="utf-8")
    assert "OLDMARKER" in first_text

    exporter.export(_result(symbols=("BTCUSDT",)), config)
    second_text = (tmp_path / "timeline_preview.json").read_text(encoding="utf-8")

    assert "BTCUSDT" in second_text
    assert "OLDMARKER" not in second_text


def test_export_filenames_do_not_contain_runtime_suffixes(tmp_path) -> None:
    TimelinePreviewExporter().export(
        _result(),
        TimelineExportConfig(output_dir=tmp_path, export_format="all"),
    )

    assert {path.name for path in tmp_path.iterdir()} == {
        "timeline_preview.json",
        "timeline_preview.md",
    }


def test_json_export_is_valid_and_contains_contract_fields(tmp_path) -> None:
    TimelinePreviewExporter().export(
        _result(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT")),
        TimelineExportConfig(output_dir=tmp_path, export_format="json"),
    )

    payload = json.loads((tmp_path / "timeline_preview.json").read_text(encoding="utf-8"))

    assert payload["service"] == "BOOK_L1_MARKET_READER"
    assert payload["export_type"] == "timeline_preview"
    assert payload["contract_version"] == "book_l1_timeline_export_v1"
    assert "config" in payload
    assert "summary" in payload
    assert "rows" in payload
    assert "safety" in payload


def test_markdown_export_contains_required_sections() -> None:
    markdown = timeline_result_to_markdown(_result())

    assert "# BOOK-L1 Timeline Preview" in markdown
    assert "## Config" in markdown
    assert "## Timeline" in markdown
    assert "## Summary" in markdown
    assert "## Safety" in markdown


def test_json_safety_is_always_fail_closed() -> None:
    payload = timeline_result_to_dict(_result())

    assert payload["safety"]["trade_signal"] == "NOT_EVALUATED"
    assert payload["safety"]["safe_for_runtime_trading"] is False
    assert payload["safety"]["orders_enabled"] is False
    assert payload["safety"]["live_trading_connected"] is False
    assert payload["rows"][0]["trade_signal"] == "NOT_EVALUATED"
    assert payload["rows"][0]["safe_for_runtime_trading"] is False


def test_markdown_safety_contains_fail_closed_lines() -> None:
    markdown = timeline_result_to_markdown(_result())

    assert "trade_signal = NOT_EVALUATED" in markdown
    assert "safe_for_runtime_trading = false" in markdown
    assert "orders_enabled = false" in markdown
    assert "live_trading_connected = false" in markdown


def test_invalid_export_format_raises_value_error(tmp_path) -> None:
    with pytest.raises(ValueError, match="export_format"):
        TimelineExportConfig(output_dir=tmp_path, export_format="csv")


def test_cli_export_non_interactive_writes_fixed_files(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_cli_runner(monkeypatch)

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
            "--export",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "Exported:" in result.stdout
    assert (tmp_path / "timeline_preview.json").is_file()
    assert (tmp_path / "timeline_preview.md").is_file()


def test_cli_export_format_json_does_not_create_markdown(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_cli_runner(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-timeline-preview",
            "--symbols",
            "BTCUSDT",
            "--non-interactive",
            "--export",
            "--export-format",
            "json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "timeline_preview.json").is_file()
    assert not (tmp_path / "timeline_preview.md").exists()


def test_cli_export_format_md_does_not_create_json(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_cli_runner(monkeypatch)

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-timeline-preview",
            "--symbols",
            "BTCUSDT",
            "--non-interactive",
            "--export",
            "--export-format",
            "md",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "timeline_preview.md").is_file()
    assert not (tmp_path / "timeline_preview.json").exists()


def test_interactive_export_prompt_enter_selects_none() -> None:
    assert prompt_timeline_export_choice(input_func=_input_from([""]), output_func=lambda value: None) == "none"


def test_interactive_export_prompt_option_2_selects_all() -> None:
    assert prompt_timeline_export_choice(input_func=_input_from(["2"]), output_func=lambda value: None) == "all"


def _patch_cli_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySessionContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    class DummyRepository:
        def __init__(self, session: object) -> None:
            self.session = session

    class DummyRunner:
        def __init__(self, *, candle_repository: object, market_reader: object | None = None) -> None:
            self.candle_repository = candle_repository
            self.market_reader = market_reader

        def run(self, config: TimelinePreviewConfig) -> TimelinePreviewResult:
            return _result(symbols=config.symbols, config=config)

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)

    import app.market_reader.timeline_preview as timeline_preview_module

    monkeypatch.setattr(timeline_preview_module, "TimelinePreviewRunner", DummyRunner)


def _result(
    *,
    symbols: tuple[str, ...] = ("BTCUSDT",),
    config: TimelinePreviewConfig | None = None,
) -> TimelinePreviewResult:
    config = config or TimelinePreviewConfig(symbols=symbols, window_size=5, window_count=4, min_candles=3)
    rows = tuple(_row(symbol, config.window_count) for symbol in config.symbols)
    return TimelinePreviewResult(config=config, rows=rows)


def _row(symbol: str, window_count: int) -> TimelineSymbolRow:
    regimes = ("FLAT", "FLAT", "UP", "UP", "FLAT", "UNKNOWN")[:window_count]
    if len(regimes) >= 2:
        transitions = tuple("NO_CHANGE" for _ in range(len(regimes) - 1))
    else:
        transitions = ("ERROR",)
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
            first_open_time="2026-06-01T00:00:00+00:00",
            last_open_time="2026-06-01T01:00:00+00:00",
            reason_codes=("MARKET_READER_ORCHESTRATED",),
        )
        for label, regime in zip(build_window_labels(window_count), regimes)
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
