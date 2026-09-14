"""Frozen causal statistical inputs for research; no production writes.

Uses the production loader/estimator and filters BEFORE hierarchy construction.
This records outcomes available in the acquired source archive, not a claim of
an exact historical filesystem snapshot. Source completeness remains explicit.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
from tempfile import TemporaryDirectory
from datetime import datetime

from sqlalchemy.orm import sessionmaker

from app.engine_paper.scalping_statistics import (
    PaperOutcome, PostgresPaperOutcomeStatisticsSource, hierarchy_from_outcomes,
    load_prospective_outcomes, STATISTICS_SOURCE_VERSION,
)
from .engine import ReadOnlyResearchDatabase, resolve_database_binding
from .result_search import fingerprint, ResultSearchService


class HistoricalStatistics:
    def __init__(self, payload: dict, cutoff_ms: int):
        claimed = payload["fingerprint"]
        if fingerprint({k: v for k, v in payload.items() if k != "fingerprint"}) != claimed:
            raise ValueError("STATISTICS_FINGERPRINT_MISMATCH")
        self.rows = tuple(PaperOutcome(**r) for r in payload["outcomes"])
        self.cutoff_ms = cutoff_ms
        self.fingerprint = claimed
        self.quality = payload.get("evidence_quality", "UNVERIFIED")
        self.trace: list[dict] = []

    def at(self, cutoff_ms: int):
        """Share already-validated immutable outcomes across boundary evaluations."""
        result = object.__new__(HistoricalStatistics)
        result.rows, result.fingerprint = self.rows, self.fingerprint
        result.quality = self.quality
        result.cutoff_ms, result.trace = cutoff_ms, []
        return result

    def resolve(self, **query):
        # Unknown timestamps cannot be promoted to historical availability.
        causal = [r for r in self.rows if 0 < r.observed_at_ms <= self.cutoff_ms]
        hierarchy = hierarchy_from_outcomes(causal, **query)
        self.trace.append({"query": query, "cutoff_ms": self.cutoff_ms,
                           "eligible_outcomes": hierarchy.outcome_count,
                           "excluded_future_or_undated": len(self.rows) - len(causal),
                           "hierarchy": asdict(hierarchy)})
        return hierarchy


def freeze_statistics(root: Path, output: Path, parameter_set_id: str) -> dict:
    if output.exists():
        raise ValueError("STATISTICS_OUTPUT_EXISTS")
    manifest_file = root / "manifest.json"
    manifest_bytes = manifest_file.read_bytes()
    manifest = json.loads(manifest_bytes)
    # The production loader skips missing parts; research must not hide them.
    missing = [p["path"] for p in manifest.get("parts", [])
               if p.get("kind") == "outcomes" and not (root / p["path"]).is_file()]
    if missing:
        raise ValueError("STATISTICS_ARCHIVE_PARTS_MISSING")
    database = ReadOnlyResearchDatabase(resolve_database_binding())
    try:
        source = PostgresPaperOutcomeStatisticsSource(sessionmaker(bind=database.engine))
        paper = source._load()
    finally:
        database.dispose()
    from hashlib import sha256
    identities = {str(manifest_file): sha256(manifest_bytes).hexdigest()}
    validation = {"records": 0, "invalid_causal_records": 0, "excluded_reasons": {}}
    with TemporaryDirectory(prefix="traders-statistics-") as temporary:
        frozen_root = Path(temporary)
        (frozen_root / "manifest.json").write_bytes(manifest_bytes)
        total_bytes = len(manifest_bytes)
        for part in manifest.get("parts", []):
            if part.get("kind") == "outcomes":
                relative = Path(part["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("UNSAFE_ARCHIVE_PART_PATH")
                path = root / relative
                if total_bytes + path.stat().st_size > 128 * 1024 * 1024:
                    raise ValueError("STATISTICS_ARCHIVE_BUDGET_EXCEEDED")
                data = path.read_bytes()
                total_bytes += len(data)
                if total_bytes > 128 * 1024 * 1024:
                    raise ValueError("STATISTICS_ARCHIVE_BUDGET_EXCEEDED")
                target = frozen_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                verified = []
                for line in data.splitlines():
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    validation["records"] += 1
                    reason = validate_outcome_time(record)
                    if reason:
                        validation["invalid_causal_records"] += 1
                        counts = validation["excluded_reasons"]
                        counts[reason] = counts.get(reason, 0) + 1
                    else:
                        verified.append(line)
                target.write_bytes(b"\n".join(verified) + b"\n")
                identities[str(path)] = sha256(data).hexdigest()
        prospective = load_prospective_outcomes(frozen_root, parameter_set_id=parameter_set_id)
    payload = {"schema": "historical-statistics/2", "source_version": STATISTICS_SOURCE_VERSION,
               "source_files": identities, "parameter_set_id": parameter_set_id,
               "paper_count": len(paper), "prospective_count": len(prospective),
               "availability_basis": "EVENT_TIME_COMPLETED_OUTCOMES_WITH_CLOSED_PATH_VALIDATION",
               "historical_source_completeness": "ALL_DECLARED_ARCHIVE_PARTS_CHECKED_EXCLUSIONS_RECORDED",
               "evidence_quality": "HISTORICAL_VERIFIED",
               "quality_scope": "CAUSAL_EVENT_TIME_STATISTICS_NOT_EXACT_PRODUCTION_READER_STATE",
               "causal_validation": validation,
               "outcomes": [asdict(r) for r in (*paper, *prospective)]}
    payload["fingerprint"] = fingerprint(payload)
    ResultSearchService._write(output, payload)
    return payload


def validate_outcome_time(record: dict) -> str | None:
    """Verify event-time availability against actual recorded outcome candles."""
    try:
        completed = datetime.fromisoformat(record["completed_at"].replace("Z", "+00:00"))
        if completed.utcoffset() is None:
            return "UNDATED_COMPLETION"
        cutoff = int(completed.timestamp() * 1000)
        path = record["closed_candle_path"]
        if not path:
            return "OUTCOME_PATH_MISSING"
        if any(int(c["close_time_ms"]) > cutoff for c in path):
            return "FUTURE_OUTCOME_CANDLE"
        if any(int(c["close_time_ms"]) != int(c["open_time_ms"]) + 59999 for c in path):
            return "INVALID_CANDLE_INTERVAL"
        opens = [int(c["open_time_ms"]) for c in path]
        if len(set(opens)) != len(opens) or any(b-a != 60000 for a,b in zip(opens, opens[1:])):
            return "OUTCOME_PATH_GAPS_OR_DUPLICATES"
        if record.get("path_diagnostics", {}).get("missing_open_time_ms"):
            return "OUTCOME_PATH_INCOMPLETE"
        return None
    except (KeyError, ValueError, TypeError, OverflowError):
        return "INVALID_OUTCOME_TIME_EVIDENCE"


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--parameter-set-id", required=True)
    a = p.parse_args()
    result = freeze_statistics(a.source, a.output, a.parameter_set_id)
    print(json.dumps({k: result[k] for k in ("fingerprint", "paper_count", "prospective_count",
                                            "historical_source_completeness")}))


if __name__ == "__main__":
    main()
