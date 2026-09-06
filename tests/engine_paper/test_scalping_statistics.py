from types import SimpleNamespace

from app.engine_paper.scalping_statistics import (
    PaperOutcome,
    PostgresPaperOutcomeStatisticsSource,
    hierarchy_from_outcomes,
)


def outcome(symbol="BTCUSDT", setup="SCALP_BREAKOUT", direction="BULLISH",
            regime="UP", cost="LOW", won=True):
    return PaperOutcome(symbol, setup, direction, regime, cost, won)


def test_hierarchy_falls_back_from_symbol_to_parent_then_global():
    rows = (
        outcome(won=True),
        outcome(symbol="ETHUSDT", won=False),
        outcome(symbol="SOLUSDT", direction="BEARISH", won=True),
    )
    value = hierarchy_from_outcomes(
        rows, symbol="ADAUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="LOW",
    )
    assert value.exact.samples == 0
    assert [bucket.level for bucket in value.parents] == [
        "setup_direction_regime", "setup_direction", "setup", "global",
    ]
    assert [bucket.samples for bucket in value.parents] == [2, 2, 3, 3]
    assert value.parents[-1].wins == 2


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, _statement):
        return tuple(self.rows)


def test_production_adapter_maps_only_persisted_rows_deterministically():
    rows = [SimpleNamespace(
        symbol="btcusdt", side="LONG", realized_pnl="1.25",
        setup_payload_json={"setup_type": "SCALP_BREAKOUT"},
        analysis_payload_json={"regime": "UP"},
        paper_payload_json={"paper_context": {"scalping_geometry_diagnostics": {
            "effective_total_cost_bps": 18,
        }}},
    )]
    source = PostgresPaperOutcomeStatisticsSource(lambda: _Session(rows))
    first = source.resolve(
        symbol="BTCUSDT", setup_type="SCALP_BREAKOUT", direction="BULLISH",
        regime="UP", cost_bucket="LOW",
    )
    second = source.resolve(
        symbol="BTCUSDT", setup_type="SCALP_BREAKOUT", direction="BULLISH",
        regime="UP", cost_bucket="LOW",
    )
    assert first == second
    assert first.exact.samples == first.exact.wins == 1
    assert first.outcome_count == 1
