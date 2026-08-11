from __future__ import annotations

from contextlib import nullcontext
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import delete, text

from app.engine_orchestrator.orchestrator_models import OnlinePipelineRun
from app.engine_paper import production_approval as approval
from app.engine_paper.paper_approvals import (
    PaperQuantityApprovalSource,
    approval_serialization,
    finalize_paper_risk_approval,
    finalize_paper_strategy_approval,
    issue_paper_quantity_approval,
)
from app.engine_risk.risk_decision import RiskDecision
from app.engine_safety.paper_domain import ExecutionMode, PaperInputHealthStatus, PaperSide
from app.engine_strategy.strategy_decision import StrategyDecision


CLOSED = 1_900_000_000_000
AS_OF = CLOSED + 5_000
VALID = CLOSED + 60_000
APPROVED_AT = datetime.fromtimestamp((CLOSED + 1_000) / 1000, tz=timezone.utc)


class FakeSession:
    def __init__(self, error=None):
        self.error = error
        self.statements = []
        self.begin_count = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.closed = True

    def begin(self):
        self.begin_count += 1
        return nullcontext()

    def execute(self, statement, parameters=None):
        self.statements.append(statement)
        if self.error:
            raise self.error
        return object()


class FakeReader:
    def __init__(self, rows=None, *, now=AS_OF, failure=None):
        self.rows = rows or {}
        self.now = now
        self.failure = failure
        self.snapshot = None

    def read_clock_ms(self, executor):
        executor.query_count += 1
        if self.failure:
            raise self.failure
        return self.now

    def read_recent(self, executor, symbol, timeframe, limit, start_ms):
        executor.query_count += 1
        if self.failure:
            raise self.failure
        values = tuple(self.rows.get(symbol, ()))
        if self.snapshot is None:
            self.snapshot = values
        values = self.snapshot if len(self.rows) == 1 else values
        if start_ms is not None:
            values = tuple(value for value in values if value.closed_until_ms >= start_ms)
        return values[:limit]


class Token:
    def __init__(self, value=True): self.value = value
    def is_set(self): return self.value


def research_strategy():
    return StrategyDecision(
        decision_id="strategy:1", created_at_ms=CLOSED + 1,
        source_setup_id="setup:1", source_analysis_snapshot_id="analysis:1",
        symbol="BTCUSDT", timeframe="15m", closed_until_ms=CLOSED,
        decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        strategy_type="BREAKOUT_CONTINUATION_RESEARCH", direction_hint="BULLISH",
        setup_status="SETUP_CANDIDATE", setup_type="BREAKOUT_CONTINUATION",
        setup_quality="GOOD", setup_quality_score=90.0, strategy_score=82.0,
        strategy_quality="ACCEPTABLE", required_next_layer="engine_risk",
        requires_risk_review=True,
    )


def research_risk():
    return RiskDecision(
        risk_decision_id="risk:1", created_at_ms=CLOSED + 2,
        source_strategy_decision_id="strategy:1", source_setup_id="setup:1",
        source_analysis_snapshot_id="analysis:1", symbol="BTCUSDT",
        timeframe="15m", closed_until_ms=CLOSED,
        risk_status="RISK_PRE_APPROVED_RESEARCH", risk_level="LOW", risk_score=90.0,
        risk_policy_version="risk-v1",
        source_decision_status="ALLOW_RESEARCH_TRADE_PLAN",
        source_strategy_type="BREAKOUT_CONTINUATION_RESEARCH",
        source_strategy_quality="ACCEPTABLE", source_strategy_score=82.0,
        direction_hint="BULLISH", risk_pre_approved=True,
        requires_execution_review=True,
    )


def approval_chain():
    strategy_input = research_strategy()
    risk_input = research_risk()
    strategy = finalize_paper_strategy_approval(
        strategy_input, mode=ExecutionMode.PAPER, paper_authorized=True,
        setup_id="setup:1", pipeline_run_id="run:1", analysis_result_id="analysis:1",
        side=PaperSide.LONG, entry_reference_price=Decimal("100"),
        stop_price=Decimal("90"), target_price=Decimal("120"), approved_at=APPROVED_AT,
        valid_until_ms=VALID, configuration_fingerprint="config:v1",
        symbol_constraints_id="constraints:BTCUSDT:v1",
        input_health_status=PaperInputHealthStatus.CURRENT, future_bars_used=False,
        correlation_id="run:1", causation_id="strategy:1", evaluation_time_ms=AS_OF,
    )
    quantity = issue_paper_quantity_approval(
        strategy, risk_input, mode=ExecutionMode.PAPER, paper_authorized=True,
        requested_quantity=Decimal("2"),
        approval_source=PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY,
        approved_at=APPROVED_AT, valid_until_ms=VALID, evaluation_time_ms=AS_OF,
        correlation_id="run:1", causation_id=strategy.approval_id,
    )
    risk = finalize_paper_risk_approval(
        strategy, risk_input, quantity, mode=ExecutionMode.PAPER, paper_authorized=True,
        approved_at=APPROVED_AT, evaluation_time_ms=AS_OF,
        correlation_id="run:1", causation_id=quantity.quantity_approval_id,
    )
    return strategy, quantity, risk


def row(**changes):
    analysis_payload = {
        "snapshot_id": "analysis:1", "source_market_data_snapshot_id": "market-snapshot:1",
        "symbol": "BTCUSDT", "timeframe": "15m", "closed_until_ms": CLOSED,
        "created_at_ms": CLOSED + 1, "future_bars_used": False,
    }
    setup_payload = {
        "setup_id": "setup:1", "source_analysis_snapshot_id": "analysis:1",
        "symbol": "BTCUSDT", "closed_until_ms": CLOSED, "created_at_ms": CLOSED + 2,
        "status": "SETUP_CANDIDATE",
    }
    strategy_payload = {
        **research_strategy().to_dict(), "created_at_ms": CLOSED + 3,
    }
    risk_payload = {**research_risk().to_dict(), "created_at_ms": CLOSED + 4}
    paper_payload = {
        "paper_plan_id": "paper:1", "source_risk_decision_id": "risk:1",
        "source_strategy_decision_id": "strategy:1", "source_setup_id": "setup:1",
        "source_analysis_snapshot_id": "analysis:1", "symbol": "BTCUSDT",
        "closed_until_ms": CLOSED, "created_at_ms": CLOSED + 5,
    }
    values = dict(
        run_pk=1, result_pk=1, run_id="run:1", symbol="BTCUSDT",
        primary_timeframe="15m", closed_until_ms=CLOSED, status="COMPLETED",
        finished_at=APPROVED_AT, freshness_deadline_at=None, future_bars_used=False,
        is_trade_signal=True, is_executable=True, order_approved=True,
        execution_approved=True, position_opened=False, position_size_approved=True,
        analysis_status="ANALYZED", setup_status="SETUP_CANDIDATE",
        strategy_status="ALLOW_RESEARCH_TRADE_PLAN",
        risk_status="RISK_PRE_APPROVED_RESEARCH", paper_status="PAPER_PLAN_READY",
        analysis=analysis_payload, setup=setup_payload, strategy=strategy_payload,
        risk=risk_payload, paper=paper_payload,
    )
    values.update(changes)
    return approval._PersistedDecision(**values)


def eligible_row():
    strategy, quantity, risk = approval_chain()
    base = row()
    paper = dict(base.paper)
    paper["persisted_final_approvals"] = {
        "paper_strategy_approval": approval_serialization(strategy),
        "paper_quantity_approval": approval_serialization(quantity),
        "paper_risk_approval": approval_serialization(risk),
    }
    return replace(base, paper=paper)


def rebase(value, *, run_pk, run_id, closed_until_ms):
    def payload(source):
        result = dict(source)
        result["closed_until_ms"] = closed_until_ms
        return result
    return replace(
        value, run_pk=run_pk, run_id=run_id, closed_until_ms=closed_until_ms,
        analysis=payload(value.analysis), setup=payload(value.setup),
        strategy=payload(value.strategy), risk=payload(value.risk), paper=payload(value.paper),
    )


def request(symbols=("BTCUSDT",), **changes):
    scope = approval.PaperProductionApprovalScope(tuple(symbols), **changes)
    return approval.PaperProductionApprovalRequest(scope, "approval-read:1", AS_OF)


def service(rows, *, reader=None, session=None, ticks=(1.0, 1.001)):
    reader = reader or FakeReader(rows)
    session = session or FakeSession()
    values = iter(ticks)
    return approval.PaperProductionApprovalSourceAdapter(
        lambda: session, reader=reader, monotonic=lambda: next(values)
    ), session


def test_authoritative_contract_and_no_decision_engine_dependencies():
    source = Path(approval.__file__).read_text(encoding="utf-8")
    assert approval.AUTHORITATIVE_SOURCE == "PRODUCTION_PERSISTED_ONLINE_PIPELINE_RESULTS"
    assert "process_strategy_decision" not in source
    assert "process_setup_candidate" not in source
    assert "command_ingestion_service" not in source
    assert "OrderExecution" not in source
    assert "Binance" not in source


def test_all_required_contracts_are_frozen():
    value = request()
    with pytest.raises(FrozenInstanceError):
        value.request_id = "changed"
    result = service({"BTCUSDT": (row(is_trade_signal=False),)})[0].read(value)
    with pytest.raises(FrozenInstanceError):
        result.outcome = approval.PaperProductionApprovalOutcome.SAFE_FAILURE


@pytest.mark.parametrize("case", range(1400))
def test_1400_deterministic_no_trade_and_fail_closed_matrix(case):
    symbol = approval.SYMBOL_ALLOWLIST[case % 3]
    base = row(
        run_pk=case + 1, run_id=f"run:{case + 1}", symbol=symbol,
        is_trade_signal=False, is_executable=False, order_approved=False,
        execution_approved=False, position_size_approved=False,
        setup_status=("NO_SETUP", "WAIT_FOR_CONFIRMATION", "SETUP_INVALID")[case % 3],
        strategy_status=("NO_DECISION", "WAIT", "REJECT")[case % 3],
        risk_status=("NO_DECISION", "WAIT", "REJECT")[case % 3],
        analysis={**row().analysis, "symbol": symbol},
        setup={**row().setup, "symbol": symbol},
        strategy={**row().strategy, "symbol": symbol},
        risk={**row().risk, "symbol": symbol},
        paper={**row().paper, "symbol": symbol},
    )
    first = service({symbol: (base,)})[0].read(request((symbol,)))
    second = service({symbol: (base,)})[0].read(request((symbol,)))
    assert first.outcome is approval.PaperProductionApprovalOutcome.NO_TRADE_SIGNAL
    assert first.readiness is approval.PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL
    assert first.candidates == ()
    assert first.symbol_results == second.symbol_results
    assert first.findings == second.findings


@pytest.mark.parametrize("field,outcome", [
    ("setup_status", approval.PaperProductionApprovalOutcome.SETUP_NOT_ELIGIBLE),
    ("strategy_status", approval.PaperProductionApprovalOutcome.STRATEGY_NOT_EXECUTABLE),
    ("risk_rejected", approval.PaperProductionApprovalOutcome.RISK_REJECTED),
    ("risk_deferred", approval.PaperProductionApprovalOutcome.RISK_DEFERRED),
    ("approval_missing", approval.PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL),
])
def test_authoritative_status_mapping(field, outcome):
    changes = {}
    if field == "setup_status": changes["setup_status"] = "NO_SETUP"
    elif field == "strategy_status": changes.update(strategy_status="WAIT", is_executable=False)
    elif field == "risk_rejected": changes["risk_status"] = "RISK_REJECTED"
    elif field == "risk_deferred": changes["risk_status"] = "RISK_DEFERRED"
    result = service({"BTCUSDT": (row(**changes),)})[0].read(request())
    assert result.outcome is outcome
    assert not result.candidates


def test_complete_persisted_approval_chain_reuses_authority_and_is_deterministic():
    value = eligible_row()
    first = service({"BTCUSDT": (value,)})[0].read(request())
    second = service({"BTCUSDT": (value,)})[0].read(request())
    assert first.outcome is approval.PaperProductionApprovalOutcome.ELIGIBLE_APPROVAL
    assert first.readiness is approval.PaperProductionApprovalReadiness.READY
    assert first.candidates == second.candidates
    candidate = first.candidates[0]
    assert candidate.quantity_authority.approved_quantity == Decimal("2")
    assert candidate.quantity_authority.approval_source is PaperQuantityApprovalSource.CONTROLLED_PAPER_AUTHORITY
    assert candidate.lineage.source_run_id == "run:1"
    assert candidate.watermark.source_market_data_snapshot_id == "market-snapshot:1"


@pytest.mark.parametrize("change,outcome", [
    ({"order_approved": False}, approval.PaperProductionApprovalOutcome.APPROVAL_NOT_FINAL),
    ({"execution_approved": False}, approval.PaperProductionApprovalOutcome.EXECUTION_NOT_APPROVED),
    ({"position_size_approved": False}, approval.PaperProductionApprovalOutcome.QUANTITY_NOT_APPROVED),
    ({"position_opened": True}, approval.PaperProductionApprovalOutcome.CAUSALITY_MISMATCH),
    ({"future_bars_used": True}, approval.PaperProductionApprovalOutcome.FUTURE_DECISION),
])
def test_persisted_boolean_incoherence_fails_closed(change, outcome):
    result = service({"BTCUSDT": (replace(eligible_row(), **change),)})[0].read(request())
    assert result.outcome is outcome
    assert not result.candidates


def test_symbol_side_lineage_watermark_and_future_mismatches_fail_closed():
    base = eligible_row()
    cases = []
    cases.append((replace(base, analysis={**base.analysis, "symbol": "ETHUSDT"}), approval.PaperProductionApprovalOutcome.SYMBOL_MISMATCH))
    cases.append((replace(base, setup={**base.setup, "source_analysis_snapshot_id": "analysis:other"}), approval.PaperProductionApprovalOutcome.CAUSALITY_MISMATCH))
    cases.append((replace(base, analysis={**base.analysis, "source_market_data_snapshot_id": ""}), approval.PaperProductionApprovalOutcome.MARKET_DATA_WATERMARK_MISMATCH))
    cases.append((replace(base, risk={**base.risk, "created_at_ms": AS_OF + 1}), approval.PaperProductionApprovalOutcome.FUTURE_DECISION))
    for value, expected in cases:
        result = service({"BTCUSDT": (value,)})[0].read(request())
        assert result.outcome is expected
        assert not result.candidates


def test_stale_approval_is_healthy_no_candidate():
    result = service({"BTCUSDT": (eligible_row(),)})[0].read(
        approval.PaperProductionApprovalRequest(request().scope, "stale", VALID + 1)
    )
    assert result.outcome is approval.PaperProductionApprovalOutcome.STALE_APPROVAL
    assert result.readiness is approval.PaperProductionApprovalReadiness.HEALTHY_NO_ELIGIBLE_APPROVAL


def test_latest_complete_result_supersedes_old_approval_and_partial_newest_is_ignored():
    approved = eligible_row()
    newer = replace(
        rebase(row(is_trade_signal=False), run_pk=2, run_id="run:2", closed_until_ms=CLOSED + 900_000),
        result_pk=2,
    )
    partial = replace(
        rebase(row(), run_pk=3, run_id="run:3", closed_until_ms=CLOSED + 1_800_000),
        result_pk=None, status="RUNNING",
    )
    result = service({"BTCUSDT": (partial, newer, approved)})[0].read(request())
    assert result.outcome is approval.PaperProductionApprovalOutcome.NO_TRADE_SIGNAL
    assert result.symbol_results[0].source_run_id == "run:2"


def test_equal_authoritative_rank_is_ambiguous_not_arbitrarily_selected():
    first = eligible_row()
    duplicate = replace(first, result_pk=2)
    result = service({"BTCUSDT": (first, duplicate)})[0].read(request())
    assert result.outcome is approval.PaperProductionApprovalOutcome.AMBIGUOUS_APPROVAL
    assert result.readiness is approval.PaperProductionApprovalReadiness.NOT_READY


def test_duplicate_final_approval_envelopes_are_ambiguous():
    base = eligible_row()
    chain = base.paper["persisted_final_approvals"]
    value = replace(base, paper={**base.paper, "persisted_final_approvals": [chain, chain]})
    result = service({"BTCUSDT": (value,)})[0].read(request())
    assert result.outcome is approval.PaperProductionApprovalOutcome.AMBIGUOUS_APPROVAL


def test_persisted_direction_disagreement_fails_closed():
    base = eligible_row()
    value = replace(base, risk={**base.risk, "direction_hint": "BEARISH"})
    result = service({"BTCUSDT": (value,)})[0].read(request())
    assert result.outcome is approval.PaperProductionApprovalOutcome.SIDE_MISMATCH


def test_consistent_snapshot_does_not_mix_concurrent_publication():
    original = row(is_trade_signal=False)
    reader = FakeReader({"BTCUSDT": (original,)})
    adapter, session = service({}, reader=reader)
    first = adapter.read(request())
    reader.rows["BTCUSDT"] = (eligible_row(),)
    adapter2, _ = service({}, reader=reader)
    second = adapter2.read(request())
    assert first.outcome is approval.PaperProductionApprovalOutcome.NO_TRADE_SIGNAL
    assert second.outcome is approval.PaperProductionApprovalOutcome.NO_TRADE_SIGNAL
    assert session.begin_count == 1


def test_read_only_guard_allows_only_select_and_exact_transaction_control():
    executor = approval._ReadOnlyExecutor(FakeSession())
    with pytest.raises(approval.ReadOnlyPolicyViolation):
        executor.execute(delete(OnlinePipelineRun))
    with pytest.raises(approval.ReadOnlyPolicyViolation):
        executor.execute(text("SELECT current_user"))
    assert executor.query_count == 0


@pytest.mark.parametrize("failure", [RuntimeError("db unavailable"), TimeoutError("timeout"), ValueError("mapping")])
def test_db_timeout_and_mapping_failures_are_safe_and_redacted(failure):
    reader = FakeReader(failure=failure)
    result = service({}, reader=reader)[0].read(request())
    assert result.outcome is approval.PaperProductionApprovalOutcome.SAFE_FAILURE
    assert not result.candidates
    rendered = str(result.safe_report()).lower()
    assert "traceback" not in rendered and "password" not in rendered and "database_url" not in rendered


def test_cancellation_before_acquisition_and_after_query_returns_no_partial_candidate():
    adapter, session = service({"BTCUSDT": (eligible_row(),)})
    result = adapter.read(request(), cancellation=Token())
    assert result.outcome is approval.PaperProductionApprovalOutcome.CANCELLED
    assert not result.candidates
    assert session.begin_count == 0


@pytest.mark.parametrize("symbols,changes,outcome", [
    (("DOGEUSDT",), {}, approval.PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT", "BTCUSDT"), {}, approval.PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED),
    (("BTCUSDT",), {"max_run_lookback": 9}, approval.PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED),
    (("BTCUSDT",), {"max_results_per_module": 9}, approval.PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED),
    (("BTCUSDT",), {"max_candidates": 4}, approval.PaperProductionApprovalOutcome.BOUNDED_LIMIT_EXCEEDED),
    (("BTCUSDT",), {"primary_timeframe": "1m"}, approval.PaperProductionApprovalOutcome.TARGET_NOT_ALLOWED),
])
def test_allowlist_and_bounds_are_fail_closed_before_database_read(symbols, changes, outcome):
    result = service({})[0].read(request(symbols, **changes))
    assert result.outcome is outcome
    assert result.query_count == 0


def test_safe_report_is_bounded_and_contains_no_payload_or_sql():
    result = service({"BTCUSDT": (eligible_row(),)})[0].read(request())
    report = result.safe_report()
    rendered = str(report).lower()
    assert report["candidate_count"] == 1
    assert report["symbols"][0]["lineage_valid"] is True
    for forbidden in ("payload_json", "approved_quantity", "select ", "password", "credential", "environment"):
        assert forbidden not in rendered


def test_revision_0008_uses_only_online_pipeline_tables_and_no_paper_graph():
    source = Path(approval.__file__).read_text(encoding="utf-8")
    assert OnlinePipelineRun.__tablename__ == "online_pipeline_runs"
    assert "OnlinePipelineResultRow" in source
    for forbidden in ("PaperExecutionCommand", "PaperOrder", "PaperFill", "PaperPosition"):
        assert forbidden not in source


def test_findings_cover_every_outcome_with_stable_unique_codes():
    assert set(approval._FINDING_BY_OUTCOME) == set(approval.PaperProductionApprovalOutcome)
    codes = [value.value for value in approval.PaperProductionApprovalFindingCode]
    assert len(codes) == len(set(codes))


def test_controlled_proof_harness_has_no_secret_or_mutation_arguments():
    source = Path("scripts/production_approval_adapter_proof.py").read_text(encoding="utf-8")
    assert "--benchmark" in source
    for forbidden in (
        "--database", "--password", "--env", "INSERT ", "UPDATE ", "DELETE ",
        "CommandIngestion", "Binance",
    ):
        assert forbidden not in source
