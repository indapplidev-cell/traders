from __future__ import annotations

import hashlib
import inspect
import json

from scripts import engine_trend_27_multi_setup_portfolio_discovery as audit


def test_contract_closes_short_v2_and_keeps_runtime_off():
    contract = audit.locked_contract()
    assert contract["short_v2_status"] == "RESEARCH_ONLY_FAILED_FORWARD_CONTRACT_CLOSED"
    assert contract["paper_enabled"] is False
    assert contract["runtime_changed"] is False
    assert contract["old_scores_loaded"] is False
    assert tuple(contract["families"]) == audit.FAMILIES
    assert contract["minimum_gate_per_family"]["clean_trades_min"] == 30
    assert contract["minimum_gate_per_family"]["profit_factor_min"] == 1.05


def test_window_is_disjoint_from_prior_candidate_and_forward_windows():
    assert audit.LAST_CONFIRMATION < audit.datetime(2025, 7, 3, tzinfo=audit.timezone.utc)
    assert audit.LAST_CONFIRMATION < audit.datetime(2025, 12, 18, tzinfo=audit.timezone.utc)


def test_generation_does_not_read_outcomes_or_old_scores():
    source = "\n".join(inspect.getsource(fn) for fn in (
        audit.detect_short_continuation, audit.detect_failed_rebound,
        audit.detect_range_rejection, audit.detect_trap_reversal,
        audit.detect_momentum_pullback, audit.scan_symbol,
    ))
    for forbidden in ("label_plan", "net_return_pct", "net_r", "TP_BEFORE_SL", "SL_BEFORE_TP", "score"):
        assert forbidden not in source


def test_gate_enforces_every_required_dimension():
    metrics = {"clean_trades": 30, "profit_factor_net_r": 1.05, "expectancy_net_r": 0.01,
               "max_drawdown_pct_fixed_1pct_risk": 14.99, "largest_winner_share_of_gross_profit": 0.49}
    rows = []
    # Empty symbol partitions prevent a pass even when aggregate numbers look acceptable.
    gate = audit.family_gate(rows, metrics)
    assert gate["pass"] is False
    assert gate["checks"]["positive_symbols_gte_2"] is False


def test_freeze_payload_has_no_outcomes_and_run_orders_freeze_before_labels():
    plan = {"candidate_id": "", "family": audit.FAMILIES[0], "symbol": "BTCUSDT",
            "confirmation_time": "2025-01-04T00:00:00Z", "fill_index_internal": 240}
    _, digest, payload = audit.freeze_plans([plan])
    assert hashlib.sha256(payload).hexdigest() == digest
    public = json.loads(payload)["plans"]
    assert "fill_index_internal" not in public[0]
    assert "label" not in public[0] and "net_r" not in public[0]
    source = inspect.getsource(audit.run)
    assert source.index("freeze_plans(plans)") < source.index("label_plan(plan")
