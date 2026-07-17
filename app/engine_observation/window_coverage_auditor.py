from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from .observation_models import RunRecord, jsonable

INTERVAL_MS = 15 * 60 * 1000


def expected_boundaries(start_utc: datetime, end_utc: datetime) -> list[int]:
    start_ms, end_ms = int(start_utc.timestamp() * 1000), int(end_utc.timestamp() * 1000)
    first = ((start_ms + INTERVAL_MS - 1) // INTERVAL_MS) * INTERVAL_MS
    return list(range(first, end_ms, INTERVAL_MS))


def audit_coverage(runs: list[RunRecord], symbols: tuple[str, ...], timeframe: str,
                   start_utc: datetime, end_utc: datetime,
                   reclaim_seconds: int = 300, now: datetime | None = None) -> dict:
    boundaries = expected_boundaries(start_utc, end_utc)
    now = now or datetime.now(timezone.utc)
    by_symbol: dict[str, dict] = {}
    for symbol in symbols:
        relevant = [r for r in runs if r.symbol == symbol and r.primary_timeframe == timeframe]
        expected = {(symbol, timeframe, b) for b in boundaries}
        counts = Counter((r.symbol, r.primary_timeframe, r.closed_until_ms) for r in relevant)
        observed = set(counts) & expected
        missing = sorted(key[2] for key in expected - set(counts))
        duplicates = sorted(key[2] for key, count in counts.items() if key in expected and count > 1)
        stale = [r for r in relevant if r.closed_until_ms in boundaries and r.status in {"PENDING", "RUNNING"}
                 and (r.started_at or r.closed_until_utc) <= now - timedelta(seconds=reclaim_seconds)]
        completed = sum(r.status == "COMPLETED" and r.closed_until_ms in boundaries for r in relevant)
        skipped = sum(r.status.startswith("SKIPPED_") and r.closed_until_ms in boundaries for r in relevant)
        extra = sorted(r.closed_until_ms for r in relevant if r.closed_until_ms not in boundaries)
        total = len(expected)
        by_symbol[symbol] = {
            "expected_windows": total, "observed_windows": len(observed), "completed_windows": completed,
            "skipped_windows": skipped, "missing_windows": len(missing), "duplicate_windows": len(duplicates),
            "unfinished_windows": len(stale), "extra_out_of_range_windows": len(extra),
            "coverage_ratio": len(observed) / total if total else 1.0,
            "completion_ratio": completed / total if total else 1.0,
            "missing_boundaries_utc": [datetime.fromtimestamp(v / 1000, tz=timezone.utc).isoformat() for v in missing],
            "duplicate_boundaries_utc": [datetime.fromtimestamp(v / 1000, tz=timezone.utc).isoformat() for v in duplicates],
        }
    keys = ("expected_windows", "observed_windows", "completed_windows", "skipped_windows",
            "missing_windows", "duplicate_windows", "unfinished_windows", "extra_out_of_range_windows")
    aggregate = {key: sum(item[key] for item in by_symbol.values()) for key in keys}
    aggregate["coverage_ratio"] = aggregate["observed_windows"] / aggregate["expected_windows"] if aggregate["expected_windows"] else 1.0
    aggregate["completion_ratio"] = aggregate["completed_windows"] / aggregate["expected_windows"] if aggregate["expected_windows"] else 1.0
    return {"by_symbol": by_symbol, "aggregate": aggregate}
