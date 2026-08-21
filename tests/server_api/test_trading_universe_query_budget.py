from __future__ import annotations

from contextlib import contextmanager

from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter


class _CountingSession:
    def __init__(self) -> None:
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return ()

    def execute(self, statement):
        self.statements.append(statement)
        return ()


def test_trading_universe_readiness_has_three_bounded_database_round_trips():
    session = _CountingSession()

    @contextmanager
    def sessions():
        yield session

    adapter = SqlAlchemyReadAdapter(sessions)
    result = adapter.trading_universe_readiness()

    assert len(result) == 10
    assert len(session.statements) == 3
    rendered = [str(statement.compile(compile_kwargs={"literal_binds": True})) for statement in session.statements]
    assert rendered[1].count("UNION ALL") == 5
    assert "row_number() OVER" in rendered[2]
    assert "recency_rank = 1" in rendered[2]
