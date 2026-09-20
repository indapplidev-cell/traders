from types import SimpleNamespace
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.paper_models import TradingUniverseSymbolPreflightRecord
from app.engine_market_data.candle import Candle
from app.trading_universe.symbol_preflight import (
    load_symbol_preflight, persist_symbol_preflight, run_symbol_preflight,
)


NOW = 1_800_000_000_000


def candles(symbol, timeframe, *, gap=False):
    duration = 60_000 if timeframe == "1m" else 300_000
    latest = (NOW // duration) * duration - duration
    opens = [latest - duration * 2, latest - duration, latest]
    if gap:
        opens[1] -= duration
    return [Candle(
        symbol, timeframe, value, value + duration - 1,
        1, 1, 1, 1, 1, is_closed=True, source="fixture",
    ) for value in opens]


class PublicFixture:
    def __init__(self, *, gap_symbol=None):
        self.gap_symbol = gap_symbol

    def fetch_server_time_ms(self):
        return NOW

    def fetch_exchange_info(self, symbols):
        return {"symbols": [{
            "symbol": symbol, "status": "TRADING", "quoteAsset": "USDT",
            "isSpotTradingAllowed": True, "baseAssetPrecision": 8,
            "quoteAssetPrecision": 8,
            "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
                {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "100", "stepSize": "0.001"},
                {"filterType": "MARKET_LOT_SIZE", "minQty": "0", "maxQty": "100", "stepSize": "0"},
                {"filterType": "NOTIONAL", "minNotional": "5", "maxNotional": "100000"},
            ],
        } for symbol in symbols]}

    def fetch_book_ticker(self, symbol):
        return SimpleNamespace(symbol=symbol, bid_price=1, ask_price=2)

    def fetch_klines(self, symbol, timeframe, limit):
        return candles(symbol, timeframe, gap=symbol == self.gap_symbol and timeframe == "1m")


class CommissionFixture:
    def __init__(self, ready):
        self.ready = ready

    def ensure_fresh(self, *, force):
        return SimpleNamespace(
            status="READY" if self.ready else "FEE_SOURCE_NOT_READY",
            real_account_data=self.ready, ready_symbols=2 if self.ready else 0,
            snapshot_id="commission-fixture" if self.ready else None,
        )


def test_preflight_passes_authoritative_inputs_and_persists_snapshot(tmp_path):
    path = tmp_path / "preflight.json"
    report = run_symbol_preflight(
        ("BTCUSDT", "ZECUSDT"), public_client=PublicFixture(),
        commission_manager=CommissionFixture(True), output_path=path,
    )
    assert report.active_symbols == ("BTCUSDT", "ZECUSDT")
    assert report.disabled_symbols == ()
    persisted = load_symbol_preflight(path)
    assert persisted["active_symbols"] == ["BTCUSDT", "ZECUSDT"]
    assert {row["commission_authority"] for row in persisted["symbols"]} == {
        "BINANCE_ACCOUNT_COMMISSION_SNAPSHOT"
    }


def test_preflight_fails_only_the_affected_symbol_without_substitution(tmp_path):
    report = run_symbol_preflight(
        ("BTCUSDT", "ZECUSDT"), public_client=PublicFixture(gap_symbol="ZECUSDT"),
        commission_manager=CommissionFixture(True), output_path=tmp_path / "preflight.json",
    )
    assert report.active_symbols == ("BTCUSDT",)
    assert report.disabled_symbols == ("ZECUSDT",)
    disabled = next(item for item in report.symbols if item.symbol == "ZECUSDT")
    assert disabled.status == "SYMBOL_FAIL_CLOSED"
    assert disabled.reason == "SYMBOL_1M_DATA_UNAVAILABLE"


def test_preflight_fails_all_symbols_when_account_commission_is_unavailable(tmp_path):
    report = run_symbol_preflight(
        ("BTCUSDT", "ZECUSDT"), public_client=PublicFixture(),
        commission_manager=CommissionFixture(False), output_path=tmp_path / "preflight.json",
    )
    assert report.active_symbols == ()
    assert {item.reason for item in report.symbols} == {"SYMBOL_COMMISSION_UNAVAILABLE"}


def test_preflight_persistence_is_one_bounded_normalized_snapshot(tmp_path):
    report = run_symbol_preflight(
        ("BTCUSDT", "ZECUSDT"), public_client=PublicFixture(),
        commission_manager=CommissionFixture(True), output_path=tmp_path / "preflight.json",
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    persist_symbol_preflight(sessions, report)
    with sessions() as session:
        rows = tuple(session.scalars(select(TradingUniverseSymbolPreflightRecord)))
    assert [(row.symbol, row.status, row.active) for row in rows] == [
        ("BTCUSDT", "PASS", True), ("ZECUSDT", "PASS", True),
    ]
    engine.dispose()
