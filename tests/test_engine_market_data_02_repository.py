import os
import pytest
from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from app.engine_market_data.db.candle_repository import CandleRepository, candle_checksum
from app.engine_market_data.db.candle_tables import Candle1m
from app.engine_market_data.db.session import create_market_data_session_factory
from sqlalchemy.dialects.postgresql import insert
from engine_market_data_02_helpers import candle


def test_repository_uses_postgres_conflict_and_rejects_open_candle():
    stmt = insert(Candle1m).values(CandleRepository._values(candle("1m", 0))).on_conflict_do_nothing(index_elements=[Candle1m.symbol, Candle1m.open_time_ms])
    assert "ON CONFLICT" in str(stmt.compile(dialect=postgresql.dialect()))
    with pytest.raises(ValueError): CandleRepository._values(candle("1m", 0, closed=False))
    assert len(candle_checksum(candle("1m", 0))) == 64


@pytest.mark.postgres
def test_postgres_idempotent_upsert_and_checksum_update():
    url = os.getenv("TEST_POSTGRES_DATABASE_URL")
    if not url: pytest.skip("TEST_POSTGRES_DATABASE_URL is not configured")
    factory = create_market_data_session_factory(url)
    repository = CandleRepository(factory)
    first = type(candle("1m", 0))("EM02TST", "1m", 0, 59_999, 10, 12, 9, 11, 5, 55, 7, True, "rest")
    changed = type(first)(first.symbol, first.timeframe, first.open_time_ms, first.close_time_ms,
                          10, 13, 9, 12, 6, 72, 8, True, "rest")
    try:
        repository.upsert_candle(first); repository.upsert_candle(first)
        assert repository.count(first.symbol, "1m") == 1
        repository.upsert_candle(changed)
        assert repository.get_latest_closed_candle(first.symbol, "1m").high == 13
    finally:
        with factory() as session:
            session.execute(delete(Candle1m).where(Candle1m.symbol == first.symbol))
            session.commit()
