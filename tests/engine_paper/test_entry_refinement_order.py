from types import SimpleNamespace

from app.engine_paper.entry_refinement import (
    EntryRefinementMode, EntryRefinementPolicy, ScalpingEntryRefinementService,
    UPSTREAM_ADMISSION, configured_mode,
)


class NeverCalled:
    def read(self, _request):
        raise AssertionError("1m market data must not run before upstream admission")

    def load(self, *_args, **_kwargs):
        raise AssertionError("cost source must not run before upstream admission")


def candidate():
    return SimpleNamespace(
        trade_profile_id="trade-5m-v2", symbol="BTCUSDT", side=SimpleNamespace(value="LONG"),
        watermark=SimpleNamespace(closed_until_ms=1_000), candidate_id="candidate:1",
        lineage=SimpleNamespace(final_approval_id="approval:1", source_run_id="run:1"),
        valid_until_ms=301_000, entry_reference_price=100,
    )


def test_mode_is_server_configured_shadow_and_cannot_be_promoted_by_environment(monkeypatch):
    monkeypatch.setenv("TRADERS_SCALPING_1M_REFINEMENT_MODE", "AUTHORITATIVE")
    assert configured_mode() is EntryRefinementMode.SHADOW


def test_1m_cannot_run_or_rescue_failed_5m_economics():
    from datetime import datetime, timezone
    never = NeverCalled()
    service = ScalpingEntryRefinementService(
        market_data=never, cost_source=never,
        policy=EntryRefinementPolicy(10, 5, 1, .4, 0),
        clock=lambda: datetime.fromtimestamp(2, timezone.utc),
    )
    result = service.evaluate(
        candidate(), selected_at=datetime.fromtimestamp(1, timezone.utc),
        economics_admitted=False,
    )
    assert result.state == "REJECTED"
    assert result.reason == UPSTREAM_ADMISSION
    assert result.terminal
    assert not result.permits_command
