# ENGINE-TREND-29 — Unified contextual diagnostics audit

## Baseline

- Current baseline: `0a04e85eae82d8a079bb693253b8f9a5e9342338` (ENGINE-TREND-28B).
- Previous checkpoint: `20fd992edd556b5eb08f2e711e3ee9d1f769c7db`.
- Branch at implementation start: `feature/engine-trend-28b`.
- The working tree was clean before implementation.

## Scope

ENGINE-TREND-29 combines the safety intent of contextual UNKNOWN/zone diagnostics, offline report exposure, and unified safety hardening and regression audit. It stabilizes only the offline diagnostic/report contract.

ENGINE-TREND-29 does not solve UNKNOWN. It does not improve trading decisions, authorize paper/live trading, tune thresholds, change composer selection, or create setups or signals. Any future decision-changing work must be a separate explicitly approved stage.

## Files inspected

- `app/market_reader/engine_trend/contextual_diagnostics.py`
- `app/market_reader/engine_trend/offline_report_diagnostics.py`
- `scripts/engine_trend_18_hypothesis_replay.py`
- `tests/test_engine_trend_28a_contextual_diagnostics.py`
- `tests/test_engine_trend_28b_report_diagnostics_exposure.py`
- ENGINE-TREND-28A and ENGINE-TREND-28B report artifacts

## Files changed

- `app/market_reader/engine_trend/contextual_diagnostics.py`
- `app/market_reader/engine_trend/offline_report_diagnostics.py`
- `scripts/engine_trend_18_hypothesis_replay.py`
- `tests/test_engine_trend_29_unified_contextual_diagnostics_audit.py`
- The six report artifacts listed by `ENGINE_TREND_29_ARTIFACT_MANIFEST.json`

No runtime, trading runtime, composer, threshold, source-selection, setup-contract, execution, order, portfolio, or risk file changed.

## Diagnostics flow summary

The engine and composer first produce the final result. `scripts/engine_trend_18_hypothesis_replay.build_diagnostic` copies that finalized result into an offline replay artifact. Only then does `attach_contextual_diagnostics` receive the completed artifact, deep-copy it, calculate contextual diagnostics, and add the optional top-level `contextual_diagnostics` field.

The enriched JSON is written to offline replay files and the same section is rendered by the replay Markdown formatter. No diagnostic value is fed back into regime selection, hypothesis selection, setup eligibility, trade decisions, or runtime. The offline adapter now compares the finalized source artifact with the enriched copy and raises if any pre-existing field changed; it also verifies that the diagnostic's source regime equals the finalized composer regime.

## Safety guarantees

- Attachment phase: `after_final_composer_decision`.
- Source regime and final regime are unchanged.
- Selected hypothesis remains value-equivalent.
- Setup eligibility and trade/no-trade fields remain value-equivalent when present.
- Diagnostics always remain non-actionable and create neither setup nor trade signal.
- Strong-looking zone, MTF, and indicator tags are negative controls, not confirmations.
- The safety assertion exists only in the offline report adapter and is not imported by live or paper execution.

## Known case verification

| Case | Original | Diagnostic context | Result |
| --- | --- | --- | --- |
| ETHUSDT 2026-07-14 10:00 | UNKNOWN / NO_ACTION | Local range below resistance, breakout unconfirmed, non-causal bullish pressure, higher-TF bearish risk | UNKNOWN / NO_ACTION; unchanged |
| BTCUSDT 2026-07-13 16:00 | UNKNOWN / WAIT_FOR_CONFIRMATION / NO_ACTION | Bearish structure/pressure without confirmed DOWN continuation | UNKNOWN / WAIT_FOR_CONFIRMATION / NO_ACTION; unchanged |
| SOLUSDT 2026-07-08 18:30 | UNKNOWN / NO_ACTION | DOWN_CONTINUATION conflicts with CONFIRMED_RANGE | UNKNOWN / NO_ACTION; unchanged |
| SOLUSDT 2026-07-08 23:45 | FLAT / NO_ACTION | CONFIRMED_RANGE_CONTEXT | FLAT / NO_ACTION; unchanged |

The machine-readable case details and observability counts are in `ENGINE_TREND_29_KNOWN_CASES_AUDIT.json` and `ENGINE_TREND_29_NO_ACTION_SAFETY_AUDIT.json`. Across four audited cases, diagnostics changed zero decisions, created zero setups, and created zero trade signals.

## Not-observable policy

Historical artifacts may omit candles, price context, zone proximity inputs, technical-indicator pressure, or multi-timeframe snapshots. Such fields are recorded as `not_observable`; they are never converted to `false`. Missing data cannot reduce risk or create confirmation. The schema keeps `false`, `true`, `unknown`, `not_observable`, and `not_applicable` as five distinct semantic states and permits partial historical source data.

## Report exposure policy

Contextual diagnostics are exposed only in offline replay JSON and per-window offline Markdown. Runtime, paper trading, live trading, setup selection, and execution paths neither import nor require the diagnostic adapter.

## Negative controls

The focused audit generates `NEAR_SUPPORT`, `NEAR_RESISTANCE`, `HIGHER_TF_BULLISH_RISK`, `HIGHER_TF_BEARISH_RISK`, and `INDICATOR_PRESSURE_WITHOUT_CAUSAL_TRIGGER` together. The expected and verified outcome remains UNKNOWN / NO_ACTION with no setup and no trade signal.

## Test commands

```text
pytest tests/test_engine_trend_28a_contextual_diagnostics.py
pytest tests/test_engine_trend_28b_report_diagnostics_exposure.py
pytest tests/test_engine_trend_29_unified_contextual_diagnostics_audit.py
pytest tests/test_engine_trend_*.py
git diff --check
```

All JSON report artifacts are parsed during verification, the generated and partial historical diagnostic payloads are checked against the ENGINE-TREND-29 schema, and the manifest is checked as the complete report-artifact inventory.

## Final acceptance status

**ACCEPTED — offline diagnostics hardening only.** Runtime decision behavior is preserved. Paper/live trading is not authorized. No automatic commit was created.
