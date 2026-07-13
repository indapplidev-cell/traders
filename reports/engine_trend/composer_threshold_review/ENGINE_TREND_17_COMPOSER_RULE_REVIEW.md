# ENGINE-TREND-17 — Composer Rule Review

## Current thresholds
`MIN_REGIME_SCORE = 0.30`; `MIN_SCORE_MARGIN = 0.08`. Candidate evidence is additive. Confidence is clamped to `[0,1]`; UNKNOWN is capped at `0.35`, with the conservative score fallback capped at `0.30`.

## Fallback and UNKNOWN rules
Invalid OHLC fails closed at confidence 0. Empty/low coverage remains UNKNOWN (maximum 0/0.25). High conflict remains UNKNOWN unless a confirmed returned/false-breakout range is clear. A winner below 0.30 or with top-two margin below 0.08 remains UNKNOWN, except detected-range FLAT margin handling.

## Conflict and coverage
Coverage and conflict are evaluated before the generic score fallback. Medium conflict caps composed confidence at 0.60; high conflict caps it further. These guards are unchanged.

## Finding
The old code clamped additive candidate totals before ranking. In all 60 reviewed traces both UP and DOWN became 1.0, manufacturing a zero top-two gap and forcing `COMPOSER_CONSERVATIVE_FALLBACK_UNKNOWN`. The selected change ranks raw totals and clamps only public scores/confidence. No threshold value or extraction behavior changes.
