from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from app.cli.commands import cli
from app.data_audit.candle_availability import (
    CONTRACT_VERSION,
    ERROR,
    INSUFFICIENT_DATA,
    MISSING,
    PASS,
    PASS_WITH_DATA_GAPS,
    READY,
    CandleAvailabilityAuditConfig,
    CandleAvailabilityAuditFormatter,
    CandleAvailabilityAuditor,
    CandleAvailabilityRow,
    build_json_payload,
    build_markdown,
    parse_audit_intervals,
    parse_audit_symbols,
    resolve_result_status,
    resolve_row_status,
    summarize_rows,
    write_candle_availability_json,
    write_candle_availability_markdown,
)


def test_default_config_symbols_are_btc_eth_sol() -> None:
    assert CandleAvailabilityAuditConfig().symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def test_default_intervals_are_15m_1h_4h() -> None:
    assert CandleAvailabilityAuditConfig().intervals == ("15m", "1h", "4h")


def test_required_candles_defaults_to_window_size_times_window_count() -> None:
    assert CandleAvailabilityAuditConfig().effective_required_candles == 1200


def test_explicit_required_candles_overrides_window_formula() -> None:
    config = CandleAvailabilityAuditConfig(window_size=300, window_count=4, required_candles=777)

    assert config.effective_required_candles == 777


def test_status_ready_when_available_at_least_required() -> None:
    assert resolve_row_status(1200, 1200) == READY
    assert resolve_row_status(1201, 1200) == READY


def test_status_insufficient_when_available_below_required() -> None:
    assert resolve_row_status(1199, 1200) == INSUFFICIENT_DATA


def test_status_missing_when_available_zero() -> None:
    assert resolve_row_status(0, 1200) == MISSING


def test_status_error_when_repository_raises(tmp_path: Path) -> None:
    config = _config(tmp_path, symbols=("BTCUSDT",), intervals=("15m",))

    result = CandleAvailabilityAuditor(_RaisingRepository()).run(config)

    assert result.status == "FAIL"
    assert result.rows[0].status == ERROR
    assert "read error" in (result.rows[0].message or "")


def test_default_result_pass_when_all_ready() -> None:
    rows = (_row("BTCUSDT", "15m", READY),)

    assert resolve_result_status(rows, strict=False) == PASS


def test_default_result_pass_with_data_gaps_when_some_missing() -> None:
    rows = (_row("BTCUSDT", "15m", READY), _row("BTCUSDT", "1h", MISSING))

    assert resolve_result_status(rows, strict=False) == PASS_WITH_DATA_GAPS


def test_strict_result_fail_when_some_missing() -> None:
    rows = (_row("BTCUSDT", "15m", READY), _row("BTCUSDT", "1h", MISSING))

    assert resolve_result_status(rows, strict=True) == "FAIL"


def test_summary_counts_statuses_correctly() -> None:
    summary = summarize_rows(
        (
            _row("BTCUSDT", "15m", READY),
            _row("BTCUSDT", "1h", MISSING),
            _row("ETHUSDT", "1h", INSUFFICIENT_DATA),
            _row("SOLUSDT", "4h", ERROR),
        )
    )

    assert summary == {READY: 1, INSUFFICIENT_DATA: 1, MISSING: 1, ERROR: 1}


def test_json_writer_creates_stable_output_path(tmp_path: Path) -> None:
    config = _config(tmp_path)

    path = write_candle_availability_json(config, (_row("BTCUSDT", "15m", READY),), _summary(ready=1), PASS)

    assert path == tmp_path / "candle_availability_audit.json"
    assert path.is_file()


def test_json_contains_contract_version() -> None:
    payload = build_json_payload(
        CandleAvailabilityAuditConfig(),
        (_row("BTCUSDT", "15m", READY),),
        _summary(ready=1),
        PASS,
    )

    assert payload["contract_version"] == CONTRACT_VERSION


def test_json_contains_safety_read_only_true() -> None:
    payload = build_json_payload(
        CandleAvailabilityAuditConfig(),
        (_row("BTCUSDT", "15m", READY),),
        _summary(ready=1),
        PASS,
    )

    assert payload["safety"]["read_only"] is True


def test_markdown_writer_creates_stable_output_path(tmp_path: Path) -> None:
    config = _config(tmp_path)

    path = write_candle_availability_markdown(config, (_row("BTCUSDT", "15m", READY),), _summary(ready=1), PASS)

    assert path == tmp_path / "candle_availability_audit.md"
    assert path.is_file()


def test_markdown_contains_availability_table() -> None:
    markdown = build_markdown(
        CandleAvailabilityAuditConfig(),
        (_row("BTCUSDT", "15m", READY),),
        _summary(ready=1),
        PASS,
    )

    assert "## Availability" in markdown
    assert "| Symbol | Interval | Available | Required | Status |" in markdown


def test_formatter_prints_result() -> None:
    config = CandleAvailabilityAuditConfig(symbols=("BTCUSDT",), intervals=("15m",))
    result = CandleAvailabilityAuditor(_FakeRepository({("BTCUSDT", "15m"): 1200})).run(config)

    output = CandleAvailabilityAuditFormatter().format(result, config=config)

    assert "Result: PASS" in output


def test_formatter_prints_ready_and_missing_counts(tmp_path: Path) -> None:
    config = _config(tmp_path, symbols=("BTCUSDT",), intervals=("15m", "1h"))
    result = CandleAvailabilityAuditor(_FakeRepository({("BTCUSDT", "15m"): 1200})).run(config)

    output = CandleAvailabilityAuditFormatter().format(result, config=config)

    assert "READY: 1" in output
    assert "MISSING: 1" in output


def test_cli_parser_supports_symbols() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--symbols" in result.stdout


def test_cli_parser_supports_symbol() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--symbol" in result.stdout


def test_cli_parser_supports_intervals() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--intervals" in result.stdout


def test_cli_parser_supports_required_candles() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--required-candles" in result.stdout


def test_cli_parser_supports_strict() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--strict" in result.stdout


def test_cli_parser_supports_show_details() -> None:
    result = CliRunner().invoke(cli, ["book-data-candle-availability-audit", "--help"])

    assert result.exit_code == 0
    assert "--show-details" in result.stdout


def test_parse_symbols_supports_symbols_csv() -> None:
    assert parse_audit_symbols("btcusdt, ethusdt") == ("BTCUSDT", "ETHUSDT")


def test_parse_symbols_supports_symbol_options() -> None:
    assert parse_audit_symbols(None, ("btcusdt", "solusdt")) == ("BTCUSDT", "SOLUSDT")


def test_parse_intervals_supports_csv() -> None:
    assert parse_audit_intervals("15m,1h") == ("15m", "1h")


def test_auditor_writes_json_with_real_rows(tmp_path: Path) -> None:
    config = _config(tmp_path, symbols=("BTCUSDT",), intervals=("15m",), required_candles=100)

    result = CandleAvailabilityAuditor(_FakeRepository({("BTCUSDT", "15m"): 123})).run(config)
    payload = json.loads((tmp_path / "candle_availability_audit.json").read_text(encoding="utf-8"))

    assert result.status == PASS
    assert payload["rows"][0]["available_candles"] == 123


class _FakeRepository:
    def __init__(self, counts: dict[tuple[str, str], int]) -> None:
        self._counts = counts
        self._first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self._last = datetime(2026, 1, 2, tzinfo=timezone.utc)

    def count_by_symbol_interval(self, symbol: str, interval: str) -> int:
        return self._counts.get((symbol, interval), 0)

    def get_open_time_bounds(self, symbol: str, interval: str) -> tuple[object | None, object | None]:
        if self.count_by_symbol_interval(symbol, interval) == 0:
            return None, None
        return self._first, self._last


class _RaisingRepository:
    def count_by_symbol_interval(self, symbol: str, interval: str) -> int:
        raise RuntimeError("database unavailable")

    def get_open_time_bounds(self, symbol: str, interval: str) -> tuple[object | None, object | None]:
        raise RuntimeError("database unavailable")


def _config(
    tmp_path: Path,
    *,
    symbols: tuple[str, ...] = ("BTCUSDT",),
    intervals: tuple[str, ...] = ("15m",),
    required_candles: int | None = 1200,
) -> CandleAvailabilityAuditConfig:
    return CandleAvailabilityAuditConfig(
        symbols=symbols,
        intervals=intervals,
        required_candles=required_candles,
        output_json=tmp_path / "candle_availability_audit.json",
        output_md=tmp_path / "candle_availability_audit.md",
    )


def _row(symbol: str, interval: str, status: str) -> CandleAvailabilityRow:
    available = 1200 if status == READY else 0
    if status == INSUFFICIENT_DATA:
        available = 100
    return CandleAvailabilityRow(
        symbol=symbol,
        interval=interval,
        available_candles=available,
        required_candles=1200,
        status=status,
    )


def _summary(*, ready: int = 0, insufficient: int = 0, missing: int = 0, error: int = 0) -> dict[str, int]:
    return {
        READY: ready,
        INSUFFICIENT_DATA: insufficient,
        MISSING: missing,
        ERROR: error,
    }
