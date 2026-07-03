from __future__ import annotations

from typing import Any

from app.labels.label_quality_grid import LabelQualityGridPlanner


ML38_5_ANTI_COLLAPSE_CONFIG_IDS = (
    "lv3_h04_thr02_tp08_sl08_ac",
    "lv3_h04_thr025_tp08_sl08_ac",
    "lv3_h06_thr025_tp10_sl08_ac",
    "lv3_h06_thr03_tp10_sl10_ac",
    "lv3_h08_thr025_tp10_sl08_ac",
    "lv3_h08_thr03_tp12_sl08_ac",
)

ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS = (
    "lv4_h06_thr035_tp12_sl08_cp",
    "lv4_h06_thr04_tp12_sl10_cp",
    "lv4_h08_thr035_tp12_sl08_cp",
    "lv4_h08_thr04_tp15_sl10_cp",
    "lv4_h12_thr04_tp12_sl08_cp",
    "lv4_h12_thr05_tp15_sl10_cp",
)

ML38_9_FLAT_BIAS_CONFIG_IDS = (
    "lv5_h06_thr045_tp10_sl10_fb",
    "lv5_h08_thr05_tp10_sl10_fb",
    "lv5_h12_thr055_tp12_sl12_fb",
    "lv5_h16_thr06_tp15_sl15_fb",
)

ML38_9_1_BIAS_AWARE_CONFIG_IDS = (
    "lv6_h08_thr052_tp10_sl10_ba",
    "lv6_h10_thr055_tp10_sl10_ba",
    "lv6_h12_thr06_tp12_sl12_ba",
    "lv6_h16_thr065_tp15_sl15_ba",
)

ML38_9_2_BASELINE_EDGE_CONFIG_IDS = (
    "lv7_h08_thr052_tp10_sl10_be",
    "lv7_h10_thr055_tp10_sl10_be",
    "lv7_h12_thr06_tp12_sl12_be",
)

ML38_9_3_CALIBRATED_DECISION_CONFIG_IDS = (
    "lv8_h10_thr055_tp10_sl10_cd",
    "lv8_h12_thr06_tp12_sl12_cd",
    "lv8_h16_thr065_tp15_sl15_cd",
)

ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS = (
    "lv9_h08_thr052_tp10_sl10_bc",
    "lv9_h12_thr06_tp12_sl12_bc",
    "lv9_h16_thr065_tp15_sl15_bc",
)

ML38_9_5_DECISION_POLICY_CONFIG_IDS = (
    "lv10_h08_thr052_tp10_sl10_dp",
    "lv10_h12_thr06_tp12_sl12_dp",
    "lv10_h16_thr065_tp15_sl15_dp",
)

ML38_9_8_BOOK_SETUP_CONTEXT_CONFIG_IDS = (
    "lv11_h08_thr052_tp10_sl10_fv4",
    "lv11_h12_thr06_tp12_sl12_fv4",
    "lv11_h16_thr065_tp15_sl15_fv4",
)

ML38_9_9_LABEL_MODE_CONFIG_IDS = (
    "lv12_h08_ft_tp10_sl10",
    "lv12_h12_ft_tp12_sl12",
    "lv12_h16_ft_tp15_sl15",
    "lv12_h12_setup_ft_tp12_sl12",
)

ML38_10_1_OPPORTUNITY_CONFIG_IDS = (
    "lv13_h08_opportunity_ft",
    "lv13_h12_opportunity_ft",
    "lv13_h16_opportunity_ft",
)

ML38_10_3_CLASS_MARGIN_CONFIG_IDS = (
    "lv14_h08_cm_setup",
    "lv14_h12_cm_setup",
    "lv14_h16_cm_setup",
)

ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS = (
    "lv15_h08_setup_pure_ft",
    "lv15_h12_setup_pure_ft",
    "lv15_h16_setup_pure_ft",
)

ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS = (
    "lv16_h08_trade_two_stage",
    "lv16_h12_trade_two_stage",
    "lv16_h16_trade_two_stage",
)

ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS = (
    "lv17_h08_tts_thr060",
    "lv17_h08_tts_thr065",
    "lv17_h12_tts_thr065",
)
ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS = (
    "lv18_h08_tts_thr065_sq060",
    "lv18_h12_tts_thr065_sq060",
    "lv18_h12_tts_thr070_sq065",
)
ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS = (
    "lv19_h08_tts_thr065_sqmask060",
    "lv19_h12_tts_thr065_sqmask060",
    "lv19_h12_tts_thr070_sqmask065",
)

ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS = (
    "lv20_h08_tts_thr065_sqmask060_trap",
    "lv20_h12_tts_thr065_sqmask060_trap",
    "lv20_h12_tts_thr070_sqmask065_trap",
)

ML38_10_14_ENTRY_PATH_QUALITY_CONFIG_IDS = (
    "lv21_h08_tts_thr065_sqmask060_epq065",
    "lv21_h12_tts_thr065_sqmask060_epq065",
    "lv21_h12_tts_thr065_sqmask060_epq070",
)

ML38_10_14_1_ENTRY_PATH_STOP_PRESSURE_CONFIG_IDS = (
    "lv22_h08_tts_thr065_sqmask060_epq070_sp045",
    "lv22_h12_tts_thr065_sqmask060_epq070_sp045",
    "lv22_h12_tts_thr065_sqmask060_epq075_sp040",
)

ML38_10_15_ENTRY_EFFECTIVENESS_CONFIG_IDS = (
    "lv23_h08_tts_thr065_sqmask060_epq065_sp050_eff",
    "lv23_h12_tts_thr065_sqmask060_epq065_sp050_eff",
    "lv23_h12_tts_thr065_sqmask060_epq068_sp047_eff",
)

ML38_10_16_MAE_AWARE_ENTRY_EXIT_CONFIG_IDS = (
    "lv24_h08_tts_thr065_sqmask060_epq068_sp047_mae",
    "lv24_h12_tts_thr065_sqmask060_epq068_sp047_mae",
    "lv24_h12_tts_thr065_sqmask060_epq070_sp045_mae_rr",
)

ML38_10_17_EXIT_OUTCOME_STOP_LOSS_MITIGATION_CONFIG_IDS = (
    "lv25_h08_tts_thr065_sqmask060_epq070_sp045_exit_mit",
    "lv25_h12_tts_thr065_sqmask060_epq070_sp045_exit_mit",
    "lv25_h12_tts_thr065_sqmask060_epq072_sp043_exit_mit_strict",
)

ML38_10_18_EXIT_MITIGATION_PATH_AUDIT_CONFIG_IDS = (
    "lv26_h08_tts_thr065_sqmask060_epq070_sp045_recovery_guard",
    "lv26_h12_tts_thr065_sqmask060_epq070_sp045_recovery_guard",
    "lv26_h12_tts_thr065_sqmask060_epq072_sp043_recovery_guard_strict",
)

ML38_10_19_DIRECTIONAL_EDGE_BIAS_HARDENING_CONFIG_IDS = (
    "lv27_h08_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias",
    "lv27_h12_tts_thr065_sqmask060_epq070_sp045_rguard_dirbias",
    "lv27_h12_tts_thr065_sqmask060_epq072_sp043_rguard_dirbias_strict",
)

ML38_10_20_DIRECTIONAL_SIDE_ABLATION_CONFIG_IDS = (
    "lv28_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_only",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_only",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_short_only",
    "lv28_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short",
)

ML38_10_24_WALK_FORWARD_VALIDATION_GATE_DIAGNOSTICS_CONFIG_IDS = (
    "lv29_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
    "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_relax",
    "lv29_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_wf_relax",
)

ML38_10_25_WALK_FORWARD_TOTAL_R_FAILURE_REPAIR_CONFIG_IDS = (
    "lv30_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
    "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_wf_totalr_probe",
    "lv30_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_wf_totalr_probe",
)

ML38_10_27_FOLD_TIME_SLICE_EXIT_REPAIR_CONFIG_IDS = (
    "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
    "lv31_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit45_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_exit75_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_bad_dates_probe",
    "lv31_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_bad_dates_exit45_probe",
)
ML38_10_28_FEATURE_REGIME_FOLD_REPAIR_CONFIG_IDS = (
    "lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe",
    "lv32_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
    "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_probe",
    "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_feature_guard_exit45_probe",
    "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_feature_guard_probe",
    "lv32_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_strict_feature_guard_exit45_probe",
)
ML38_10_29_ADAPTIVE_FEATURE_REGIME_REPAIR_CONFIG_IDS = (
    "lv33_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_probe",
    "lv33_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_adaptive_feature_guard_exit45_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_adaptive_feature_guard_probe",
    "lv33_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_adaptive_feature_guard_exit45_probe",
)
ML38_10_31_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS = (
    "lv34_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe",
    "lv34_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
    "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_probe",
    "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_cond_regime_exit45_probe",
    "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_cond_regime_probe",
    "lv34_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_cond_regime_exit45_probe",
)
ML38_10_33_TARGETED_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS = (
    "lv35_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe",
    "lv35_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_exit45_probe",
    "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_probe",
    "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_targeted_cond_regime_exit45_probe",
    "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_targeted_cond_regime_probe",
    "lv35_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_targeted_cond_regime_exit45_probe",
)
ML38_10_35_METRIC_RELAXATION_PROBE_CONFIG_IDS = (
    "lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe",
    "lv36_h08_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe",
    "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_probe",
    "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_long_metric_relax_exit45_probe",
    "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_probe",
    "lv36_h12_tts_thr065_sqmask060_epq070_sp045_rguard_suppress_short_metric_relax_exit45_probe",
)

ML38_2_FV3_TUNING_CONFIG_IDS = (
    "lv2_h08_thr03_tp10_sl10",
    "lv2_h08_thr04_tp10_sl10",
    "lv2_h08_thr05_tp15_sl10",
    "lv2_h12_thr03_tp10_sl10",
    "lv2_h12_thr04_tp15_sl10",
    "lv2_h12_thr05_tp15_sl10",
    "lv2_h16_thr04_tp15_sl10",
    "lv2_h16_thr05_tp20_sl10",
    *ML38_5_ANTI_COLLAPSE_CONFIG_IDS,
    *ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS,
    *ML38_9_FLAT_BIAS_CONFIG_IDS,
    *ML38_9_1_BIAS_AWARE_CONFIG_IDS,
    *ML38_9_2_BASELINE_EDGE_CONFIG_IDS,
    *ML38_9_3_CALIBRATED_DECISION_CONFIG_IDS,
    *ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS,
    *ML38_9_5_DECISION_POLICY_CONFIG_IDS,
    *ML38_9_8_BOOK_SETUP_CONTEXT_CONFIG_IDS,
    *ML38_9_9_LABEL_MODE_CONFIG_IDS,
    *ML38_10_1_OPPORTUNITY_CONFIG_IDS,
    *ML38_10_3_CLASS_MARGIN_CONFIG_IDS,
    *ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS,
    *ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS,
    *ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS,
    *ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS,
    *ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS,
    *ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS,
    *ML38_10_14_ENTRY_PATH_QUALITY_CONFIG_IDS,
    *ML38_10_14_1_ENTRY_PATH_STOP_PRESSURE_CONFIG_IDS,
    *ML38_10_15_ENTRY_EFFECTIVENESS_CONFIG_IDS,
    *ML38_10_16_MAE_AWARE_ENTRY_EXIT_CONFIG_IDS,
    *ML38_10_17_EXIT_OUTCOME_STOP_LOSS_MITIGATION_CONFIG_IDS,
    *ML38_10_18_EXIT_MITIGATION_PATH_AUDIT_CONFIG_IDS,
    *ML38_10_19_DIRECTIONAL_EDGE_BIAS_HARDENING_CONFIG_IDS,
    *ML38_10_20_DIRECTIONAL_SIDE_ABLATION_CONFIG_IDS,
    *ML38_10_24_WALK_FORWARD_VALIDATION_GATE_DIAGNOSTICS_CONFIG_IDS,
    *ML38_10_25_WALK_FORWARD_TOTAL_R_FAILURE_REPAIR_CONFIG_IDS,
    *ML38_10_27_FOLD_TIME_SLICE_EXIT_REPAIR_CONFIG_IDS,
    *ML38_10_28_FEATURE_REGIME_FOLD_REPAIR_CONFIG_IDS,
    *ML38_10_29_ADAPTIVE_FEATURE_REGIME_REPAIR_CONFIG_IDS,
    *ML38_10_31_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS,
    *ML38_10_33_TARGETED_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS,
    *ML38_10_35_METRIC_RELAXATION_PROBE_CONFIG_IDS,
)
ML38_2_REQUIRED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
ML38_2_FEATURE_VERSION = "fv4_book_setup_context"


class ML382FV3TuningMatrix:
    def build(self) -> dict[str, Any]:
        available = {
            item["config_id"]: dict(item)
            for item in LabelQualityGridPlanner().build_grid()["configs"]
        }
        configs = []
        missing = []
        for config_id in ML38_2_FV3_TUNING_CONFIG_IDS:
            payload = available.get(config_id)
            if payload is None:
                missing.append(config_id)
                continue
            config_payload = dict(payload)
            config_payload["feature_version"] = ML38_2_FEATURE_VERSION
            configs.append(config_payload)
        return {
            "stage": "ML38.2",
            "anti_collapse_stage": "ML38.5",
            "confidence_profitability_stage": "ML38.6",
            "feature_version": ML38_2_FEATURE_VERSION,
            "anti_collapse_config_ids": list(ML38_5_ANTI_COLLAPSE_CONFIG_IDS),
            "anti_collapse_config_count": len(ML38_5_ANTI_COLLAPSE_CONFIG_IDS),
            "confidence_profit_config_ids": list(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS),
            "flat_bias_stage": "ML38.9",
            "flat_bias_config_ids": list(ML38_9_FLAT_BIAS_CONFIG_IDS),
            "flat_bias_config_count": len(ML38_9_FLAT_BIAS_CONFIG_IDS),
            "bias_aware_stage": "ML38.9.1",
            "bias_aware_config_ids": list(ML38_9_1_BIAS_AWARE_CONFIG_IDS),
            "bias_aware_config_count": len(ML38_9_1_BIAS_AWARE_CONFIG_IDS),
            "baseline_edge_stage": "ML38.9.2",
            "baseline_edge_config_ids": list(ML38_9_2_BASELINE_EDGE_CONFIG_IDS),
            "baseline_edge_config_count": len(ML38_9_2_BASELINE_EDGE_CONFIG_IDS),
            "calibrated_decision_stage": "ML38.9.3",
            "calibrated_decision_config_ids": list(ML38_9_3_CALIBRATED_DECISION_CONFIG_IDS),
            "calibrated_decision_config_count": len(ML38_9_3_CALIBRATED_DECISION_CONFIG_IDS),
            "bounded_calibration_stage": "ML38.9.4",
            "bounded_calibration_config_ids": list(ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS),
            "bounded_calibration_config_count": len(ML38_9_4_BOUNDED_CALIBRATION_CONFIG_IDS),
            "decision_policy_grid_stage": "ML38.9.5",
            "decision_policy_config_ids": list(ML38_9_5_DECISION_POLICY_CONFIG_IDS),
            "decision_policy_config_count": len(ML38_9_5_DECISION_POLICY_CONFIG_IDS),
            "book_setup_context_stage": "ML38.9.8",
            "book_setup_context_config_ids": list(ML38_9_8_BOOK_SETUP_CONTEXT_CONFIG_IDS),
            "book_setup_context_config_count": len(ML38_9_8_BOOK_SETUP_CONTEXT_CONFIG_IDS),
            "label_mode_stage": "ML38.9.9",
            "label_mode_config_ids": list(ML38_9_9_LABEL_MODE_CONFIG_IDS),
            "label_mode_config_count": len(ML38_9_9_LABEL_MODE_CONFIG_IDS),
            "opportunity_first_stage": "ML38.10.1",
            "opportunity_first_config_ids": list(ML38_10_1_OPPORTUNITY_CONFIG_IDS),
            "opportunity_first_config_count": len(ML38_10_1_OPPORTUNITY_CONFIG_IDS),
            "class_margin_stage": "ML38.10.3",
            "class_margin_config_ids": list(ML38_10_3_CLASS_MARGIN_CONFIG_IDS),
            "class_margin_config_count": len(ML38_10_3_CLASS_MARGIN_CONFIG_IDS),
            "setup_semantics_stage": "ML38.10.4",
            "setup_semantics_config_ids": list(ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS),
            "setup_semantics_config_count": len(ML38_10_4_SETUP_SEMANTICS_CONFIG_IDS),
            "trade_two_stage_stage": "ML38.10.5",
            "trade_two_stage_config_ids": list(ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS),
            "trade_two_stage_config_count": len(ML38_10_5_TRADE_TWO_STAGE_CONFIG_IDS),
            "two_stage_threshold_stage": "ML38.10.6",
            "two_stage_threshold_config_ids": list(ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS),
            "two_stage_threshold_config_count": len(ML38_10_6_TWO_STAGE_THRESHOLD_CONFIG_IDS),
            "setup_quality_filter_stage": "ML38.10.7",
            "setup_quality_filter_config_ids": list(ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS),
            "setup_quality_filter_config_count": len(ML38_10_7_SETUP_QUALITY_FILTER_CONFIG_IDS),
            "setup_quality_decision_mask_stage": "ML38.10.8",
            "setup_quality_decision_mask_config_ids": list(ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS),
            "setup_quality_decision_mask_config_count": len(ML38_10_8_SETUP_QUALITY_DECISION_MASK_CONFIG_IDS),
            "false_breakout_trap_stage": "ML38.10.10",
            "false_breakout_trap_config_ids": list(ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS),
            "false_breakout_trap_config_count": len(ML38_10_10_FALSE_BREAKOUT_TRAP_CONFIG_IDS),
            "entry_path_quality_stage": "ML38.10.14",
            "entry_path_quality_config_ids": list(ML38_10_14_ENTRY_PATH_QUALITY_CONFIG_IDS),
            "entry_path_quality_config_count": len(ML38_10_14_ENTRY_PATH_QUALITY_CONFIG_IDS),
            "entry_path_stop_pressure_stage": "ML38.10.14.1",
            "entry_path_stop_pressure_config_ids": list(ML38_10_14_1_ENTRY_PATH_STOP_PRESSURE_CONFIG_IDS),
            "entry_path_stop_pressure_config_count": len(ML38_10_14_1_ENTRY_PATH_STOP_PRESSURE_CONFIG_IDS),
            "entry_path_effectiveness_tuning_stage": "ML38.10.15",
            "entry_path_effectiveness_tuning_config_ids": list(ML38_10_15_ENTRY_EFFECTIVENESS_CONFIG_IDS),
            "entry_path_effectiveness_tuning_config_count": len(ML38_10_15_ENTRY_EFFECTIVENESS_CONFIG_IDS),
            "mae_aware_entry_exit_tuning_stage": "ML38.10.16",
            "mae_aware_entry_exit_tuning_config_ids": list(ML38_10_16_MAE_AWARE_ENTRY_EXIT_CONFIG_IDS),
            "mae_aware_entry_exit_tuning_config_count": len(ML38_10_16_MAE_AWARE_ENTRY_EXIT_CONFIG_IDS),
            "exit_outcome_stop_loss_mitigation_stage": "ML38.10.17",
            "exit_outcome_stop_loss_mitigation_config_ids": list(ML38_10_17_EXIT_OUTCOME_STOP_LOSS_MITIGATION_CONFIG_IDS),
            "exit_outcome_stop_loss_mitigation_config_count": len(ML38_10_17_EXIT_OUTCOME_STOP_LOSS_MITIGATION_CONFIG_IDS),
            "exit_mitigation_path_audit_stage": "ML38.10.18",
            "exit_mitigation_path_audit_config_ids": list(ML38_10_18_EXIT_MITIGATION_PATH_AUDIT_CONFIG_IDS),
            "exit_mitigation_path_audit_config_count": len(ML38_10_18_EXIT_MITIGATION_PATH_AUDIT_CONFIG_IDS),
            "directional_edge_bias_hardening_stage": "ML38.10.19",
            "directional_edge_bias_hardening_config_ids": list(ML38_10_19_DIRECTIONAL_EDGE_BIAS_HARDENING_CONFIG_IDS),
            "directional_edge_bias_hardening_config_count": len(ML38_10_19_DIRECTIONAL_EDGE_BIAS_HARDENING_CONFIG_IDS),
            "directional_side_ablation_stage": "ML38.10.20",
            "directional_side_ablation_config_ids": list(ML38_10_20_DIRECTIONAL_SIDE_ABLATION_CONFIG_IDS),
            "directional_side_ablation_config_count": len(ML38_10_20_DIRECTIONAL_SIDE_ABLATION_CONFIG_IDS),
            "walk_forward_validation_gate_diagnostics_stage": "ML38.10.24",
            "walk_forward_validation_gate_diagnostics_config_ids": list(
                ML38_10_24_WALK_FORWARD_VALIDATION_GATE_DIAGNOSTICS_CONFIG_IDS
            ),
            "walk_forward_validation_gate_diagnostics_config_count": len(
                ML38_10_24_WALK_FORWARD_VALIDATION_GATE_DIAGNOSTICS_CONFIG_IDS
            ),
            "walk_forward_total_r_failure_repair_stage": "ML38.10.25",
            "walk_forward_total_r_failure_repair_config_ids": list(
                ML38_10_25_WALK_FORWARD_TOTAL_R_FAILURE_REPAIR_CONFIG_IDS
            ),
            "walk_forward_total_r_failure_repair_config_count": len(
                ML38_10_25_WALK_FORWARD_TOTAL_R_FAILURE_REPAIR_CONFIG_IDS
            ),
            "fold_time_slice_exit_repair_probe_stage": "ML38.10.27",
            "fold_time_slice_exit_repair_probe_config_ids": list(
                ML38_10_27_FOLD_TIME_SLICE_EXIT_REPAIR_CONFIG_IDS
            ),
            "fold_time_slice_exit_repair_probe_config_count": len(
                ML38_10_27_FOLD_TIME_SLICE_EXIT_REPAIR_CONFIG_IDS
            ),
            "feature_regime_fold_repair_stage": "ML38.10.28",
            "feature_regime_fold_repair_config_ids": list(
                ML38_10_28_FEATURE_REGIME_FOLD_REPAIR_CONFIG_IDS
            ),
            "feature_regime_fold_repair_config_count": len(
                ML38_10_28_FEATURE_REGIME_FOLD_REPAIR_CONFIG_IDS
            ),
            "ml38_10_29_adaptive_feature_regime_repair_config_ids": list(
                ML38_10_29_ADAPTIVE_FEATURE_REGIME_REPAIR_CONFIG_IDS
            ),
            "ml38_10_31_conditional_regime_repair_config_ids": list(
                ML38_10_31_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS
            ),
            "ml38_10_33_targeted_conditional_regime_repair_config_ids": list(
                ML38_10_33_TARGETED_CONDITIONAL_REGIME_REPAIR_CONFIG_IDS
            ),
            "targeted_conditional_regime_repair_stage": "ML38.10.33",
            "confidence_profit_config_count": len(ML38_6_CONFIDENCE_PROFIT_CONFIG_IDS),
            "config_count": len(configs),
            "configs": configs,
            "config_ids": [item["config_id"] for item in configs],
            "required_symbols": list(ML38_2_REQUIRED_SYMBOLS),
            "missing_configs": missing,
            "safety": {
                "traders_core_integration": False,
                "live_trading": False,
                "orders_trades": False,
                "model_auto_activation": False,
            },
        }
