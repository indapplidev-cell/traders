from app.validation.gate_selector import GateSelector
from app.labels.label_quality_grid import LabelQualityGridPlanner
from app.experiments.ml38_2_fv3_tuning_matrix import ML382FV3TuningMatrix
import run_fv3_cached_tuning


def _gate(**overrides):
    payload = {
        "gate_type": "max_prob",
        "threshold": 0.5,
        "signal_count": 8,
        "profit_factor": 0.90,
        "total_r": -0.1,
        "expectancy_r": -0.01,
        "long_count": 8,
        "short_count": 0,
        "max_drawdown_r": 0.5,
    }
    payload.update(overrides)
    return payload


def test_ml38_10_24_gate_selector_reports_failure_reasons_when_no_gate_passes() -> None:
    selector = GateSelector()
    payload = selector.select([_gate()])
    assert payload["selected_gate"] is None
    assert payload["reject_reason"] == "no_validation_gate_passed"
    diagnostics = payload["diagnostics"]
    assert diagnostics["diagnostic_version"] == "ml38.10.24"
    assert diagnostics["diagnostic_status"] == "NO_GATE_PASSED"
    assert diagnostics["failure_reason_counts"]["signal_count_below_min"] == 1
    assert diagnostics["failure_reason_counts"]["profit_factor_below_min"] == 1
    assert diagnostics["failure_reason_counts"]["total_r_below_min"] == 1


def test_ml38_10_24_side_aware_relaxation_can_select_single_long_gate_research_only() -> None:
    selector = GateSelector()
    payload = selector.select(
        [
            _gate(
                signal_count=12,
                profit_factor=0.97,
                total_r=-0.05,
                expectancy_r=-0.005,
                long_count=12,
                short_count=0,
            )
        ],
        directional_side_filter_profile="long_only_research",
        allowed_signal_directions=("LONG",),
        side_aware_validation_relaxation_enabled=True,
        side_aware_min_validation_signal_count=10,
        side_aware_min_validation_profit_factor=0.95,
        side_aware_min_validation_total_r=-0.25,
        side_aware_min_validation_expectancy_r=-0.02,
        side_aware_allow_single_direction_validation=True,
    )
    assert payload["selected_gate"] is not None
    assert payload["selected_gate"]["side_aware_validation_relaxation_used"] is True
    diagnostics = payload["diagnostics"]
    assert diagnostics["selection_mode"] == "side_aware_research_relaxed"
    assert diagnostics["passed_gate_count"] == 1


def test_ml38_10_24_grid_matrix_and_runtime_include_lv29_research_configs() -> None:
    grid = LabelQualityGridPlanner().build_grid()
    configs_by_id = {item["config_id"]: item for item in grid["configs"]}
    assert grid["walk_forward_validation_gate_diagnostics_stage"] == "ML38.10.24"
    long_h12 = configs_by_id[
        "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax"
    ]
    assert long_h12["side_aware_validation_relaxation_enabled"] is True
    assert long_h12["side_aware_min_validation_signal_count"] == 10
    assert long_h12["side_aware_allow_single_direction_validation"] is True
    assert len(long_h12["label_version"]) <= 50

    matrix = ML382FV3TuningMatrix().build()
    assert matrix["walk_forward_validation_gate_diagnostics_stage"] == "ML38.10.24"
    assert (
        "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax"
        in matrix["config_ids"]
    )
    assert run_fv3_cached_tuning.FAST_DEBUG_CONFIGS[0].startswith("lv29_")
    assert run_fv3_cached_tuning.QUICK_QUALITY_CONFIGS[0].startswith("lv29_")
