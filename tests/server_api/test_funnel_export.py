from __future__ import annotations

import csv
import io
import json
from dataclasses import replace
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.engine_orchestrator.orchestrator_models import OnlinePipelineResultRow, OnlinePipelineRun
from app.server_api.app_factory import create_app
from app.server_api.funnel_export import EXPORT_SCHEMA_VERSION, MAX_EXPORT_ROWS
from app.server_api.trading_funnel import TradingFunnelReadRepository
from tests.server_api.fakes import FakeReadRepository


NOW = datetime(2030, 3, 17, 18, 0, tzinfo=timezone.utc)
FROM = "2030-03-17T17:00:00Z"
TO = "2030-03-17T18:00:00Z"


def _pair(profile="trade-15m-v1", symbol="BTCUSDT", boundary=1_900_000_200_000, rejected=False):
    timeframe = "5m" if profile == "trade-5m-v1" else "15m"
    stamp = datetime.fromtimestamp(boundary / 1000, timezone.utc)
    run = OnlinePipelineRun(
        id=1, run_id=f"run:{profile}:{symbol}:{boundary}", trade_profile_id=profile,
        profile_mode="PRODUCTION_SEARCH", symbol=symbol, primary_timeframe=timeframe,
        closed_until_ms=boundary, closed_until_utc=stamp, status="COMPLETED",
        started_at=stamp, finished_at=stamp, duration_ms=12, trigger_source="scheduled",
        daemon_instance_id="safe-runtime", updated_at=stamp,
        analysis_status="ANALYZED", setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH", paper_status="NO_PLAN" if rejected else "PAPER_PLAN_READY",
        final_reason="PAPER_REJECT_LOW_NET_RR" if rejected else None,
    )
    diagnostic = {
        "entry": 100, "atr": 1, "causal_invalidation": 99.5, "raw_stop": 99.25,
        "final_stop": 99.25, "stop_distance_bps": 75, "stop_envelope_bps": 80,
        "stop_envelope_pass": True, "causal_target": 101.5, "target_source_type": "LOCAL",
        "target_distance_bps": 150, "target_available": True, "entry_fee_bps": 10,
        "exit_fee_bps": 10, "spread_bps": 1, "entry_slippage_bps": 2,
        "exit_slippage_bps": 2, "depth_impact_bps": 1, "safety_margin_bps": 3,
        "total_cost_bps": 29, "gross_rr": 2, "net_rr": 1.16,
        "expected_net_edge_bps": 121, "break_even_win_rate": .463,
        "economic_gate_enabled": True, "economic_gate_pass": not rejected,
    }
    result = OnlinePipelineResultRow(
        id=1, run_id=run.run_id, trade_profile_id=profile, profile_mode="PRODUCTION_SEARCH",
        symbol=symbol, primary_timeframe=timeframe, closed_until_ms=boundary,
        market_data_payload_json={tf: {"closed_until_ms": boundary} for tf in ("1m", "5m", "15m", "1h", "4h")},
        analysis_payload_json={"status": "ANALYZED", "regime": "UP"},
        setup_payload_json={"setup_status": "SETUP_CANDIDATE", "setup_type": "BREAKOUT", "direction_hint": "BULLISH"},
        strategy_payload_json={"decision_status": "ALLOW_RESEARCH_TRADE_PLAN", "direction_hint": "BULLISH"},
        risk_payload_json={"risk_status": "RISK_PRE_APPROVED_RESEARCH", "execution_budget_reserved": False},
        paper_payload_json={
            "paper_status": "NO_PLAN" if rejected else "PAPER_PLAN_READY", "paper_direction": "BULLISH",
            "runtime_parameter_set_id": f"{profile}-runtime-v1-testhash",
            "paper_context": {"scalping_geometry_diagnostics": diagnostic},
        },
        module_reasons_json={"paper": ["PAPER_REJECT_LOW_NET_RR"]} if rejected else {},
        module_warnings_json={}, safety_counters_json={}, created_at=stamp,
    )
    return run, result


class ExportRepo:
    def __init__(self, pairs):
        self.pairs = tuple(pairs)
        self.calls = []

    def project(self, *_args):
        raise AssertionError("screen projection must not serve export")

    def export_rows(self, profile, from_ms, to_ms, symbol, limit, after=None):
        self.calls.append((profile, from_ms, to_ms, symbol, limit, after))
        pairs = sorted(
            (pair for pair in self.pairs if pair[0].trade_profile_id == profile
             and from_ms <= pair[0].closed_until_ms <= to_ms
             and (symbol is None or pair[0].symbol == symbol)),
            key=lambda pair: (pair[0].closed_until_ms, pair[0].symbol, pair[0].run_id),
        )
        if after is not None:
            pairs = [pair for pair in pairs if (pair[0].closed_until_ms, pair[0].symbol, pair[0].run_id) > after]
        return tuple(pairs[:limit + 1])

    def export_bounds(self, profile, symbol):
        values = [pair[0].closed_until_ms for pair in self.pairs
                  if pair[0].trade_profile_id == profile and (symbol is None or pair[0].symbol == symbol)]
        return (min(values), max(values)) if values else (None, None)


def _client(repo):
    repositories = replace(FakeReadRepository().api_repositories(), funnel=repo)
    return TestClient(create_app(repositories=repositories, clock=lambda: NOW))


def _get(client, **params):
    query = {"trade_profile_id": "trade-15m-v1", "from": FROM, "to": TO, "format": "jsonl", **params}
    return client.get("/api/v1/trading/funnel/export", params=query)


def test_jsonl_is_profile_isolated_deterministic_complete_and_null_preserving():
    late = _pair(symbol="ETHUSDT", boundary=1_900_000_500_000, rejected=True)
    early = _pair(symbol="BTCUSDT", boundary=1_900_000_200_000)
    other = _pair(profile="trade-5m-v1")
    repo = ExportRepo((late, other, early))
    response = _get(_client(repo))
    assert response.status_code == 200
    rows = [json.loads(line) for line in response.text.splitlines()]
    assert [row["market_analysis"]["symbol"] for row in rows] == ["BTCUSDT", "ETHUSDT"]
    assert all(row["provenance"]["trade_profile_id"] == "trade-15m-v1" for row in rows)
    assert rows[0]["provenance"]["export_schema_version"] == EXPORT_SCHEMA_VERSION
    assert set(rows[1]["funnel_trace"]) == {
        "analysis", "setup", "strategy", "geometry", "cost", "risk",
        "paper_plan", "final_approval", "paper_command", "position", "exit",
    }
    assert rows[1]["funnel_trace"]["paper_plan"]["status"] == "NO_PLAN"
    assert rows[1]["funnel_trace"]["paper_command"]["status"] == "NOT_REACHED"
    assert rows[1]["geometry"]["final_stop"] == 99.25
    assert rows[1]["paper_outcome"]["position_id"] is None
    assert repo.calls[0][4] == MAX_EXPORT_ROWS


def test_symbol_filter_csv_and_summary_formats():
    repo = ExportRepo((_pair(), _pair(symbol="ETHUSDT", rejected=True)))
    client = _client(repo)
    response = _get(client, symbol="BTCUSDT", format="csv")
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == 1 and rows[0]["market_analysis.symbol"] == "BTCUSDT"
    summary = _get(client, format="summary-json").json()
    assert summary["profile"] == "trade-15m-v1" and summary["evaluations"] == 2
    assert "stop_distance" in summary and "rr_cohorts" in summary
    markdown = _get(client, format="summary-md")
    assert markdown.status_code == 200 and "# Trading Funnel report" in markdown.text


def test_empty_summary_is_explicit_and_range_format_candles_are_bounded():
    client = _client(ExportRepo(()))
    assert _get(client, format="summary-json").json()["sample_status"] == "INSUFFICIENT_SAMPLE"
    too_wide = client.get("/api/v1/trading/funnel/export", params={
        "trade_profile_id": "trade-5m-v1", "from": "2030-03-16T17:59:59Z", "to": TO, "format": "jsonl",
    })
    assert too_wide.status_code == 422
    assert _get(client, include_candles="true").status_code == 422
    assert _get(client, include_candles="false").status_code == 200
    assert client.post("/api/v1/trading/funnel/export").status_code == 405


def test_secret_like_raw_reason_is_dropped():
    run, result = _pair(rejected=True)
    run.final_reason = "password=do-not-export"
    result.module_reasons_json = {"paper": ["authorization bearer hidden"]}
    row = json.loads(_get(_client(ExportRepo(((run, result),)))).text)
    rendered = json.dumps(row).casefold()
    assert "do-not-export" not in rendered and "bearer hidden" not in rendered


def test_repository_uses_one_bounded_statement_and_no_profile_mixing():
    pair = _pair(profile="trade-5m-v1")

    class Session:
        calls = 0
        statement = None
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def execute(self, statement):
            self.calls += 1; self.statement = statement
            return (pair,)

    session = Session()
    universe = type("Universe", (), {"symbols": ("BTCUSDT",), "version_id": "v2"})()
    repo = TradingFunnelReadRepository(lambda: session, lambda: universe)
    rows = repo.export_rows(
        "trade-5m-v1", 1, 2_000_000_000_000, None, MAX_EXPORT_ROWS,
        (1_899_000_000_000, "BTCUSDT", "run-before"),
    )
    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert rows == (pair,) and session.calls == 1
    assert "trade-5m-v1" in sql and "LIMIT 2881" in sql
    assert "online_pipeline_runs.closed_until_ms, online_pipeline_runs.symbol, online_pipeline_runs.run_id" in sql
    assert "OFFSET" not in sql.upper()
    assert all(token not in sql.upper() for token in ("UPDATE ", "DELETE ", "INSERT ", "ALTER "))


def test_arbitrary_range_keyset_pages_are_stable_complete_and_tamper_validated():
    boundaries = [1_899_000_000_000 + index * 300_000 for index in range(5)]
    repo = ExportRepo(tuple(_pair(profile="trade-5m-v1", boundary=value) for value in boundaries))
    client = _client(repo)
    query = {
        "trade_profile_id": "trade-5m-v1", "from": "2029-01-01T00:00:00Z",
        "to": "2031-01-01T00:00:00Z", "format": "jsonl-records", "page_size": 2,
    }
    first = client.get("/api/v1/trading/funnel/export", params=query)
    assert first.status_code == 200
    first_page = first.json()
    assert first_page["page_row_count"] == 2 and first_page["has_more"] is True
    assert first_page["available_from"] == boundaries[0] and first_page["available_to"] == boundaries[-1]
    snapshot = first_page["snapshot_closed_until"]

    # A later run arrives after the snapshot starts and must not drift into this export.
    repo.pairs += (_pair(profile="trade-5m-v1", boundary=boundaries[-1] + 300_000),)
    rows = list(first_page["records"])
    cursor = first_page["next_cursor"]
    while cursor is not None:
        response = client.get("/api/v1/trading/funnel/export", params={
            **query, "cursor": cursor, "snapshot_closed_until": snapshot,
        })
        assert response.status_code == 200
        page = response.json(); rows.extend(page["records"]); cursor = page["next_cursor"]
    keys = [(row["provenance"]["trade_profile_id"], row["market_analysis"]["boundary_closed_at_ms"],
             row["market_analysis"]["symbol"], row["provenance"]["source_run_id"]) for row in rows]
    assert len(keys) == len(set(keys)) == 5
    assert keys == sorted(keys, key=lambda item: (item[1], item[2], item[3]))
    assert all(item[1] <= snapshot for item in keys)
    assert all(call[4] == 2 for call in repo.calls)

    tampered = first_page["next_cursor"][:-1] + ("A" if first_page["next_cursor"][-1] != "A" else "B")
    assert client.get("/api/v1/trading/funnel/export", params={
        **query, "cursor": tampered, "snapshot_closed_until": snapshot,
    }).status_code == 422
    assert client.get("/api/v1/trading/funnel/export", params={
        **query, "trade_profile_id": "trade-15m-v1", "cursor": first_page["next_cursor"],
        "snapshot_closed_until": snapshot,
    }).status_code == 422


def test_paged_mode_accepts_both_profiles_all_range_classes_and_bounded_page_sizes():
    pairs = (_pair(profile="trade-5m-v1"), _pair(profile="trade-15m-v1"))
    client = _client(ExportRepo(pairs))
    ranges = (
        ("2030-03-17T17:50:00Z", TO),
        (FROM, TO),
        ("2030-03-16T18:00:00Z", TO),
        ("2030-03-10T18:00:00Z", TO),
        ("2030-02-15T18:00:00Z", TO),
        ("2020-01-01T00:00:00Z", TO),
    )
    for profile in ("trade-5m-v1", "trade-15m-v1"):
        for from_value, to_value in ranges:
            response = client.get("/api/v1/trading/funnel/export", params={
                "trade_profile_id": profile, "from": from_value, "to": to_value,
                "format": "jsonl-records",
            })
            assert response.status_code == 200
            assert response.json()["trade_profile_id"] == profile
        for page_size in (1, 200, 2000):
            assert client.get("/api/v1/trading/funnel/export", params={
                "trade_profile_id": profile, "from": FROM, "to": TO,
                "format": "csv-records", "page_size": page_size,
            }).status_code == 200
    assert client.get("/api/v1/trading/funnel/export", params={
        "trade_profile_id": "trade-5m-v1", "from": FROM, "to": TO,
        "format": "jsonl-records", "page_size": 2001,
    }).status_code == 422


def test_cursor_snapshot_mismatch_and_empty_partial_availability_are_explicit():
    boundary = 1_900_000_200_000
    client = _client(ExportRepo((_pair(profile="trade-5m-v1", boundary=boundary),
                                 _pair(profile="trade-5m-v1", boundary=boundary + 300_000))))
    query = {"trade_profile_id": "trade-5m-v1", "from": "2020-01-01T00:00:00Z", "to": TO,
             "format": "jsonl-records", "page_size": 1}
    first = client.get("/api/v1/trading/funnel/export", params=query).json()
    assert first["available_from"] == boundary and first["available_from"] > first["requested_from"]
    assert client.get("/api/v1/trading/funnel/export", params={
        **query, "cursor": first["next_cursor"], "snapshot_closed_until": first["snapshot_closed_until"] - 1,
    }).status_code == 422
    empty = _client(ExportRepo(())).get("/api/v1/trading/funnel/export", params=query)
    assert empty.status_code == 200
    assert empty.json()["records"] == [] and empty.json()["available_from"] is None
