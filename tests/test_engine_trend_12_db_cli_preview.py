from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.market_reader.engine_trend import db_cli_preview as cli


def parsed(*arguments: str):
    parser = cli.build_parser()
    args = parser.parse_args(list(arguments))
    cli.validate_args(args, parser)
    return args


def test_cli_validates_confirmed_symbol() -> None:
    assert parsed("--symbol", "BTCUSDT").symbol == "BTCUSDT"


def test_cli_rejects_unconfirmed_symbol() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["--symbol", "XRPUSDT"])
    assert exc.value.code == 2


def test_cli_accepts_only_15m_interval() -> None:
    assert parsed("--symbol", "ETHUSDT", "--interval", "15m").interval == "15m"
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--symbol", "ETHUSDT", "--interval", "1h"])


def test_cli_rejects_max_candles_above_hard_cap() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["--symbol", "SOLUSDT", "--max-candles", "501"])
    with pytest.raises(SystemExit) as exc:
        cli.validate_args(args, parser)
    assert exc.value.code == 2


def test_db_env_resolution_respects_explicit_name() -> None:
    environment = {
        "TRADERS_ML_DATABASE_URL": "first",
        "CUSTOM_DB_URL": "explicit",
    }
    assert cli.resolve_db_url(environment, "CUSTOM_DB_URL") == (
        "CUSTOM_DB_URL",
        "explicit",
    )
    with pytest.raises(cli.CliError) as exc:
        cli.resolve_db_url(environment, "MISSING_DB_URL")
    assert exc.value.code == "DB_CONFIG_MISSING"


def test_db_env_resolution_uses_default_search_order() -> None:
    environment = {"DATABASE_URL": "third", "POSTGRES_URL": "fourth"}
    assert cli.resolve_db_url(environment) == ("DATABASE_URL", "third")


def test_db_url_masking_hides_credentials_and_database() -> None:
    masked = cli.mask_db_url(
        "postgresql+psycopg://real_user:super-secret@localhost:5433/real_db"
    )
    assert "super-secret" not in masked
    assert "real_user" not in masked
    assert "real_db" not in masked
    assert masked == (
        "postgresql+psycopg://<user>:<password>@localhost:5433/<db>"
    )


class OneRowResult:
    def __init__(self, row: dict[str, object]) -> None:
        self.row = row

    def mappings(self) -> OneRowResult:
        return self

    def one(self) -> dict[str, object]:
        return self.row


class PeriodConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def execute(self, statement, parameters):
        self.calls.append((statement, parameters))
        return OneRowResult(
            {"max_open_time": datetime(2026, 6, 15, 20, 0, tzinfo=timezone.utc)}
        )


def test_period_resolution_uses_max_open_time_and_inclusive_end() -> None:
    connection = PeriodConnection()
    start, end = cli.resolve_period_bounds(connection, "BTCUSDT", "15m", 96)
    assert start == "2026-06-14T20:15:00+00:00"
    assert end == "2026-06-15T20:00:00+00:00"
    sql = str(connection.calls[0][0])
    assert "MAX(open_time)" in sql
    assert connection.calls[0][1] == {"symbol": "BTCUSDT", "interval": "15m"}


def test_availability_query_is_read_only_and_confirmed_only() -> None:
    normalized = " ".join(cli.AVAILABILITY_SQL.split())
    assert normalized.startswith("SELECT symbol, interval, COUNT(*)")
    assert "public.market_candles" in normalized
    assert "('BTCUSDT', 'ETHUSDT', 'SOLUSDT')" in normalized
    assert "interval = '15m'" in normalized
    for forbidden in ("insert ", "update ", "delete ", "drop ", "alter ", "truncate "):
        assert forbidden not in normalized.lower()


def test_output_path_creation_works_without_database(tmp_path) -> None:
    path = cli.save_json({"payload": {"market_regime": "UNKNOWN"}}, tmp_path / "a" / "result.json")
    assert json.loads(path.read_text(encoding="utf-8"))["payload"]["market_regime"] == "UNKNOWN"


def test_module_import_does_not_attempt_database_connection(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("database connection attempted during import")

    monkeypatch.setattr(cli, "create_engine", fail)
    importlib.reload(cli)


def test_safety_fields_are_validated_and_printed(capsys) -> None:
    safety = {
        "trade_signal": "NOT_EVALUATED",
        "safe_for_runtime_trading": False,
        "live_trading_connected": False,
    }
    result = SimpleNamespace(
        engine_output=SimpleNamespace(
            preview={
                "symbol": "BTCUSDT",
                "interval": "15m",
                "period_start": "start",
                "period_end": "end",
                "market_regime": "UNKNOWN",
                "confidence": 0.0,
                "reason_codes_top": ["INSUFFICIENT_EVIDENCE"],
                "safety": safety,
            }
        ),
        batch=SimpleNamespace(metadata={"candle_count": 96}),
        warnings=(),
        errors=(),
        status=SimpleNamespace(value="READY"),
    )
    preview = cli.build_cli_preview(result, "DATABASE_URL", "invalid", None, None)
    cli.print_human_preview(preview)
    stdout = capsys.readouterr().out
    assert "safety.trade_signal: NOT_EVALUATED" in stdout
    assert "safety.safe_for_runtime_trading: false" in stdout
    assert "safety.live_trading_connected: false" in stdout
