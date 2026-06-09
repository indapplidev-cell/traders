from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.repositories.candle_repository import CandleRepository
import app.db.models  # noqa: F401


def test_candle_repository_upsert_and_range_queries() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = CandleRepository(session)
        first_open = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
        second_open = datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc)
        first_close = datetime(2025, 1, 1, 0, 14, 59, tzinfo=timezone.utc)
        second_close = datetime(2025, 1, 1, 0, 29, 59, tzinfo=timezone.utc)
        candles = [
            _build_candle(first_open, first_close, Decimal("100.00")),
            _build_candle(second_open, second_close, Decimal("101.00")),
        ]

        assert repository.upsert_many(candles) == 2

        updated_first = _build_candle(first_open, first_close, Decimal("102.00"))
        assert repository.upsert_many([updated_first]) == 1

        stored = repository.get_range(
            symbol="BTCUSDT",
            interval="15m",
            start_at=first_open,
            end_at=datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc),
        )

        assert repository.count_range("BTCUSDT", "15m", first_open, datetime(2025, 1, 1, 0, 30, tzinfo=timezone.utc)) == 2
        assert len(stored) == 2
        assert str(stored[0].close) == "102.00000000"
        assert repository.get_last_open_time("BTCUSDT", "15m").isoformat().startswith("2025-01-01T00:15:00")


def _build_candle(open_time: datetime, close_time: datetime, close_price: Decimal) -> dict:
    return {
        "symbol": "BTCUSDT",
        "interval": "15m",
        "open_time": open_time,
        "close_time": close_time,
        "open": Decimal("99.00"),
        "high": Decimal("103.00"),
        "low": Decimal("98.00"),
        "close": close_price,
        "volume": Decimal("10.00"),
        "quote_asset_volume": Decimal("1000.00"),
        "number_of_trades": 20,
        "taker_buy_base_volume": Decimal("5.00"),
        "taker_buy_quote_volume": Decimal("500.00"),
        "source": "binance",
    }
