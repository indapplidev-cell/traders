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

    def export_rows(self, profile, from_ms, to_ms, symbol, limit):
        self.calls.append((profile, from_ms, to_ms, symbol, limit))
        return tuple(pair for pair in self.pairs if pair[0].trade_profile_id == profile and (symbol is None or pair[0].symbol == symbol))


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
    assert rows[1]["funnel_trace"]["paper_trade_plan"]["status"] == "NO_PLAN"
    assert rows[1]["funnel_trace"]["quantity_approved"]["status"] == "NOT_REACHED"
    assert rows[1]["geometry"]["final_stop"] == 99.25
    assert rows[1]["paper_outcome"]["position_id"] is None
    assert repo.calls[0][-1] == MAX_EXPORT_ROWS


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
    rows = repo.export_rows("trade-5m-v1", 1, 2_000_000_000_000, None, MAX_EXPORT_ROWS)
    sql = str(session.statement.compile(compile_kwargs={"literal_binds": True}))
    assert rows == (pair,) and session.calls == 1
    assert "trade-5m-v1" in sql and "LIMIT 2881" in sql
    assert all(token not in sql.upper() for token in ("UPDATE ", "DELETE ", "INSERT ", "ALTER "))
