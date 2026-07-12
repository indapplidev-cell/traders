# traders-ml planning

## Active plan

The single active source of truth for the project is:

```text
planning/00_ENGINE_TREND_MASTER_PLAN.md
```

All new work must start from this plan.

---

## Current direction

The project direction is now:

```text
engine_trend
```

`engine_trend` is the new clean book-based L1 core for reading trend and market state.

Its task is to receive candles for a selected period and determine:

```text
UP
DOWN
FLAT
UNKNOWN
```

The decision must be explained through evidence and `reason_codes`.

---

## Book-based foundation

`engine_trend` must be based on three books:

```text
1. Steve Nison — Japanese Candlestick Charting Techniques /
   Японские свечи: графический анализ финансовых рынков

2. Т. М. Алтунина — Основы технического анализа финансовых рынков

3. Jack Schwager — Technical Analysis /
   Технический анализ. Полный курс
```

The books must be used as much as possible, but only for market reading.

Allowed:

```text
book idea
→ measurable feature
→ evidence
→ reason_code
→ contribution to UP / DOWN / FLAT / UNKNOWN
```

Forbidden:

```text
BUY
SELL
LONG
SHORT
ENTRY
EXIT
trading signal
edge validation
runtime trading
```

---

## Active architecture decision

Do not rewrite the whole project from scratch.

Keep the existing infrastructure:

```text
BOOK-DATA
CLI
JSON exports
BOOK-L2
FLAT_CONTEXT
JSON consumers
API readiness checks
reports
tests
terminal guide
```

But write the new L1 market-reading core cleanly inside the existing project:

```text
app/market_reader/engine_trend/
```

The old L1 remains only as:

```text
baseline
reference
comparison target
```

It must not guide the new logic.

---

## Planning rule

Old planning documents are historical only.

They must not be used as active instructions.

Old active planning files should be moved to:

```text
planning/legacy_before_engine_trend/
```

The active `planning/` root should contain only the current planning entry point and supporting folders such as:

```text
planning/README.md
planning/00_ENGINE_TREND_MASTER_PLAN.md
planning/books/
planning/legacy_before_engine_trend/
planning/backup/
```

---

## Mandatory rule before every new stage

Before starting any new stage, check:

```text
planning/00_ENGINE_TREND_MASTER_PLAN.md
```

Then state:

```text
1. Which ENGINE-TREND stage is being executed.
2. Which files should be created or changed.
3. What must not be changed.
4. What result counts as PASS.
```

If a proposed task does not fit the master plan, do not start it without explicit user approval.

---

## Next stage

The next stage is:

```text
ENGINE-TREND-00 — Plan Anchor and Planning Cleanup
```

Purpose:

```text
1. Save the master plan as planning/00_ENGINE_TREND_MASTER_PLAN.md.
2. Move old active planning Markdown files to planning/legacy_before_engine_trend/.
3. Rewrite this README to point only to the new master plan.
4. Confirm that future work starts from engine_trend.
```

After that:

```text
ENGINE-TREND-01 — Current L1 vs Book Matrix Audit
```

---

## Safety

`engine_trend` must never produce trading instructions.

Always keep:

```text
trade_signal = NOT_EVALUATED
safe_for_runtime_trading = false
```

The project remains:

```text
market reading only
no trading execution
no edge claims
no BOOK-L3
```
