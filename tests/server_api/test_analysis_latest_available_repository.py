from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.engine_orchestrator.orchestrator_models import (
    OnlinePipelineResultRow,
    OnlinePipelineRun,
)
from app.server_api import create_app
from app.server_api.repositories.protocols import ApiRepositories
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter


OLD_BOUNDARY = datetime(2026, 7, 28, 7, 45, tzinfo=timezone.utc)
NEW_BOUNDARY = datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc)
OLD_BOUNDARY_MS = int(OLD_BOUNDARY.timestamp() * 1000)
NEW_BOUNDARY_MS = int(NEW_BOUNDARY.timestamp() * 1000)


def _database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    OnlinePipelineRun.__table__.create(engine)
    OnlinePipelineResultRow.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    adapter = SqlAlchemyReadAdapter(sessions)
    repositories = ApiRepositories(
        health=adapter,
        markets=adapter,
        analysis=adapter,
        setups=adapter,
        incidents=adapter,
        dashboard=adapter,
    )
    client = TestClient(create_app(repositories=repositories, clock=lambda: NEW_BOUNDARY))
    return engine, sessions, adapter, client


def _run(
    run_id: str,
    boundary: datetime,
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
    status: str = "COMPLETED",
    analysis_status: str | None = "ANALYZED",
    created_at: datetime | None = None,
) -> dict:
    return {
        "run_id": run_id,
        "symbol": symbol,
        "primary_timeframe": timeframe,
        "closed_until_ms": int(boundary.timestamp() * 1000),
        "closed_until_utc": boundary,
        "status": status,
        "trigger_source": "test_fixture",
        "daemon_instance_id": "test",
        "analysis_status": analysis_status,
        "future_bars_used": False,
        "is_trade_signal": False,
        "is_executable": False,
        "order_approved": False,
        "execution_approved": False,
        "position_opened": False,
        "position_size_approved": False,
        "created_at": created_at or boundary,
        "updated_at": created_at or boundary,
    }


def _analysis_payload(
    run: dict,
    *,
    snapshot_id: str | None = None,
    status: str = "ANALYZED",
    symbol: str | None = None,
    timeframe: str | None = None,
    closed_until_ms: int | None = None,
    future_bars_used: bool = False,
    degraded: bool = False,
    enough_data: bool = True,
) -> dict:
    return {
        "snapshot_id": snapshot_id or f"analysis:{run['run_id']}",
        "symbol": symbol or run["symbol"],
        "timeframe": timeframe or run["primary_timeframe"],
        "closed_until_ms": (
            run["closed_until_ms"]
            if closed_until_ms is None
            else closed_until_ms
        ),
        "created_at_ms": run["closed_until_ms"] + 1,
        "market_data_health": "OK",
        "future_bars_used": future_bars_used,
        "degraded": degraded,
        "enough_data": enough_data,
        "status": status,
        "regime": "TREND",
        "action": "BULLISH",
        "confidence": 0.8,
        "reason_codes": ["fixture"],
    }


def _result(
    run: dict,
    *,
    payload: dict | None = None,
    symbol: str | None = None,
    timeframe: str | None = None,
    closed_until_ms: int | None = None,
    created_at: datetime | None = None,
) -> dict:
    return {
        "run_id": run["run_id"],
        "symbol": symbol or run["symbol"],
        "primary_timeframe": timeframe or run["primary_timeframe"],
        "closed_until_ms": (
            run["closed_until_ms"]
            if closed_until_ms is None
            else closed_until_ms
        ),
        "market_data_payload_json": {},
        "analysis_payload_json": (
            _analysis_payload(run) if payload is None else payload
        ),
        "setup_payload_json": {},
        "strategy_payload_json": {},
        "risk_payload_json": {},
        "paper_payload_json": {},
        "module_reasons_json": {},
        "module_warnings_json": {},
        "safety_counters_json": {"future_bars_used_count": 0},
        "created_at": created_at or run["created_at"],
    }


def _insert(sessions, run: dict, result: dict | None = None) -> None:
    with sessions.begin() as session:
        session.execute(OnlinePipelineRun.__table__.insert(), run)
        if result is not None:
            session.execute(OnlinePipelineResultRow.__table__.insert(), result)


def _assert_analysis(response, boundary_ms: int, analysis_id: str) -> None:
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["data"]["closed_until_ms"] == boundary_ms
    assert payload["data"]["analysis_id"] == analysis_id
    assert payload["data"]["symbol"] == "BTCUSDT"


def test_original_race_sequence_never_transitions_200_to_404():
    _engine, sessions, _adapter, client = _database()
    old = _run("run-old", OLD_BOUNDARY)
    new = _run(
        "run-new",
        NEW_BOUNDARY,
        status="RUNNING",
        analysis_status=None,
    )
    _insert(sessions, old, _result(old))

    _assert_analysis(
        client.get("/api/v1/analysis/BTCUSDT"),
        OLD_BOUNDARY_MS,
        "analysis:run-old",
    )
    _insert(sessions, new)
    _assert_analysis(
        client.get("/api/v1/analysis/BTCUSDT"),
        OLD_BOUNDARY_MS,
        "analysis:run-old",
    )

    with sessions.begin() as session:
        session.execute(
            OnlinePipelineRun.__table__.update()
            .where(OnlinePipelineRun.run_id == "run-new")
            .values(status="COMPLETED", analysis_status="ANALYZED")
        )
        session.execute(
            OnlinePipelineResultRow.__table__.insert(),
            _result(new, created_at=NEW_BOUNDARY + timedelta(seconds=2)),
        )
    _assert_analysis(
        client.get("/api/v1/analysis/BTCUSDT"),
        NEW_BOUNDARY_MS,
        "analysis:run-new",
    )


def test_no_available_analysis_preserves_safe_resource_not_found_contract():
    _engine, sessions, _adapter, client = _database()
    run = _run(
        "run-no-analysis",
        NEW_BOUNDARY,
        analysis_status=None,
    )
    _insert(sessions, run)

    response = client.get("/api/v1/analysis/BTCUSDT")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert payload["error"]["message"] == "The requested resource was not found."
    assert "sql" not in str(payload).lower()


def test_newer_failed_run_without_result_does_not_hide_valid_older_result():
    _engine, sessions, adapter, _client = _database()
    old = _run("run-old", OLD_BOUNDARY)
    failed = _run(
        "run-failed",
        NEW_BOUNDARY,
        status="ERROR",
        analysis_status=None,
    )
    _insert(sessions, old, _result(old))
    _insert(sessions, failed)

    assert adapter.get_analysis("BTCUSDT").analysis_id == "analysis:run-old"


def test_ineligible_newer_rows_do_not_hide_valid_older_result():
    _engine, sessions, adapter, _client = _database()
    old = _run("run-old", OLD_BOUNDARY)
    _insert(sessions, old, _result(old))
    invalid_cases = [
        ("empty", {}, {}),
        ("wrong-module", {"setup_id": "setup:new"}, {}),
        ("wrong-status", _analysis_payload(_run("x", NEW_BOUNDARY), status="ERROR"), {}),
        ("wrong-payload-symbol", _analysis_payload(_run("x", NEW_BOUNDARY), symbol="ETHUSDT"), {}),
        ("wrong-payload-timeframe", _analysis_payload(_run("x", NEW_BOUNDARY), timeframe="1h"), {}),
        ("wrong-payload-boundary", _analysis_payload(_run("x", NEW_BOUNDARY), closed_until_ms=OLD_BOUNDARY_MS), {}),
        ("future-bars", _analysis_payload(_run("x", NEW_BOUNDARY), future_bars_used=True), {}),
        ("degraded", _analysis_payload(_run("x", NEW_BOUNDARY), degraded=True), {}),
        ("not-enough-data", _analysis_payload(_run("x", NEW_BOUNDARY), enough_data=False), {}),
        ("missing-snapshot-id", _analysis_payload(_run("x", NEW_BOUNDARY)), {}),
        ("missing-created-at", _analysis_payload(_run("x", NEW_BOUNDARY)), {}),
        ("missing-market-health", _analysis_payload(_run("x", NEW_BOUNDARY)), {}),
        ("wrong-result-symbol", _analysis_payload(_run("x", NEW_BOUNDARY)), {"symbol": "ETHUSDT"}),
    ]
    for index, (label, payload, result_overrides) in enumerate(invalid_cases):
        boundary = NEW_BOUNDARY + timedelta(minutes=15 * index)
        run = _run(f"run-invalid-{label}", boundary)
        payload = dict(payload)
        if payload:
            payload["snapshot_id"] = f"analysis:invalid:{label}"
            payload["symbol"] = payload.get("symbol", run["symbol"])
            payload["timeframe"] = payload.get("timeframe", run["primary_timeframe"])
            if label not in {"wrong-payload-boundary"}:
                payload["closed_until_ms"] = run["closed_until_ms"]
            if label == "missing-snapshot-id":
                payload.pop("snapshot_id")
            if label == "missing-created-at":
                payload.pop("created_at_ms")
            if label == "missing-market-health":
                payload.pop("market_data_health")
        _insert(
            sessions,
            run,
            _result(run, payload=payload, **result_overrides),
        )

    assert adapter.get_analysis("BTCUSDT").analysis_id == "analysis:run-old"


def test_multiple_valid_results_use_boundary_creation_and_stable_id_order():
    _engine, sessions, adapter, _client = _database()
    older = _run("run-older", OLD_BOUNDARY)
    tied_timestamp = NEW_BOUNDARY + timedelta(seconds=1)
    tied_first = _run("run-tied-first", NEW_BOUNDARY, created_at=tied_timestamp)
    wrong_timeframe = _run(
        "run-wrong-timeframe",
        NEW_BOUNDARY + timedelta(minutes=15),
        timeframe="1h",
        created_at=tied_timestamp,
    )
    _insert(sessions, older, _result(older))
    _insert(sessions, tied_first, _result(tied_first))
    _insert(sessions, wrong_timeframe, _result(wrong_timeframe))

    values = [adapter.get_analysis("BTCUSDT") for _ in range(20)]

    assert {item.analysis_id for item in values} == {"analysis:run-tied-first"}
    assert {item.closed_until_ms for item in values} == {NEW_BOUNDARY_MS}


def test_repository_normalizes_symbol_and_does_not_require_downstream_completion():
    _engine, sessions, adapter, _client = _database()
    run = _run("run-analysis-only", NEW_BOUNDARY, status="RUNNING")
    result = _result(run)
    assert result["setup_payload_json"] == {}
    assert result["strategy_payload_json"] == {}
    assert result["risk_payload_json"] == {}
    _insert(sessions, run, result)

    record = adapter.get_analysis("btcusdt")

    assert record is not None
    assert record.analysis_id == "analysis:run-analysis-only"


def test_wrong_module_result_does_not_hide_valid_analysis():
    _engine, sessions, adapter, _client = _database()
    old = _run("run-old", OLD_BOUNDARY)
    newer = _run("run-setup-only", NEW_BOUNDARY, analysis_status=None)
    setup_only = _result(newer, payload={})
    setup_only["setup_payload_json"] = {
        "setup_id": "setup:new",
        "status": "READY",
    }
    _insert(sessions, old, _result(old))
    _insert(sessions, newer, setup_only)

    assert adapter.get_analysis("BTCUSDT").analysis_id == "analysis:run-old"


def test_all_candidates_invalid_preserves_resource_not_found():
    _engine, sessions, _adapter, client = _database()
    invalid = _run("run-invalid", NEW_BOUNDARY)
    _insert(
        sessions,
        invalid,
        _result(
            invalid,
            payload=_analysis_payload(invalid, future_bars_used=True),
        ),
    )

    response = client.get("/api/v1/analysis/BTCUSDT")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "RESOURCE_NOT_FOUND"
    assert error["message"] == "The requested resource was not found."
    assert "sql" not in str(error).lower()


def test_analysis_response_schema_is_unchanged():
    _engine, sessions, _adapter, client = _database()
    run = _run("run-schema", NEW_BOUNDARY)
    _insert(sessions, run, _result(run))

    data = client.get("/api/v1/analysis/BTCUSDT").json()["data"]

    assert set(data) == {
        "analysis_id",
        "symbol",
        "timeframe",
        "closed_until",
        "closed_until_ms",
        "status",
        "market_data_status",
        "regime",
        "direction",
        "confidence",
        "impulse_phase",
        "entry_quality",
        "reason_codes",
        "updated_at",
    }


def test_query_joins_only_an_eligible_result_and_is_deterministic_and_bounded():
    engine, sessions, adapter, _client = _database()
    run = _run("run-valid", OLD_BOUNDARY)
    _insert(sessions, run, _result(run))
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(" ".join(statement.lower().split()))

    assert adapter.get_analysis("BTCUSDT") is not None

    assert len(statements) == 1
    sql = statements[0]
    assert " from online_pipeline_runs join online_pipeline_results " in f" {sql} "
    assert "online_pipeline_results_1.run_id = online_pipeline_runs.run_id" in sql
    assert "left outer join" not in sql
    assert " order by online_pipeline_runs.closed_until_ms desc" in sql
    assert "online_pipeline_results.created_at desc" in sql
    assert "online_pipeline_results.id desc" in sql
    assert sql.count(" limit ") == 2
    assert " as integer" not in sql
    assert "cast(online_pipeline_runs.closed_until_ms as varchar)" in sql


def test_unsupported_symbol_and_invalid_path_forms_are_safe():
    _engine, _sessions, adapter, client = _database()

    assert adapter.get_analysis("SOLUSDT") is None
    for path in (
        "/api/v1/analysis/SOLUSDT",
        "/api/v1/analysis/BTCUSDT%20",
        "/api/v1/analysis/%E2%80%8BBTCUSDT",
    ):
        response = client.get(path)
        expected = 404 if path.endswith("SOLUSDT") else 422
        assert response.status_code == expected
        assert response.json()["error"]["code"] == (
            "RESOURCE_NOT_FOUND" if expected == 404 else "INVALID_REQUEST"
        )


def test_database_unavailable_is_internal_error_not_not_found():
    engine, _sessions, adapter, _client = _database()
    engine.dispose()
    repositories = ApiRepositories(
        health=adapter,
        markets=adapter,
        analysis=adapter,
        setups=adapter,
        incidents=adapter,
        dashboard=adapter,
    )
    client = TestClient(
        create_app(repositories=repositories, clock=lambda: NEW_BOUNDARY),
        raise_server_exceptions=False,
    )

    response = client.get("/api/v1/analysis/BTCUSDT")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_aggregate_latest_analysis_is_one_query_latest_only_and_deterministic():
    engine, sessions, adapter, _client = _database()
    btc_old = _run("btc-old", OLD_BOUNDARY)
    btc_new = _run("btc-new", NEW_BOUNDARY)
    eth = _run("eth-new", NEW_BOUNDARY, symbol="ETHUSDT")
    _insert(sessions, btc_old, _result(btc_old))
    _insert(sessions, btc_new, _result(btc_new))
    _insert(sessions, eth, _result(eth))
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(" ".join(statement.lower().split()))

    values = adapter.list_latest_analyses(("ETHUSDT", "BTCUSDT"))

    assert [item.symbol for item in values] == ["BTCUSDT", "ETHUSDT"]
    assert values[0].analysis_id == "analysis:btc-new"
    assert len(statements) == 1
    assert "row_number() over" not in statements[0]
    assert " union all " in statements[0]
    assert statements[0].count(" limit ") >= 3


def test_aggregate_matches_single_symbol_latest_semantics_for_ten_symbol_bound():
    _engine, sessions, adapter, _client = _database()
    symbols = (
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
        "BNBUSDT", "DOGEUSDT", "LINKUSDT", "SUIUSDT", "XRPUSDT",
    )
    for symbol in symbols[:-1]:
        old = _run(f"{symbol}-old", OLD_BOUNDARY, symbol=symbol)
        new = _run(f"{symbol}-new", NEW_BOUNDARY, symbol=symbol)
        invalid = _run(
            f"{symbol}-invalid", NEW_BOUNDARY + timedelta(minutes=15), symbol=symbol
        )
        _insert(sessions, old, _result(old))
        _insert(sessions, new, _result(new))
        _insert(
            sessions,
            invalid,
            _result(
                invalid,
                payload=_analysis_payload(invalid, degraded=True),
            ),
        )

    aggregate = adapter.list_latest_analyses(symbols)
    singles = tuple(
        value for symbol in symbols
        if (value := adapter.get_analysis(symbol)) is not None
    )

    assert len(aggregate) == len(symbols) - 1
    assert aggregate == tuple(sorted(singles, key=lambda item: item.symbol))
    assert all(item.analysis_id.endswith("-new") for item in aggregate)
    assert adapter.list_latest_analyses(symbols + ("EXTRAUSDT",)) == ()
