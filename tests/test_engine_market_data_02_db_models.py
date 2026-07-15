from sqlalchemy import BigInteger, CheckConstraint, DateTime, Numeric
from app.engine_market_data.db.candle_tables import CANDLE_MODELS


def test_six_separate_identical_postgres_models():
    assert {m.__tablename__ for m in CANDLE_MODELS.values()} == {"candles_1m", "candles_5m", "candles_15m", "candles_1h", "candles_4h", "candles_1d"}
    for model in CANDLE_MODELS.values():
        table = model.__table__
        assert isinstance(table.c.open_time_ms.type, BigInteger)
        assert isinstance(table.c.open_time_utc.type, DateTime) and table.c.open_time_utc.type.timezone
        assert isinstance(table.c.open.type, Numeric) and (table.c.open.type.precision, table.c.open.type.scale) == (38, 18)
        checks = " ".join(str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint))
        assert "is_closed = true" in checks and "volume >= 0" in checks
