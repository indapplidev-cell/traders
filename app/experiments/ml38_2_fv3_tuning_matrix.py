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
