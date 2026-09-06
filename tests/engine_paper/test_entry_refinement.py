from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.engine_market_data.candle import Candle
from app.engine_paper.entry_refinement import (
    CONFIRMED,
    EntryRefinementMode,
    EntryRefinementPolicy,
    EntryRefinementState,
    ScalpingEntryRefinementService,
    refinement_identity,
    refinement_window,
)
from app.engine_paper.production_market_data import PaperProductionMarketDataReadiness
from app.engine_paper.scalping_shadow import ShadowCostInputs


BOUNDARY = 1_800_000
SELECTED_MS = BOUNDARY + 10_000


def candidate(*, boundary=BOUNDARY, side="LONG", valid_until=BOUNDARY + 299_999):
    return SimpleNamespace(
        trade_profile_id="trade-5m-v2", symbol="BTCUSDT",
        side=SimpleNamespace(value=side), candidate_id=f"candidate:{boundary}",
        entry_reference_price=Decimal("100"), stop_price=Decimal("99"),
        target_price=Decimal("103"), valid_until_ms=valid_until,
        watermark=SimpleNamespace(closed_until_ms=boundary),
        lineage=SimpleNamespace(
            final_approval_id=f"approval:{boundary}", source_run_id=f"run:{boundary}"
        ),
    )


def candle(*, direction="BULLISH", open_ms=BOUNDARY):
    opening = Decimal("100")
    closing = Decimal("100.1") if direction == "BULLISH" else Decimal("99.9")
    return Candle(
        "BTCUSDT", "1m", open_ms, open_ms + 59_999,
        opening, Decimal("100.2"), Decimal("99.8"), closing, Decimal("1"),
        is_closed=True, source="test",
    )


class Market:
    def __init__(self, rows=(), *, ready=True):
        self.rows = tuple(rows)
        self.ready = ready

    def read(self, request):
        if not self.ready:
            return SimpleNamespace(
                readiness=PaperProductionMarketDataReadiness.NOT_READY, data=None
            )
        watermark = SimpleNamespace(watermark_id="watermark:1")
        snapshot = SimpleNamespace(
            snapshot_id="snapshot:1", watermark=watermark,
            candles=(("1m", self.rows),),
        )
        return SimpleNamespace(
            readiness=PaperProductionMarketDataReadiness.READY,
            data=SimpleNamespace(snapshots=(snapshot,)),
        )


class Costs:
    def __init__(self, *, bid=99.99, ask=100.01, spread=2.0, authoritative=True):
        self.bid, self.ask, self.spread, self.authoritative = bid, ask, spread, authoritative
        self.calls = []

    def load(self, symbol, entry, *, safety_margin_bps):
        self.calls.append((symbol, entry, safety_margin_bps))
        return ShadowCostInputs(
            entry_fee_bps=1, exit_fee_bps=1, entry_slippage_bps=1,
            exit_slippage_bps=1, safety_margin_bps=safety_margin_bps,
            spread_bps=self.spread, depth_impact_bps=1,
            commission_authoritative=self.authoritative,
            spread_authoritative=True, depth_authoritative=True,
            fee_source="BINANCE_ACCOUNT_COMMISSION_SNAPSHOT",
            bid=self.bid, ask=self.ask,
        )


def service(*, rows=(), costs=None, now_ms=BOUNDARY + 65_000,
            mode=EntryRefinementMode.SHADOW, ready=True):
    return ScalpingEntryRefinementService(
        market_data=Market(rows, ready=ready), cost_source=costs or Costs(),
        policy=EntryRefinementPolicy(10, 10, 1, 1.5, 1), mode=mode,
        clock=lambda: datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc),
    )


def selected_at():
    return datetime.fromtimestamp(SELECTED_MS / 1000, tz=timezone.utc)


def test_closed_1m_confirmation_is_ready_and_preserves_5m_identity_and_policy():
    source = candidate()
    before = (source.side.value, source.stop_price, source.target_price, source.candidate_id)
    costs = Costs()
    result = service(rows=(candle(),), costs=costs).evaluate(source, selected_at=selected_at())
    assert result.state == EntryRefinementState.READY_TO_ENTER.value
    assert result.reason == CONFIRMED
    assert result.one_min_candle_close_ms == BOUNDARY + 60_000
    assert result.refinement_valid_until_ms <= source.valid_until_ms
    assert result.executed_net_rr is not None and result.executed_net_rr >= 1.5
    assert result.executed_net_edge_bps is not None and result.executed_net_edge_bps >= 1
    assert costs.calls == [("BTCUSDT", 100.0, 1)]
    assert before == (source.side.value, source.stop_price, source.target_price, source.candidate_id)


def test_waits_for_closed_1m_and_expires_without_command_authority():
    waiting = service(rows=(), mode=EntryRefinementMode.AUTHORITATIVE).evaluate(
        candidate(), selected_at=selected_at()
    )
    assert waiting.state == "WAITING_FOR_1M"
    assert waiting.permits_command is False
    expired = service(rows=(), now_ms=BOUNDARY + 300_000).evaluate(
        candidate(), selected_at=selected_at()
    )
    assert expired.state == "EXPIRED"
    assert expired.reason == "ENTRY_REFINEMENT_WINDOW_EXPIRED"


def test_contradicting_micro_move_waits_but_cannot_flip_side():
    source = candidate(side="LONG")
    result = service(rows=(candle(direction="BEARISH"),)).evaluate(
        source, selected_at=selected_at()
    )
    assert result.state == "WAITING_FOR_1M"
    assert result.reason == "ENTRY_REFINEMENT_MOMENTUM_INVALIDATED"
    assert result.side == "LONG"


def test_later_closed_minute_can_confirm_after_an_earlier_contradiction():
    result = service(rows=(
        candle(direction="BEARISH"),
        candle(direction="BULLISH", open_ms=BOUNDARY + 60_000),
    ), now_ms=BOUNDARY + 125_000).evaluate(
        candidate(), selected_at=selected_at()
    )
    assert result.state == "CONFIRMED"
    assert result.one_min_candle_open_ms == BOUNDARY + 60_000


def test_price_drift_and_spread_reject_without_moving_stop_or_target():
    source = candidate()
    drift = service(rows=(candle(),), costs=Costs(bid=100.19, ask=100.21)).evaluate(
        source, selected_at=selected_at()
    )
    assert drift.state == "REJECTED"
    assert drift.reason == "ENTRY_REFINEMENT_PRICE_DRIFT_TOO_LARGE"
    spread = service(rows=(candle(),), costs=Costs(spread=11)).evaluate(
        source, selected_at=selected_at()
    )
    assert spread.reason == "ENTRY_REFINEMENT_SPREAD_TOO_WIDE"
    assert (source.stop_price, source.target_price) == (Decimal("99"), Decimal("103"))


def test_missing_authoritative_cost_or_stale_market_data_fails_exactly():
    missing_fee = service(rows=(candle(),), costs=Costs(authoritative=False)).evaluate(
        candidate(), selected_at=selected_at()
    )
    assert missing_fee.state == "FAILED"
    assert missing_fee.reason == "ENTRY_REFINEMENT_COST_DATA_UNAVAILABLE"
    stale = service(rows=(), ready=False).evaluate(candidate(), selected_at=selected_at())
    assert stale.reason == "ENTRY_REFINEMENT_MARKET_DATA_STALE"


def test_identity_is_boundary_scoped_and_shadow_never_grants_new_authority():
    first, second = candidate(), candidate(boundary=BOUNDARY + 300_000)
    assert refinement_identity(first) != refinement_identity(second)
    start, end = refinement_window(first, selected_at())
    assert start == SELECTED_MS and end == first.valid_until_ms
    rejected = service(rows=(candle(),), costs=Costs(spread=11)).evaluate(
        first, selected_at=selected_at()
    )
    assert rejected.permits_command is True
    assert rejected.profile_id == "trade-5m-v2"


def test_durable_plan_id_and_previous_close_context_are_preserved_for_whipsaw_analysis():
    source = candidate()
    result = service(rows=(candle(),)).evaluate(
        source,
        selected_at=selected_at(),
        plan_id="paper-plan:exact",
        previous_close={
            "time_since_previous_close_seconds": 42.5,
            "previous_exit_reason": "STOP_FILLED",
            "previous_side": "SHORT",
        },
    )
    assert result.plan_id == "paper-plan:exact"
    assert result.refinement_identity == refinement_identity(
        source, plan_id="paper-plan:exact"
    )
    assert result.time_since_previous_close_seconds == 42.5
    assert result.previous_exit_reason == "STOP_FILLED"
    assert result.same_symbol_reentry is True
    assert result.direction_flip is True
