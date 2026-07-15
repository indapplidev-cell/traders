# ENGINE-MARKET-DATA-02 report

Implemented PostgreSQL/SQLAlchemy 2.x storage with six separate candle tables and
an Alembic revision integrated into the existing migration chain. Millisecond UTC
open/close timestamps are authoritative; readable columns use timezone-aware UTC.

The boundary scheduler emits deduplicated 15m, 1h, 4h and 1d events after a 2-second
safety delay. A 15m event checks 1x15m, 3x5m and 15x1m; the other events check one
candle of their own timeframe. Synchronization queries the repository first and
uses public REST only for contiguous missing ranges. Only exact, closed responses
are persisted. No candles are synthesized, interpolated or zero-filled.

Warmup constructs the latest closed expected range per enabled timeframe, checks
existing rows, downloads gaps in bounded pages, then verifies completeness. Sync
reports remain causal (`future_bars_used=false`) and degrade when gaps remain.

This stage has no downstream-engine imports and makes no analysis behavior change.
