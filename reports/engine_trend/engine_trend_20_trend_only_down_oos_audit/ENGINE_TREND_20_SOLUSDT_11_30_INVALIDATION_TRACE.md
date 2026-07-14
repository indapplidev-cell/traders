# SOLUSDT 2026-07-08 11:30 — invalidation trace

Conclusion: **diagnostic reporting gap**, not evidence of a continuation status logic defect.

The existing `_continuation_hypothesis` status precedence sets `INVALIDATED` whenever `alt.impulse_correction.structural_pivot_breached` is true. This case has that exact condition. Specifically, the bearish leg started at index 87 (2026-07-08 09:30 UTC) at 77.49, and the following correction ended at index 91 (10:30 UTC) at 77.50; `77.50 >= 77.49` breached that stored bearish pivot. The exported reason code is correct, but the hypothesis trace itself omits these pivot/leg values.

## Exported hypothesis

```json
{
  "hypothesis_id": "hypothesis:down_continuation",
  "hypothesis_type": "DOWN_CONTINUATION",
  "direction": "BEARISH",
  "status": "INVALIDATED",
  "score": 0.8945359634916941,
  "trigger_index": 82,
  "confirmation_index": null,
  "supporting_event_ids": [
    "pattern:81:82:BEARISH_SEPARATING_LINES_CONTEXT"
  ],
  "reason_codes": [
    "HYPOTHESIS_STRUCTURE_ALIGNED",
    "HYPOTHESIS_CANDLE_CONTINUATION_CONFIRMED",
    "HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED",
    "HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED",
    "HYPOTHESIS_STRUCTURAL_PIVOT_BREACHED"
  ],
  "confidence": 0.8945359634916941,
  "evidence": {
    "reason_codes": [
      "HYPOTHESIS_STRUCTURE_ALIGNED",
      "HYPOTHESIS_CANDLE_CONTINUATION_CONFIRMED",
      "HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED",
      "HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED",
      "HYPOTHESIS_STRUCTURAL_PIVOT_BREACHED"
    ],
    "supporting_events": [
      {
        "event_id": "pattern:81:82:BEARISH_SEPARATING_LINES_CONTEXT",
        "pattern_code": "BEARISH_SEPARATING_LINES_CONTEXT",
        "direction": "BEARISH",
        "role": "CONTINUATION",
        "start_index": 81,
        "end_index": 82,
        "prior_structure": "BEARISH_STRUCTURE",
        "zone_relation": "AT_RESISTANCE",
        "related_zone_mid": 78.325,
        "follow_through": "CONFIRMED",
        "status": "CONFIRMED",
        "reason_codes": [
          "BEARISH_SEPARATING_LINES_CONTEXT",
          "PATTERN_PRIOR_BEARISH_STRUCTURE",
          "AT_RESISTANCE",
          "PATTERN_LEVEL_CONTEXT_CONFIRMED",
          "PATTERN_FOLLOW_THROUGH_CONFIRMED"
        ]
      }
    ]
  },
  "missing_evidence": [],
  "rejection_reason": [
    "HYPOTHESIS_STRUCTURE_ALIGNED",
    "HYPOTHESIS_CANDLE_CONTINUATION_CONFIRMED",
    "HYPOTHESIS_TECHNICAL_INDICATORS_ALIGNED",
    "HYPOTHESIS_DECISION_WINDOW_PROGRESS_ALIGNED",
    "HYPOTHESIS_STRUCTURAL_PIVOT_BREACHED"
  ],
  "pending_reason": null,
  "conflict_reason": null
}
```

## Altunina source condition

```json
{
  "impulse_correction": {
    "bullish_impulse_total": 0.0,
    "bearish_impulse_total": 9.620000000000019,
    "bullish_correction_total": 0.0,
    "bearish_correction_total": 5.120000000000019,
    "dominant_impulse_direction": "DOWN",
    "max_pullback_depth": 1.0181818181818276,
    "average_pullback_depth": 0.5971060424534919,
    "correction_count": 7,
    "correction_limit": 0.62,
    "correction_limit_breached": true,
    "structural_pivot_breached": true,
    "nearest_fibonacci_level": 0.62
  },
  "pivot_breach_provenance": [
    {
      "comparison": "correction_end_price >= prior_bearish_impulse_start_price",
      "prior_structural_pivot": {
        "index": 87,
        "timestamp": "2026-07-08T09:30:00Z",
        "price": 77.49,
        "point_type": "HIGH"
      },
      "correction_leg": {
        "start": {
          "index": 89,
          "timestamp": "2026-07-08T10:00:00Z",
          "price": 76.94,
          "point_type": "LOW"
        },
        "end": {
          "index": 91,
          "timestamp": "2026-07-08T10:30:00Z",
          "price": 77.5,
          "point_type": "HIGH"
        },
        "direction": "UP",
        "absolute_change": 0.5600000000000023,
        "relative_change": 0.007278398752274529,
        "candle_span": 2
      },
      "observed": "77.5 >= 77.49"
    }
  ]
}
```

Suggested future task: `ENGINE-TREND-20A_DIAGNOSTIC_TRACE_HARDENING`. Add diagnostic-only provenance fields for pivot price/index, correction endpoint price/index, breach comparator, and status-transition cause. Do not change status logic or thresholds.
