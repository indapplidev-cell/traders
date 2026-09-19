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
        self.statement = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, _statement):
        self.statement = _statement
        return tuple(self.rows)


def test_production_adapter_maps_only_persisted_rows_deterministically():
    rows = [SimpleNamespace(
        symbol="btcusdt", side="LONG", realized_pnl="1.25",
        setup_payload_json={"setup_type": "SCALP_BREAKOUT"},
        analysis_payload_json={"regime": "UP"},
        paper_payload_json={"paper_context": {"scalping_geometry_diagnostics": {
            "effective_total_cost_bps": 18,
        }}},
        entry_quantity="0.01", average_entry_price="10000",
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
    assert first.exact.average_win_net_bps == 125.0
    assert first.outcome_count == 1


def test_hierarchy_carries_observed_net_payoff_distribution():
    rows = (
        PaperOutcome("BTCUSDT", "SCALP_BREAKOUT", "BULLISH", "UP", "LOW", True,
                     net_return_bps=30.0),
        PaperOutcome("BTCUSDT", "SCALP_BREAKOUT", "BULLISH", "UP", "LOW", True,
                     net_return_bps=50.0),
        PaperOutcome("BTCUSDT", "SCALP_BREAKOUT", "BULLISH", "UP", "LOW", False,
                     net_return_bps=-20.0),
    )
    value = hierarchy_from_outcomes(
        rows, symbol="BTCUSDT", setup_type="SCALP_BREAKOUT",
        direction="BULLISH", regime="UP", cost_bucket="LOW",
    )
    assert value.exact.average_win_net_bps == 40.0
    assert value.exact.average_loss_net_bps == 20.0


def test_production_adapter_deduplicates_positions_and_reads_nested_policy_identity():
    payload = {
        "paper_plan_id": "plan-1",
        "paper_context": {
            "parameter_set_id": "scalping-v2-set-2",
            "resolved_config_hash": "hash-2",
            "admission_mode_at_entry": "PAPER_BOOTSTRAP",
            "scalping_geometry_diagnostics": {
                "effective_total_cost_bps": 22,
            },
        },
        "effective_configuration": {
            "config_epoch_id": "epoch-2",
            "source_commit": "commit-2",
        },
    }
    row = SimpleNamespace(
        position_id="position-1", command_id="command-1",
        symbol="dogeusdt", side="LONG", realized_pnl="0.5",
        setup_payload_json={"setup_type": "SCALP_MOMENTUM_CONTINUATION", "setup_id": "candidate-1"},
        analysis_payload_json={"regime": "UP"}, paper_payload_json=payload,
        entry_quantity="100", average_entry_price="0.1", closed_at=None,
    )
    source = PostgresPaperOutcomeStatisticsSource(lambda: _Session((row, row)))
    hierarchy = source.resolve(
        symbol="DOGEUSDT", setup_type="SCALP_MOMENTUM_CONTINUATION",
        direction="BULLISH", regime="UP", cost_bucket="MEDIUM",
        parameter_set_id="scalping-v2-set-2", resolved_config_hash="hash-2",
    )
    assert hierarchy.outcome_count == 1
    assert hierarchy.exact.samples == 1
    loaded = source._load()
    assert loaded[0].position_id == "position-1"
    assert loaded[0].admission_mode_at_entry == "PAPER_BOOTSTRAP"
    assert loaded[0].config_epoch_id == "epoch-2"
    assert loaded[0].source_commit == "commit-2"


def test_incompatible_config_and_parameter_set_never_form_authority():
    rows = (
        PaperOutcome(
            "DOGEUSDT", "SCALP_MOMENTUM_CONTINUATION", "BULLISH", "UP",
            "MEDIUM", True, parameter_set_id="scalping-v2-set-2",
            net_return_bps=10, resolved_config_hash="old-hash",
        ),
        PaperOutcome(
            "DOGEUSDT", "SCALP_MOMENTUM_CONTINUATION", "BULLISH", "UP",
            "MEDIUM", True, parameter_set_id="trade-5m-v1",
            net_return_bps=10, resolved_config_hash="current-hash",
        ),
    )
    hierarchy = hierarchy_from_outcomes(
        rows, symbol="DOGEUSDT", setup_type="SCALP_MOMENTUM_CONTINUATION",
        direction="BULLISH", regime="UP", cost_bucket="MEDIUM",
        parameter_set_id="scalping-v2-set-2", resolved_config_hash="current-hash",
    )
    assert hierarchy.outcome_count == 0
    assert hierarchy.parents[-1].samples == 0


def test_production_query_is_v2_closed_natural_and_symbol_correlated():
    session = _Session(())
    source = PostgresPaperOutcomeStatisticsSource(lambda: session)
    assert source._load() == ()
    compiled = session.statement.compile()
    sql = str(compiled)
    assert "online_pipeline_runs.trade_profile_id" in sql
    assert "online_pipeline_results.symbol = paper_positions.symbol" in sql
    assert "paper_positions.state" in sql
    assert "trade-5m-v2" in compiled.params.values()
