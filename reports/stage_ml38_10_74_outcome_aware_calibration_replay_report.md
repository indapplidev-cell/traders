# ML38.10.74 — Outcome-aware calibration replay

## Final decision
- decision: OUTCOME_AWARE_CALIBRATION_REPLAY_COMPLETED_NO_POLICY_BEATS_BASELINE
- recommendation: NO_CALIBRATION_POLICY_BEATS_BASELINE
- next_allowed_stage: ML38.10.75 — class-prior class-balance diagnostic
- production_policy_allowed_now: false
- cascade/outcome blocked: true
- production-like recompute/tradable edge not claimed: true

## Evidence
- output_dir: `D:\disk_E\game_projects\traders\traders-ml\reports\feature_regime_experiments\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260708_153049`
- streams_scanned: 45
- summaries_scanned: 45
- schemas_scanned: 45
- rows_scanned: 291645
- ML38.10.73 was already executed before this diagnostic; ML38.10.74 did not rerun wrapper or training.

## Field contract validation
- field_contract_status: PASSED
- contract_version: ml38.10.69
- actual_label: available
- raw probabilities: available
- calibrated probabilities: available
- row_alignment_key: available and unique per stream
- prediction_layers: present
- LF-only and summary hash/size validation: passed

## Actual label distribution — test split
- DOWN: 31
- FLAT: 899
- UP: 43
- total: 973

## Best replay policy
- policy_name: directional_confidence_floor
- parameters: `{"threshold": 0.6}`
- avg_accuracy: 0.485098
- avg_accuracy_edge: -0.438849
- avg_flat_recall: 0.443826
- avg_directional_recall: 0.986486
- avg_false_directional_on_actual_flat: 500.000000
- best_candidate_predicted_distribution: `{"DOWN": 281, "FLAT": 400, "UP": 292}`

## Raw vs calibrated comparison
```json
{
  "accuracy_delta_calibrated_minus_raw": 0.0,
  "calibrated_argmax": {
    "avg_accuracy": 0.09146968139773905,
    "avg_accuracy_edge": -0.8324768756423427,
    "avg_directional_recall": 1.0,
    "avg_false_directional_on_actual_flat": 884.0,
    "avg_false_flat_on_actual_directional": 0.0,
    "avg_flat_recall": 0.01668520578420466,
    "best_candidate_accuracy": 0.09146968139773895,
    "best_candidate_accuracy_edge": -0.8324768756423433,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 31,
        "FLAT": 0,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 501,
        "FLAT": 15,
        "UP": 383
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 1.0,
    "best_candidate_false_directional_on_actual_flat": 884,
    "best_candidate_flat_recall": 0.01668520578420467,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 532,
      "FLAT": 15,
      "UP": 426
    },
    "candidate_count": 45,
    "parameters": {},
    "policy_name": "calibrated_argmax"
  },
  "directional_recall_delta_calibrated_minus_raw": 0.0,
  "false_directional_delta_calibrated_minus_raw": 0.0,
  "flat_recall_delta_calibrated_minus_raw": 0.0,
  "raw_argmax": {
    "avg_accuracy": 0.09146968139773905,
    "avg_accuracy_edge": -0.8324768756423427,
    "avg_directional_recall": 1.0,
    "avg_false_directional_on_actual_flat": 884.0,
    "avg_false_flat_on_actual_directional": 0.0,
    "avg_flat_recall": 0.01668520578420466,
    "best_candidate_accuracy": 0.09146968139773895,
    "best_candidate_accuracy_edge": -0.8324768756423433,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 31,
        "FLAT": 0,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 501,
        "FLAT": 15,
        "UP": 383
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 1.0,
    "best_candidate_false_directional_on_actual_flat": 884,
    "best_candidate_flat_recall": 0.01668520578420467,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 532,
      "FLAT": 15,
      "UP": 426
    },
    "candidate_count": 45,
    "parameters": {},
    "policy_name": "raw_argmax"
  }
}
```

## Policy grid summary
- policies_tested: 20
- candidate_policy_pairs_ranked: 900
- any_policy_positive_accuracy_edge: False
- any_policy_beats_majority_baseline: False
- probability_sequences_identical_across_candidates: True

## Best replay policies
```json
[
  {
    "avg_accuracy": 0.48509763617677254,
    "avg_accuracy_edge": -0.4388489208633096,
    "avg_directional_recall": 0.9864864864864862,
    "avg_false_directional_on_actual_flat": 500.0,
    "avg_false_flat_on_actual_directional": 1.0,
    "avg_flat_recall": 0.4438264738598438,
    "best_candidate_accuracy": 0.4850976361767729,
    "best_candidate_accuracy_edge": -0.43884892086330934,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 30,
        "FLAT": 1,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 251,
        "FLAT": 399,
        "UP": 249
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 0.9864864864864865,
    "best_candidate_false_directional_on_actual_flat": 500,
    "best_candidate_flat_recall": 0.44382647385984425,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 281,
      "FLAT": 400,
      "UP": 292
    },
    "candidate_count": 45,
    "parameters": {
      "threshold": 0.6
    },
    "policy_name": "directional_confidence_floor"
  },
  {
    "avg_accuracy": 0.40698869475847876,
    "avg_accuracy_edge": -0.5169578622816037,
    "avg_directional_recall": 0.9864864864864862,
    "avg_false_directional_on_actual_flat": 576.0,
    "avg_false_flat_on_actual_directional": 1.0,
    "avg_flat_recall": 0.35928809788654076,
    "best_candidate_accuracy": 0.40698869475847893,
    "best_candidate_accuracy_edge": -0.5169578622816033,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 30,
        "FLAT": 1,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 302,
        "FLAT": 323,
        "UP": 274
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 0.9864864864864865,
    "best_candidate_false_directional_on_actual_flat": 576,
    "best_candidate_flat_recall": 0.3592880978865406,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 332,
      "FLAT": 324,
      "UP": 317
    },
    "candidate_count": 45,
    "parameters": {
      "threshold": 0.55
    },
    "policy_name": "directional_confidence_floor"
  },
  {
    "avg_accuracy": 0.40698869475847876,
    "avg_accuracy_edge": -0.5169578622816037,
    "avg_directional_recall": 0.9864864864864862,
    "avg_false_directional_on_actual_flat": 576.0,
    "avg_false_flat_on_actual_directional": 1.0,
    "avg_flat_recall": 0.35928809788654076,
    "best_candidate_accuracy": 0.40698869475847893,
    "best_candidate_accuracy_edge": -0.5169578622816033,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 30,
        "FLAT": 1,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 302,
        "FLAT": 323,
        "UP": 274
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 0.9864864864864865,
    "best_candidate_false_directional_on_actual_flat": 576,
    "best_candidate_flat_recall": 0.3592880978865406,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 332,
      "FLAT": 324,
      "UP": 317
    },
    "candidate_count": 45,
    "parameters": {
      "margin": 0.1,
      "threshold": 0.55
    },
    "policy_name": "combined_conservative"
  },
  {
    "avg_accuracy": 0.3535457348406989,
    "avg_accuracy_edge": -0.5704008221993828,
    "avg_directional_recall": 1.0,
    "avg_false_directional_on_actual_flat": 629.0,
    "avg_false_flat_on_actual_directional": 0.0,
    "avg_flat_recall": 0.3003337041156838,
    "best_candidate_accuracy": 0.35354573484069884,
    "best_candidate_accuracy_edge": -0.5704008221993834,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 31,
        "FLAT": 0,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 326,
        "FLAT": 270,
        "UP": 303
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 1.0,
    "best_candidate_false_directional_on_actual_flat": 629,
    "best_candidate_flat_recall": 0.3003337041156841,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 357,
      "FLAT": 270,
      "UP": 346
    },
    "candidate_count": 45,
    "parameters": {
      "threshold": 0.3
    },
    "policy_name": "flat_min_probability"
  },
  {
    "avg_accuracy": 0.345323741007194,
    "avg_accuracy_edge": -0.5786228160328877,
    "avg_directional_recall": 1.0,
    "avg_false_directional_on_actual_flat": 637.0,
    "avg_false_flat_on_actual_directional": 0.0,
    "avg_flat_recall": 0.2914349276974414,
    "best_candidate_accuracy": 0.34532374100719426,
    "best_candidate_accuracy_edge": -0.5786228160328879,
    "best_candidate_confusion_matrix": {
      "DOWN": {
        "DOWN": 31,
        "FLAT": 0,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 338,
        "FLAT": 262,
        "UP": 299
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_candidate_directional_recall": 1.0,
    "best_candidate_false_directional_on_actual_flat": 637,
    "best_candidate_flat_recall": 0.2914349276974416,
    "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
    "best_candidate_predicted_distribution": {
      "DOWN": 369,
      "FLAT": 262,
      "UP": 342
    },
    "candidate_count": 45,
    "parameters": {
      "threshold": 0.5
    },
    "policy_name": "directional_confidence_floor"
  }
]
```

## Flat protection analysis
```json
{
  "actual_flat_count": 899,
  "best_policy_false_directional_on_actual_flat": 500,
  "best_policy_flat_recall": 0.44382647385984425,
  "best_policy_predicted_distribution": {
    "DOWN": 281,
    "FLAT": 400,
    "UP": 292
  },
  "overcorrection_risk": "NOT_DETERMINED"
}
```

## Directional preservation analysis
```json
{
  "actual_directional_count": 74,
  "best_policy_directional_recall": 0.9864864864864865,
  "risk": "stronger FLAT override may erase directional rows"
}
```

## h08 scope
- h08 issue known: true
- h08 fix applied: false
- h08 remains separately scoped.

## Guardrails
- no training run
- no wrapper / quick-quality rerun
- no run_fv3_cached_tuning.py
- no DB writes
- no ml_labels/ml_predictions writes
- labels/builders/gates/model logic unchanged
- class weights/objective/production calibration unchanged
- directional_confidence_floor 0.60 not implemented
- flat override not implemented
- existing real artifacts not mutated
- no new real sidecars/ZIP created by ML38.10.74
- archive recovery not performed
- no commit/planning/snapshot

## Tests
- full_pytest_result: 1187 passed, 0 skipped, 1 warning
- full_pytest_exit_code: 0
- full_pytest_log: `D:\disk_E\game_projects\traders\traders-ml-run-logs\full_pytest_ml38_10_74_20260709_192223.log`

## Raw diagnostic JSON
```json
{
  "actual_label_distribution": {
    "test_split": {
      "DOWN": 31,
      "FLAT": 899,
      "UP": 43,
      "total": 973
    }
  },
  "best_replay_policies": [
    {
      "avg_accuracy": 0.48509763617677254,
      "avg_accuracy_edge": -0.4388489208633096,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 500.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.4438264738598438,
      "best_candidate_accuracy": 0.4850976361767729,
      "best_candidate_accuracy_edge": -0.43884892086330934,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 251,
          "FLAT": 399,
          "UP": 249
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 500,
      "best_candidate_flat_recall": 0.44382647385984425,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 281,
        "FLAT": 400,
        "UP": 292
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.6
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.40698869475847876,
      "avg_accuracy_edge": -0.5169578622816037,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 576.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.35928809788654076,
      "best_candidate_accuracy": 0.40698869475847893,
      "best_candidate_accuracy_edge": -0.5169578622816033,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 302,
          "FLAT": 323,
          "UP": 274
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 576,
      "best_candidate_flat_recall": 0.3592880978865406,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 332,
        "FLAT": 324,
        "UP": 317
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.55
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.40698869475847876,
      "avg_accuracy_edge": -0.5169578622816037,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 576.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.35928809788654076,
      "best_candidate_accuracy": 0.40698869475847893,
      "best_candidate_accuracy_edge": -0.5169578622816033,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 302,
          "FLAT": 323,
          "UP": 274
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 576,
      "best_candidate_flat_recall": 0.3592880978865406,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 332,
        "FLAT": 324,
        "UP": 317
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.1,
        "threshold": 0.55
      },
      "policy_name": "combined_conservative"
    },
    {
      "avg_accuracy": 0.3535457348406989,
      "avg_accuracy_edge": -0.5704008221993828,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 629.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.3003337041156838,
      "best_candidate_accuracy": 0.35354573484069884,
      "best_candidate_accuracy_edge": -0.5704008221993834,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 326,
          "FLAT": 270,
          "UP": 303
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 629,
      "best_candidate_flat_recall": 0.3003337041156841,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 357,
        "FLAT": 270,
        "UP": 346
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.3
      },
      "policy_name": "flat_min_probability"
    },
    {
      "avg_accuracy": 0.345323741007194,
      "avg_accuracy_edge": -0.5786228160328877,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 637.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.2914349276974414,
      "best_candidate_accuracy": 0.34532374100719426,
      "best_candidate_accuracy_edge": -0.5786228160328879,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 338,
          "FLAT": 262,
          "UP": 299
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 637,
      "best_candidate_flat_recall": 0.2914349276974416,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 369,
        "FLAT": 262,
        "UP": 342
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.5
      },
      "policy_name": "directional_confidence_floor"
    }
  ],
  "candidate_ranking": [
    {
      "accuracy": 0.09146968139773895,
      "accuracy_edge": -0.8324768756423433,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 958,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 884,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.01668520578420467,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {},
      "policy_name": "calibrated_argmax",
      "predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "predicted_flat_count": 15,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.09146968139773895,
      "accuracy_edge": -0.8324768756423433,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 958,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 884,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.01668520578420467,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {},
      "policy_name": "raw_argmax",
      "predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "predicted_flat_count": 15,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.1366906474820144,
      "accuracy_edge": -0.7872559095580678,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 472,
          "FLAT": 59,
          "UP": 368
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 914,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 840,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.06562847608453838,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "margin": 0.02
      },
      "policy_name": "flat_margin_buffer",
      "predicted_distribution": {
        "DOWN": 503,
        "FLAT": 59,
        "UP": 411
      },
      "predicted_flat_count": 59,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.17985611510791366,
      "accuracy_edge": -0.7440904419321686,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 446,
          "FLAT": 101,
          "UP": 352
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 872,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 798,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.11234705228031146,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "margin": 0.05
      },
      "policy_name": "flat_margin_buffer",
      "predicted_distribution": {
        "DOWN": 477,
        "FLAT": 101,
        "UP": 395
      },
      "predicted_flat_count": 101,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.2199383350462487,
      "accuracy_edge": -0.7040082219938335,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 422,
          "FLAT": 140,
          "UP": 337
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 833,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 759,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.1557285873192436,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "margin": 0.08
      },
      "policy_name": "flat_margin_buffer",
      "predicted_distribution": {
        "DOWN": 453,
        "FLAT": 140,
        "UP": 380
      },
      "predicted_flat_count": 140,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.25077081192189105,
      "accuracy_edge": -0.6731757451181912,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 401,
          "FLAT": 170,
          "UP": 328
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 803,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 729,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.18909899888765294,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "margin": 0.1
      },
      "policy_name": "flat_margin_buffer",
      "predicted_distribution": {
        "DOWN": 432,
        "FLAT": 170,
        "UP": 371
      },
      "predicted_flat_count": 170,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.3011305241521069,
      "accuracy_edge": -0.6228160328879753,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 364,
          "FLAT": 219,
          "UP": 316
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 754,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 680,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.2436040044493882,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "margin": 0.15
      },
      "policy_name": "flat_margin_buffer",
      "predicted_distribution": {
        "DOWN": 395,
        "FLAT": 219,
        "UP": 359
      },
      "predicted_flat_count": 219,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.35354573484069884,
      "accuracy_edge": -0.5704008221993834,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 326,
          "FLAT": 270,
          "UP": 303
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 703,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 629,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.3003337041156841,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "threshold": 0.3
      },
      "policy_name": "flat_min_probability",
      "predicted_distribution": {
        "DOWN": 357,
        "FLAT": 270,
        "UP": 346
      },
      "predicted_flat_count": 270,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.09146968139773895,
      "accuracy_edge": -0.8324768756423433,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 958,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 884,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.01668520578420467,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "threshold": 0.35
      },
      "policy_name": "flat_min_probability",
      "predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "predicted_flat_count": 15,
      "rows": 973,
      "up_recall": 1.0
    },
    {
      "accuracy": 0.09146968139773895,
      "accuracy_edge": -0.8324768756423433,
      "actual_directional_count": 74,
      "actual_distribution": {
        "DOWN": 31,
        "FLAT": 899,
        "UP": 43
      },
      "actual_flat_count": 899,
      "candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "directional_predictions": 958,
      "directional_recall": 1.0,
      "down_recall": 1.0,
      "false_directional_on_actual_flat": 884,
      "false_flat_on_actual_directional": 0,
      "flat_recall": 0.01668520578420467,
      "majority_flat_baseline_accuracy": 0.9239465570400822,
      "parameters": {
        "threshold": 0.4
      },
      "policy_name": "flat_min_probability",
      "predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "predicted_flat_count": 15,
      "rows": 973,
      "up_recall": 1.0
    }
  ],
  "candidate_replay_summary": {
    "any_policy_beats_majority_baseline": false,
    "any_policy_positive_accuracy_edge": false,
    "candidate_policy_pairs_ranked": 900,
    "candidates_scanned": 45,
    "policies_tested": 20,
    "probability_sequences_identical_across_candidates": true,
    "unique_probability_sequences": 1
  },
  "confusion_matrix_summary": {
    "best_policy_confusion_matrix": {
      "DOWN": {
        "DOWN": 30,
        "FLAT": 1,
        "UP": 0
      },
      "FLAT": {
        "DOWN": 251,
        "FLAT": 399,
        "UP": 249
      },
      "UP": {
        "DOWN": 0,
        "FLAT": 0,
        "UP": 43
      }
    },
    "best_policy_name": "directional_confidence_floor",
    "best_policy_parameters": {
      "threshold": 0.6
    }
  },
  "decision": [
    "OUTCOME_AWARE_CALIBRATION_REPLAY_COMPLETED_NO_POLICY_BEATS_BASELINE"
  ],
  "decision_gate": {
    "actual_labels_available": true,
    "any_policy_beats_majority_baseline": false,
    "any_policy_positive_accuracy_edge": false,
    "calibrated_probabilities_available": true,
    "candidate_policy_pairs_ranked": true,
    "cascade_outcome_allowed_now": false,
    "decision": "OUTCOME_AWARE_CALIBRATION_REPLAY_COMPLETED_NO_POLICY_BEATS_BASELINE",
    "next_action_selected": true,
    "next_allowed_stage": "ML38.10.75 — class-prior class-balance diagnostic",
    "outcome_replay_completed": true,
    "production_like_recompute_allowed_now": false,
    "production_policy_allowed_now": false,
    "raw_probabilities_available": true,
    "tradable_edge_claim_allowed_now": false
  },
  "diagnostic_name": "outcome_aware_calibration_replay",
  "diagnostic_version": "ml38.10.74",
  "directional_preservation_analysis": {
    "actual_directional_count": 74,
    "best_policy_directional_recall": 0.9864864864864865,
    "risk": "stronger FLAT override may erase directional rows"
  },
  "evidence_sources": {
    "completion_marker_path": "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\solusdt_quick_quality_20260708_183037.completion.json",
    "evidence_mode": "READ_ONLY_ML38_10_73_SIDECARS",
    "output_dir": "D:\\disk_E\\game_projects\\traders\\traders-ml\\reports\\feature_regime_experiments\\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260708_153049",
    "real_artifacts_mutated": false,
    "rows_scanned": 291645,
    "schemas_scanned": 45,
    "streams_scanned": 45,
    "summaries_scanned": 45,
    "wrapper_log_path": "D:\\disk_E\\game_projects\\traders\\traders-ml-run-logs\\solusdt_quick_quality_20260708_183037.log",
    "zip_path": "D:\\disk_E\\game_projects\\traders\\traders-ml\\reports\\feature_regime_experiments\\quick_quality_fv3_cached_fresh_tuning_solusdt_15m_20260708_153049.zip"
  },
  "execution_mode": "READ_ONLY_OUTCOME_AWARE_CALIBRATION_REPLAY_NO_RERUN",
  "flat_protection_analysis": {
    "actual_flat_count": 899,
    "best_policy_false_directional_on_actual_flat": 500,
    "best_policy_flat_recall": 0.44382647385984425,
    "best_policy_predicted_distribution": {
      "DOWN": 281,
      "FLAT": 400,
      "UP": 292
    },
    "overcorrection_risk": "NOT_DETERMINED"
  },
  "guardrails": {
    "archive_recovery_performed": false,
    "cascade_outcome_run": false,
    "class_weights_changed": false,
    "commit_performed": false,
    "db_writes_during_stage": false,
    "directional_confidence_floor_implemented": false,
    "existing_real_artifacts_mutated": false,
    "flat_override_implemented": false,
    "h08_fix_applied": false,
    "labels_builders_gates_model_logic_changed": false,
    "ml_labels_writes_during_stage": false,
    "ml_predictions_writes_during_stage": false,
    "new_real_sidecars_created": false,
    "new_zip_created": false,
    "planning_update_performed": false,
    "production_calibration_policy_changed": false,
    "production_like_recompute": false,
    "quick_quality_rerun_during_stage": false,
    "run_fv3_cached_tuning_used_during_stage": false,
    "snapshot_performed": false,
    "tradable_edge_confirmed": false,
    "training_objective_changed": false,
    "training_run_during_stage": false,
    "wrapper_execute_used_during_stage": false
  },
  "h08_scope_boundary": {
    "h08_candidate_missing_or_failed_in_ml38_10_73": true,
    "h08_fix_applied": false,
    "h08_issue_known": true,
    "h08_not_part_of_outcome_replay": true,
    "h08_remains_separately_scoped": true
  },
  "next_step_plan": [
    "ML38.10.75 — class-prior class-balance diagnostic",
    "Do not implement production calibration policy in ML38.10.74.",
    "Keep h08 denominator fix separately scoped."
  ],
  "policy_grid_results": [
    {
      "avg_accuracy": 0.48509763617677254,
      "avg_accuracy_edge": -0.4388489208633096,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 500.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.4438264738598438,
      "best_candidate_accuracy": 0.4850976361767729,
      "best_candidate_accuracy_edge": -0.43884892086330934,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 251,
          "FLAT": 399,
          "UP": 249
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 500,
      "best_candidate_flat_recall": 0.44382647385984425,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 281,
        "FLAT": 400,
        "UP": 292
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.6
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.40698869475847876,
      "avg_accuracy_edge": -0.5169578622816037,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 576.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.35928809788654076,
      "best_candidate_accuracy": 0.40698869475847893,
      "best_candidate_accuracy_edge": -0.5169578622816033,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 302,
          "FLAT": 323,
          "UP": 274
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 576,
      "best_candidate_flat_recall": 0.3592880978865406,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 332,
        "FLAT": 324,
        "UP": 317
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.55
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.40698869475847876,
      "avg_accuracy_edge": -0.5169578622816037,
      "avg_directional_recall": 0.9864864864864862,
      "avg_false_directional_on_actual_flat": 576.0,
      "avg_false_flat_on_actual_directional": 1.0,
      "avg_flat_recall": 0.35928809788654076,
      "best_candidate_accuracy": 0.40698869475847893,
      "best_candidate_accuracy_edge": -0.5169578622816033,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 30,
          "FLAT": 1,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 302,
          "FLAT": 323,
          "UP": 274
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 0.9864864864864865,
      "best_candidate_false_directional_on_actual_flat": 576,
      "best_candidate_flat_recall": 0.3592880978865406,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 332,
        "FLAT": 324,
        "UP": 317
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.1,
        "threshold": 0.55
      },
      "policy_name": "combined_conservative"
    },
    {
      "avg_accuracy": 0.3535457348406989,
      "avg_accuracy_edge": -0.5704008221993828,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 629.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.3003337041156838,
      "best_candidate_accuracy": 0.35354573484069884,
      "best_candidate_accuracy_edge": -0.5704008221993834,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 326,
          "FLAT": 270,
          "UP": 303
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 629,
      "best_candidate_flat_recall": 0.3003337041156841,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 357,
        "FLAT": 270,
        "UP": 346
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.3
      },
      "policy_name": "flat_min_probability"
    },
    {
      "avg_accuracy": 0.345323741007194,
      "avg_accuracy_edge": -0.5786228160328877,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 637.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.2914349276974414,
      "best_candidate_accuracy": 0.34532374100719426,
      "best_candidate_accuracy_edge": -0.5786228160328879,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 338,
          "FLAT": 262,
          "UP": 299
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 637,
      "best_candidate_flat_recall": 0.2914349276974416,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 369,
        "FLAT": 262,
        "UP": 342
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.5
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.345323741007194,
      "avg_accuracy_edge": -0.5786228160328877,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 637.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.2914349276974414,
      "best_candidate_accuracy": 0.34532374100719426,
      "best_candidate_accuracy_edge": -0.5786228160328879,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 338,
          "FLAT": 262,
          "UP": 299
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 637,
      "best_candidate_flat_recall": 0.2914349276974416,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 369,
        "FLAT": 262,
        "UP": 342
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.05,
        "threshold": 0.5
      },
      "policy_name": "combined_conservative"
    },
    {
      "avg_accuracy": 0.345323741007194,
      "avg_accuracy_edge": -0.5786228160328877,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 637.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.2914349276974414,
      "best_candidate_accuracy": 0.34532374100719426,
      "best_candidate_accuracy_edge": -0.5786228160328879,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 338,
          "FLAT": 262,
          "UP": 299
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 637,
      "best_candidate_flat_recall": 0.2914349276974416,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 369,
        "FLAT": 262,
        "UP": 342
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.1,
        "threshold": 0.5
      },
      "policy_name": "combined_conservative"
    },
    {
      "avg_accuracy": 0.30113052415210706,
      "avg_accuracy_edge": -0.6228160328879753,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 680.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.24360400444938807,
      "best_candidate_accuracy": 0.3011305241521069,
      "best_candidate_accuracy_edge": -0.6228160328879753,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 364,
          "FLAT": 219,
          "UP": 316
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 680,
      "best_candidate_flat_recall": 0.2436040044493882,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 395,
        "FLAT": 219,
        "UP": 359
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.15
      },
      "policy_name": "flat_margin_buffer"
    },
    {
      "avg_accuracy": 0.2764645426515932,
      "avg_accuracy_edge": -0.6474820143884896,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 704.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.21690767519466073,
      "best_candidate_accuracy": 0.27646454265159304,
      "best_candidate_accuracy_edge": -0.6474820143884892,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 380,
          "FLAT": 195,
          "UP": 324
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 704,
      "best_candidate_flat_recall": 0.21690767519466073,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 411,
        "FLAT": 195,
        "UP": 367
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.45
      },
      "policy_name": "directional_confidence_floor"
    },
    {
      "avg_accuracy": 0.2764645426515932,
      "avg_accuracy_edge": -0.6474820143884896,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 704.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.21690767519466073,
      "best_candidate_accuracy": 0.27646454265159304,
      "best_candidate_accuracy_edge": -0.6474820143884892,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 380,
          "FLAT": 195,
          "UP": 324
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 704,
      "best_candidate_flat_recall": 0.21690767519466073,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 411,
        "FLAT": 195,
        "UP": 367
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.05,
        "threshold": 0.45
      },
      "policy_name": "combined_conservative"
    },
    {
      "avg_accuracy": 0.2507708119218909,
      "avg_accuracy_edge": -0.6731757451181908,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 729.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.189098998887653,
      "best_candidate_accuracy": 0.25077081192189105,
      "best_candidate_accuracy_edge": -0.6731757451181912,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 401,
          "FLAT": 170,
          "UP": 328
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 729,
      "best_candidate_flat_recall": 0.18909899888765294,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 432,
        "FLAT": 170,
        "UP": 371
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.1
      },
      "policy_name": "flat_margin_buffer"
    },
    {
      "avg_accuracy": 0.2199383350462487,
      "avg_accuracy_edge": -0.7040082219938341,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 759.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.15572858731924372,
      "best_candidate_accuracy": 0.2199383350462487,
      "best_candidate_accuracy_edge": -0.7040082219938335,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 422,
          "FLAT": 140,
          "UP": 337
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 759,
      "best_candidate_flat_recall": 0.1557285873192436,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 453,
        "FLAT": 140,
        "UP": 380
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.08
      },
      "policy_name": "flat_margin_buffer"
    },
    {
      "avg_accuracy": 0.17985611510791352,
      "avg_accuracy_edge": -0.7440904419321688,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 798.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.1123470522803114,
      "best_candidate_accuracy": 0.17985611510791366,
      "best_candidate_accuracy_edge": -0.7440904419321686,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 446,
          "FLAT": 101,
          "UP": 352
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 798,
      "best_candidate_flat_recall": 0.11234705228031146,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 477,
        "FLAT": 101,
        "UP": 395
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.05
      },
      "policy_name": "flat_margin_buffer"
    },
    {
      "avg_accuracy": 0.1366906474820144,
      "avg_accuracy_edge": -0.7872559095580675,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 840.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.06562847608453838,
      "best_candidate_accuracy": 0.1366906474820144,
      "best_candidate_accuracy_edge": -0.7872559095580678,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 472,
          "FLAT": 59,
          "UP": 368
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 840,
      "best_candidate_flat_recall": 0.06562847608453838,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 503,
        "FLAT": 59,
        "UP": 411
      },
      "candidate_count": 45,
      "parameters": {
        "margin": 0.02
      },
      "policy_name": "flat_margin_buffer"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {},
      "policy_name": "calibrated_argmax"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {},
      "policy_name": "raw_argmax"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.35
      },
      "policy_name": "flat_min_probability"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.4
      },
      "policy_name": "flat_min_probability"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.45
      },
      "policy_name": "flat_min_probability"
    },
    {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {
        "threshold": 0.5
      },
      "policy_name": "flat_min_probability"
    }
  ],
  "raw_vs_calibrated_comparison": {
    "accuracy_delta_calibrated_minus_raw": 0.0,
    "calibrated_argmax": {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {},
      "policy_name": "calibrated_argmax"
    },
    "directional_recall_delta_calibrated_minus_raw": 0.0,
    "false_directional_delta_calibrated_minus_raw": 0.0,
    "flat_recall_delta_calibrated_minus_raw": 0.0,
    "raw_argmax": {
      "avg_accuracy": 0.09146968139773905,
      "avg_accuracy_edge": -0.8324768756423427,
      "avg_directional_recall": 1.0,
      "avg_false_directional_on_actual_flat": 884.0,
      "avg_false_flat_on_actual_directional": 0.0,
      "avg_flat_recall": 0.01668520578420466,
      "best_candidate_accuracy": 0.09146968139773895,
      "best_candidate_accuracy_edge": -0.8324768756423433,
      "best_candidate_confusion_matrix": {
        "DOWN": {
          "DOWN": 31,
          "FLAT": 0,
          "UP": 0
        },
        "FLAT": {
          "DOWN": 501,
          "FLAT": 15,
          "UP": 383
        },
        "UP": {
          "DOWN": 0,
          "FLAT": 0,
          "UP": 43
        }
      },
      "best_candidate_directional_recall": 1.0,
      "best_candidate_false_directional_on_actual_flat": 884,
      "best_candidate_flat_recall": 0.01668520578420467,
      "best_candidate_id": "fv3_cached_fresh_tuning_solusdt_15m_20260708_153049_label_grid_lv19_h12_tts_thr065_sqmask060",
      "best_candidate_predicted_distribution": {
        "DOWN": 532,
        "FLAT": 15,
        "UP": 426
      },
      "candidate_count": 45,
      "parameters": {},
      "policy_name": "raw_argmax"
    }
  },
  "recommendation": {
    "next_stage": "ML38.10.75 — class-prior class-balance diagnostic",
    "production_policy_recommended_now": false,
    "reason": "No diagnostic replay may directly authorize production policy; policy candidate requires separate proposal stage if positive edge exists.",
    "recommendation_type": "NO_CALIBRATION_POLICY_BEATS_BASELINE"
  },
  "sidecar_field_contract_validation": {
    "LF_only": true,
    "all_rows_have_actual_label": true,
    "all_rows_have_calibrated_probabilities": true,
    "all_rows_have_raw_probabilities": true,
    "all_rows_have_row_alignment_key": true,
    "contract_version": "ml38.10.69",
    "field_contract_status": "PASSED",
    "label_substitution_detected": false,
    "prediction_layers_present": true,
    "raw_contract_stats": {
      "bad_row_examples": [],
      "bad_rows": 0,
      "contract_version_rows": 291645,
      "duplicate_alignment_key_streams": 0,
      "lf_only_failures": 0,
      "rows_scanned": 291645,
      "rows_with_actual_label": 291645,
      "rows_with_calibrated_probabilities": 291645,
      "rows_with_prediction_layers": 291645,
      "rows_with_raw_probabilities": 291645,
      "rows_with_row_alignment_key": 291645,
      "schema_contract_failures": 0,
      "schemas_scanned": 45,
      "streams_scanned": 45,
      "summaries_scanned": 45,
      "summary_hash_size_failures": 0
    },
    "row_alignment_key_unique_per_stream": true,
    "summary_hash_size_valid": true
  }
}
```
