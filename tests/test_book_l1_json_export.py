from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.history_snapshot import (
    HistorySnapshotConfig,
    HistorySnapshotResult,
    RegimeTransitionRow,
    RegimeWindowSnapshot,
)
from app.market_reader.json_export import (
    CONTRACT_VERSION,
    SERVICE_NAME,
    BookL1JsonExportEnvelope,
    BookL1JsonExportSafety,
    build_current_preview_export_payload,
    build_history_preview_export_payload,
    build_multi_preview_export_payload,
    build_timeline_preview_export_payload,
    resolve_export_path,
    write_book_l1_json_export,
)
from app.market_reader.multi_symbol_preview import (
    MultiSymbolPreviewConfig,
    MultiSymbolPreviewResult,
    SymbolPreviewRow,
)
from app.market_reader.timeline_preview import (
    TimelinePreviewConfig,
    TimelinePreviewResult,
    TimelineSymbolRow,
    TimelineWindowSnapshot,
    build_window_labels,
    classify_timeline_stability,
)


def test_safety_default_is_fail_closed() -> None:
    safety = BookL1JsonExportSafety().to_dict()

    assert safety == {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "orders_enabled": False,
        "live_trading_connected": False,
        "traders_core_connected": False,
        "approved_for_live_trading": False,
        "approved_for_auto_activation": False,
        "model_training_executed": False,
        "binance_download_executed": False,
    }


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("trade_signal", "BUY"),
        ("safe_for_runtime_trading", True),
        ("orders_enabled", True),
        ("live_trading_connected", True),
    ],
)
def test_safety_rejects_unsafe_values(field_name: str, value: object) -> None:
    with pytest.raises(ValueError):
        BookL1JsonExportSafety(**{field_name: value})


def test_envelope_has_service_contract_and_list_messages() -> None:
    envelope = BookL1JsonExportEnvelope(
        report_type="current_preview",
        request={"symbol": "BTCUSDT"},
        result={"ok": True},
        summary={"market_regime": "FLAT"},
        warnings=("warn",),
        errors=("err",),
    )

    payload = envelope.to_dict()
    assert payload["service"] == SERVICE_NAME
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["warnings"] == ["warn"]
    assert payload["errors"] == ["err"]


@pytest.mark.parametrize(
    ("report_type", "filename"),
    [
        ("current_preview", "current_preview.json"),
        ("multi_preview", "multi_preview.json"),
        ("history_preview", "history_preview.json"),
        ("timeline_preview", "timeline_preview.json"),
    ],
)
def test_resolve_export_path_uses_stable_filenames(report_type: str, filename: str, tmp_path) -> None:
    path = resolve_export_path(report_type, output_dir=tmp_path)

    assert path == tmp_path / filename
    assert "BTCUSDT" not in path.name
    assert "15m" not in path.name
    assert "2026" not in path.name
    assert "_" in path.name


def test_resolve_export_path_rejects_unknown_report_type() -> None:
    with pytest.raises(ValueError):
        resolve_export_path("unknown_preview")


def test_write_json_export_creates_overwrites_and_keeps_utf8(tmp_path) -> None:
    first = BookL1JsonExportEnvelope(
        report_type="current_preview",
        request={},
        result={"marker": "OLD", "note": "тест"},
        summary={},
    )
    second = BookL1JsonExportEnvelope(
        report_type="current_preview",
        request={},
        result={"marker": "NEW", "note": "тест"},
        summary={},
    )

    path = write_book_l1_json_export(first, output_dir=tmp_path)
    assert path.is_file()
    assert "OLD" in path.read_text(encoding="utf-8")

    path = write_book_l1_json_export(second, output_dir=tmp_path)
    text = path.read_text(encoding="utf-8")

    assert "NEW" in text
    assert "OLD" not in text
    assert "тест".encode("utf-8") in path.read_bytes()


def test_build_current_preview_export_payload() -> None:
    envelope = build_current_preview_export_payload(
        request={"symbol": "BTCUSDT", "interval": "15m", "limit": 300, "min_candles": 50},
        preview_payload=_current_preview_payload(),
    )

    payload = envelope.to_dict()
    assert payload["report_type"] == "current_preview"
    assert payload["summary"]["market_regime"] == "UP"
    assert payload["summary"]["trade_signal"] == "NOT_EVALUATED"
    assert payload["summary"]["safe_for_runtime_trading"] is False


def test_build_multi_preview_export_payload_and_partial_status() -> None:
    envelope = build_multi_preview_export_payload(
        request={"symbols": ["BTCUSDT", "ETHUSDT"]},
        result=_multi_result(("OK", "ERROR")),
    )

    payload = envelope.to_dict()
    assert payload["report_type"] == "multi_preview"
    assert payload["status"] == "partial"
    assert payload["summary"]["total_symbols"] == 2
    assert payload["summary"]["ok"] == 1
    assert payload["summary"]["errors"] == 1
    assert payload["summary"]["up"] == 1
    assert payload["errors"] == ["ETHUSDT: repository failed"]


def test_build_history_preview_export_payload() -> None:
    envelope = build_history_preview_export_payload(
        request={"symbols": ["BTCUSDT", "ETHUSDT"]},
        result=_history_result(("OK", "INSUFFICIENT_DATA")),
    )

    payload = envelope.to_dict()
    assert payload["report_type"] == "history_preview"
    assert payload["status"] == "partial"
    assert payload["summary"]["insufficient_data"] == 1
    assert payload["summary"]["transition_counts"]["FLAT_TO_UP"] == 1
    assert payload["summary"]["current_regime_counts"]["up"] == 1


def test_build_timeline_preview_export_payload() -> None:
    envelope = build_timeline_preview_export_payload(
        request={"symbols": ["BTCUSDT", "ETHUSDT"]},
        result=_timeline_result(("OK", "INSUFFICIENT_DATA")),
    )

    payload = envelope.to_dict()
    assert payload["report_type"] == "timeline_preview"
    assert payload["status"] == "partial"
    assert payload["summary"]["insufficient_data"] == 1
    assert payload["summary"]["current_regime_counts"]["up"] == 1
    assert payload["summary"]["last_transition_counts"]["ERROR"] == 1
    assert payload["summary"]["stability_counts"]["ERROR"] == 1


def test_cli_book_l1_preview_export_json_writes_current_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_session(monkeypatch)

    import app.market_reader.cli_preview as cli_preview_module

    monkeypatch.setattr(cli_preview_module, "build_market_reader_preview_payload", lambda **kwargs: _current_preview_payload())

    result = CliRunner().invoke(
        cli,
        [
            "book-l1-preview",
            "--symbol",
            "BTCUSDT",
            "--interval",
            "15m",
            "--limit",
            "300",
            "--min-candles",
            "50",
            "--export-json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "JSON export written:" in result.stdout
    assert (tmp_path / "current_preview.json").is_file()
    assert json.loads((tmp_path / "current_preview.json").read_text(encoding="utf-8"))["report_type"] == "current_preview"


def test_cli_book_l1_multi_preview_export_json_writes_multi_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_session(monkeypatch)

    import app.market_reader.multi_symbol_preview as multi_symbol_module

    monkeypatch.setattr(multi_symbol_module, "MultiSymbolPreviewRunner", _multi_runner(("OK", "OK")))

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
            "--export-json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "multi_preview.json").is_file()
    assert json.loads((tmp_path / "multi_preview.json").read_text(encoding="utf-8"))["report_type"] == "multi_preview"


def test_cli_book_l1_history_preview_export_json_writes_history_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_session(monkeypatch)

    import app.market_reader.history_snapshot as history_module

    monkeypatch.setattr(history_module, "HistorySnapshotRunner", _history_runner(("OK", "OK")))

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
            "--export-json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "history_preview.json").is_file()
    assert json.loads((tmp_path / "history_preview.json").read_text(encoding="utf-8"))["report_type"] == "history_preview"


def test_cli_book_l1_timeline_preview_export_json_writes_timeline_file(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_session(monkeypatch)

    import app.market_reader.timeline_preview as timeline_module

    monkeypatch.setattr(timeline_module, "TimelinePreviewRunner", _timeline_runner(("OK", "OK")))

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
            "--export-json",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / "timeline_preview.json").is_file()
    assert not (tmp_path / "timeline_preview.md").exists()
    assert json.loads((tmp_path / "timeline_preview.json").read_text(encoding="utf-8"))["report_type"] == "timeline_preview"


def test_repeated_cli_export_overwrites_same_json_file_without_markdown(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_session(monkeypatch)

    import app.market_reader.timeline_preview as timeline_module

    monkeypatch.setattr(timeline_module, "TimelinePreviewRunner", _timeline_runner(("OK",)))
    args = [
        "book-l1-timeline-preview",
        "--symbols",
        "BTCUSDT",
        "--non-interactive",
        "--export-json",
        "--output-dir",
        str(tmp_path),
    ]

    first = CliRunner().invoke(cli, args)
    json_path = tmp_path / "timeline_preview.json"
    json_path.write_text(json_path.read_text(encoding="utf-8").replace("BTCUSDT", "OLDMARKER"), encoding="utf-8")
    second = CliRunner().invoke(cli, args)

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert {path.name for path in tmp_path.iterdir()} == {"timeline_preview.json"}
    assert "OLDMARKER" not in json_path.read_text(encoding="utf-8")
    assert not (tmp_path / "timeline_preview.md").exists()


def _patch_session(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySessionContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, *args: object) -> None:
            return None

    class DummyRepository:
        def __init__(self, session: object) -> None:
            self.session = session

    monkeypatch.setattr(commands_module, "get_session", lambda: DummySessionContext())
    monkeypatch.setattr(commands_module, "CandleRepository", DummyRepository)


def _current_preview_payload() -> dict[str, object]:
    return {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "requested_limit": 300,
        "candle_count": 300,
        "first_open_time": "2026-06-01T00:00:00+00:00",
        "last_open_time": "2026-06-04T02:45:00+00:00",
        "analysis": {
            "symbol": "BTCUSDT",
            "interval": "15m",
            "market_regime": "UP",
            "directional_bias": "BULLISH",
            "confidence": 0.72,
            "trend_strength": "MODERATE",
            "reason_codes": ["UP_TREND_STRUCTURE"],
            "trade_signal": "NOT_EVALUATED",
            "safe_for_runtime_trading": False,
        },
    }


def _multi_result(statuses: tuple[str, ...]) -> MultiSymbolPreviewResult:
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT")[: len(statuses)]
    return MultiSymbolPreviewResult(
        config=MultiSymbolPreviewConfig(symbols=symbols, limit=300, min_candles=50),
        rows=tuple(_multi_row(symbol, status) for symbol, status in zip(symbols, statuses)),
        warnings=tuple(f"{symbol}: repository failed" for symbol, status in zip(symbols, statuses) if status != "OK"),
    )


def _multi_row(symbol: str, status: str) -> SymbolPreviewRow:
    return SymbolPreviewRow(
        symbol=symbol,
        status=status,
        market_regime="UP" if status == "OK" else "UNKNOWN",
        directional_bias="BULLISH" if status == "OK" else "UNKNOWN",
        confidence=0.72 if status == "OK" else 0.0,
        trend_strength="MODERATE" if status == "OK" else "UNKNOWN",
        volatility_context="NORMAL" if status == "OK" else "N/A",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        candle_count=300 if status == "OK" else 0,
        warning=None if status == "OK" else "repository failed",
    )


def _history_result(statuses: tuple[str, ...]) -> HistorySnapshotResult:
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT")[: len(statuses)]
    return HistorySnapshotResult(
        config=HistorySnapshotConfig(symbols=symbols, limit=300, min_candles=50),
        rows=tuple(_history_row(symbol, status) for symbol, status in zip(symbols, statuses)),
        warnings=tuple(f"{symbol}: required 600 candles, found 10." for symbol, status in zip(symbols, statuses) if status != "OK"),
    )


def _history_row(symbol: str, status: str) -> RegimeTransitionRow:
    if status != "OK":
        return RegimeTransitionRow(
            symbol=symbol,
            status=status,
            previous_regime="UNKNOWN",
            current_regime="UNKNOWN",
            transition="ERROR",
            previous_confidence=0.0,
            current_confidence=0.0,
            current_trend_strength="UNKNOWN",
            trade_signal="NOT_EVALUATED",
            safe_for_runtime_trading=False,
            warning="required 600 candles, found 10.",
        )

    return RegimeTransitionRow(
        symbol=symbol,
        status="OK",
        previous_regime="FLAT",
        current_regime="UP",
        transition="FLAT_TO_UP",
        previous_confidence=0.55,
        current_confidence=0.72,
        current_trend_strength="MODERATE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        previous_snapshot=_history_snapshot(symbol, "previous", "FLAT"),
        current_snapshot=_history_snapshot(symbol, "current", "UP"),
    )


def _history_snapshot(symbol: str, window_name: str, regime: str) -> RegimeWindowSnapshot:
    return RegimeWindowSnapshot(
        symbol=symbol,
        window_name=window_name,
        market_regime=regime,
        directional_bias="BULLISH" if regime == "UP" else "NEUTRAL",
        confidence=0.72,
        trend_strength="MODERATE" if regime == "UP" else "NONE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        candle_count=300,
        first_open_time="2026-06-01T00:00:00+00:00",
        last_open_time="2026-06-04T02:45:00+00:00",
        reason_codes=(f"{regime}_REASON",),
    )


def _timeline_result(statuses: tuple[str, ...]) -> TimelinePreviewResult:
    symbols = ("BTCUSDT", "ETHUSDT", "SOLUSDT")[: len(statuses)]
    config = TimelinePreviewConfig(symbols=symbols, window_size=300, window_count=4, min_candles=50)
    return TimelinePreviewResult(
        config=config,
        rows=tuple(_timeline_row(symbol, status, config.window_count) for symbol, status in zip(symbols, statuses)),
        warnings=tuple(f"{symbol}: required 1200 candles, found 10." for symbol, status in zip(symbols, statuses) if status != "OK"),
    )


def _timeline_row(symbol: str, status: str, window_count: int) -> TimelineSymbolRow:
    if status != "OK":
        windows = tuple(_timeline_snapshot(symbol, label, "UNKNOWN") for label in build_window_labels(window_count))
        return TimelineSymbolRow(
            symbol=symbol,
            status=status,
            windows=windows,
            regimes=tuple("UNKNOWN" for _ in windows),
            transitions=tuple("ERROR" for _ in range(window_count - 1)),
            last_transition="ERROR",
            stability="ERROR",
            current_confidence=0.0,
            current_trend_strength="UNKNOWN",
            trade_signal="NOT_EVALUATED",
            safe_for_runtime_trading=False,
            warning="required 1200 candles, found 10.",
        )

    regimes = ("FLAT", "FLAT", "UP", "UP")[:window_count]
    transitions = tuple("NO_CHANGE" for _ in range(window_count - 1))
    windows = tuple(_timeline_snapshot(symbol, label, regime) for label, regime in zip(build_window_labels(window_count), regimes))
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


def _timeline_snapshot(symbol: str, label: str, regime: str) -> TimelineWindowSnapshot:
    return TimelineWindowSnapshot(
        symbol=symbol,
        window_label=label,
        market_regime=regime,
        directional_bias="BULLISH" if regime == "UP" else "NEUTRAL",
        confidence=0.72 if regime != "UNKNOWN" else 0.0,
        trend_strength="MODERATE" if regime == "UP" else "NONE",
        trade_signal="NOT_EVALUATED",
        safe_for_runtime_trading=False,
        candle_count=300,
        first_open_time="2026-06-01T00:00:00+00:00",
        last_open_time="2026-06-04T02:45:00+00:00",
        reason_codes=(f"{regime}_REASON",),
    )


def _multi_runner(statuses: tuple[str, ...]) -> type:
    class DummyRunner:
        def __init__(self, *, candle_repository: object, reader: object | None = None) -> None:
            self.candle_repository = candle_repository
            self.reader = reader

        def run(self, config: MultiSymbolPreviewConfig) -> MultiSymbolPreviewResult:
            selected_statuses = statuses[: len(config.symbols)] or ("OK",)
            if len(selected_statuses) < len(config.symbols):
                selected_statuses = selected_statuses + tuple("OK" for _ in range(len(config.symbols) - len(selected_statuses)))
            return _multi_result(selected_statuses)

    return DummyRunner


def _history_runner(statuses: tuple[str, ...]) -> type:
    class DummyRunner:
        def __init__(self, *, candle_repository: object, market_reader: object | None = None) -> None:
            self.candle_repository = candle_repository
            self.market_reader = market_reader

        def run(self, config: HistorySnapshotConfig) -> HistorySnapshotResult:
            selected_statuses = statuses[: len(config.symbols)] or ("OK",)
            if len(selected_statuses) < len(config.symbols):
                selected_statuses = selected_statuses + tuple("OK" for _ in range(len(config.symbols) - len(selected_statuses)))
            return _history_result(selected_statuses)

    return DummyRunner


def _timeline_runner(statuses: tuple[str, ...]) -> type:
    class DummyRunner:
        def __init__(self, *, candle_repository: object, market_reader: object | None = None) -> None:
            self.candle_repository = candle_repository
            self.market_reader = market_reader

        def run(self, config: TimelinePreviewConfig) -> TimelinePreviewResult:
            selected_statuses = statuses[: len(config.symbols)] or ("OK",)
            if len(selected_statuses) < len(config.symbols):
                selected_statuses = selected_statuses + tuple("OK" for _ in range(len(config.symbols) - len(selected_statuses)))
            return _timeline_result(selected_statuses)

    return DummyRunner
