# ENGINE-TREND-00 - Plan Anchor and Planning Cleanup

## Status

`PASS`

## Purpose

This stage anchors the new active planning direction for the project.

The project now starts from:

`planning/00_ENGINE_TREND_MASTER_PLAN.md`

## Active plan

`planning/00_ENGINE_TREND_MASTER_PLAN.md`

## Active README

`planning/README.md`

## Legacy planning

Old active planning Markdown files were moved to:

`planning/legacy_before_engine_trend/`

They are historical only and must not guide future work.

## New module direction

The new L1 core module is:

`engine_trend`

Target path:

`app/market_reader/engine_trend/`

## Core rule

`engine_trend` receives candles for a selected period and classifies the period as:

- `UP`
- `DOWN`
- `FLAT`
- `UNKNOWN`

It must use one stable book-based methodology and must not tune window settings to force a regime.

## Book foundation

The new module is based on:

- Steve Nison
- T. M. Altunina
- Jack Schwager

## Existing infrastructure

The existing project infrastructure is kept:

- BOOK-DATA
- CLI
- JSON exports
- BOOK-L2
- FLAT_CONTEXT
- reports
- tests

The old L1 remains only as baseline/reference until `engine_trend` is validated.

## Safety

No trading logic was added.

Forbidden outputs remain forbidden:

- BUY
- SELL
- LONG
- SHORT
- ENTRY
- EXIT
- edge validation
- runtime trading

Required safety values remain:

- `trade_signal = NOT_EVALUATED`
- `safe_for_runtime_trading = false`

## Checks

- branch check: PASS
- planning README check: PASS
- master plan exists: PASS
- old planning files moved to legacy: PASS
- books folder preserved: PASS
- no runtime logic changed: PASS
- no L1/L2/DATA logic changed: PASS

## Next stage

`ENGINE-TREND-01 — Current L1 vs Book Matrix Audit`

The next stage must audit the current L1 against the book-based matrix before any new `engine_trend` core logic is implemented.
