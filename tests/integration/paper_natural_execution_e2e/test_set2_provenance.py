from datetime import datetime, timezone
from uuid import uuid4

from app.engine_orchestrator.orchestrator_models import OnlinePipelineRun, OnlinePipelineResultRow
from app.engine_orchestrator.pipeline_runner import PipelineRunner
from app.server_api.repositories.sqlalchemy_read import SqlAlchemyReadAdapter
from app.server_api.services.paper_reporting import PaperReadonlyReportingService
from tests.engine_orchestrator.test_parameter_set_cycle_binding import configuration
from tests.engine_orchestrator.test_parallel_trade_profiles import five_minute_config
from tests.engine_orchestrator_01_helpers import BOUNDARY, CandleRepo


def test_persisted_cycle_provenance_is_projected_without_global_rebind(natural_e2e_sessions):
    current = configuration("scalping-v2-set-2")
    pipeline = PipelineRunner(five_minute_config(), CandleRepo(), parameter_loader=lambda: current)
    cycle = pipeline.for_cycle(BOUNDARY)
    payload = cycle._profiled_payload({})
    run_id = "set2-provenance-" + uuid4().hex
    with natural_e2e_sessions() as session:
        session.add(OnlinePipelineRun(run_id=run_id, symbol="BTCUSDT", primary_timeframe="5m",
            trade_profile_id="trade-5m-v2", profile_mode="PRODUCTION_SEARCH", closed_until_ms=BOUNDARY,
            closed_until_utc=datetime.fromtimestamp(BOUNDARY / 1000, timezone.utc),
            status="COMPLETED", trigger_source="ISOLATED_TEST", daemon_instance_id="isolated-test"))
        session.flush()
        session.add(OnlinePipelineResultRow(run_id=run_id, symbol="BTCUSDT", primary_timeframe="5m",
            trade_profile_id="trade-5m-v2", profile_mode="PRODUCTION_SEARCH", closed_until_ms=BOUNDARY,
            paper_payload_json=payload))
        session.commit()
    current = configuration()
    assert pipeline.for_cycle(BOUNDARY + 300000).runtime_parameters.minimum_planned_rr == .4
    repository = SqlAlchemyReadAdapter(
        natural_e2e_sessions, primary_timeframe="5m", trade_profile_id="trade-5m-v2"
    )
    observed = repository.latest_scalping_parameter_snapshot()
    assert observed["parameter_set_id"] == "scalping-v2-set-2"
    assert observed["resolved_config_hash"] == cycle.runtime_parameters.resolved_config_hash
    for path, value in {"geometry.minimum_planned_rr": .6, "geometry.target_min_bps": 60,
                        "risk.risk_per_trade_bps": 5, "economics.min_ev_reserve_r": .05}.items():
        assert observed["parameters"][path]["value"] == value
        assert observed["parameters"][path]["source"] == "SET_2_OVERRIDE"
    assert cycle.paper_runner.geometry_config.production_rr_floor == .6
    assert cycle.paper_runner.geometry_config.minimum_ev_reserve_r == .05
