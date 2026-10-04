from datetime import datetime, timezone
import os

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.db.paper_models import PaperFirstCanarySessionRecord
from app.engine_paper.continuous_authority import PaperContinuousAuthorityStore
from app.engine_paper.first_canary_correlation import (
    CanaryCorrelationError,
    SqlAlchemyPaperFirstCanaryStore,
)


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def lifecycle_store():
    raw = os.environ.get("MULTI_POSITION_2_TEST_PG_URL")
    if not raw:
        pytest.skip("MULTI_POSITION_2_TEST_PG_URL is not configured")
    url = make_url(raw)
    if (
        url.get_backend_name() != "postgresql"
        or (url.database or "") != "traders_multi2_migration_test"
    ):
        pytest.fail("task-owned traders_multi2_migration_test PostgreSQL is required")
    engine = create_engine(raw, hide_parameters=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with engine.begin() as connection:
        assert connection.execute(text(
            "SELECT version_num FROM alembic_version"
        )).scalar_one() == "0037_continuous_two_lifecycle_slots"
        connection.execute(text(
            "TRUNCATE paper_first_canary_sessions, "
            "paper_continuous_control_events, paper_continuous_control CASCADE"
        ))
    authority = PaperContinuousAuthorityStore(factory)
    authority.activate(
        generation=16,
        source="MULTI_POSITION_2_TEST",
        reason="MULTI_POSITION_2_TEST",
        now=NOW,
    )
    try:
        yield SqlAlchemyPaperFirstCanaryStore(factory), factory
    finally:
        engine.dispose()


def _reserve(store, identity: str):
    return store.reserve_continuous_cycle(
        candidate_identity=identity,
        generation=16,
        control_transition_id="00000000-0000-4000-8000-000000000016",
        allowed_symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
        now=NOW,
    )


def test_two_slots_rehydrate_and_third_is_blocked(lifecycle_store) -> None:
    store, factory = lifecycle_store
    first = _reserve(store, "candidate-a")
    second = _reserve(store, "candidate-b")

    assert (first.lifecycle_slot, second.lifecycle_slot) == (1, 2)
    restarted = SqlAlchemyPaperFirstCanaryStore(factory)
    assert [value.canary_id for value in restarted.active()] == [
        first.canary_id, second.canary_id,
    ]
    with pytest.raises(
        CanaryCorrelationError,
        match="CONTINUOUS_LIFECYCLE_CAPACITY_EXHAUSTED",
    ):
        _reserve(restarted, "candidate-c")


def test_terminalizing_either_slot_preserves_the_other(lifecycle_store) -> None:
    store, factory = lifecycle_store
    first = _reserve(store, "candidate-a")
    second = _reserve(store, "candidate-b")

    store.fail_safe(first.canary_id, "TEST_CLOSE_A", NOW)
    active_after_a = SqlAlchemyPaperFirstCanaryStore(factory).active()
    assert [value.canary_id for value in active_after_a] == [second.canary_id]

    replacement = _reserve(store, "candidate-c")
    assert replacement.lifecycle_slot == 1
    store.fail_safe(second.canary_id, "TEST_CLOSE_B", NOW)
    active_after_b = SqlAlchemyPaperFirstCanaryStore(factory).active()
    assert [value.canary_id for value in active_after_b] == [replacement.canary_id]

    with factory() as session:
        rows = tuple(session.scalars(select(PaperFirstCanarySessionRecord)))
        assert len(rows) == 3
