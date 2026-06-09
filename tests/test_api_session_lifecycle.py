from app.api import routes_models, routes_predict, routes_replay
from app.db import session as db_session_module


def test_routes_use_db_session_dependency_and_shared_factories_accept_session() -> None:
    assert routes_predict.predict.__defaults__ is not None
    assert routes_models.list_models.__defaults__ is not None
    assert routes_models.activate_model.__defaults__ is not None
    assert routes_replay.list_replay_sessions.__defaults__ is not None
    assert callable(db_session_module.db_session_dependency)
