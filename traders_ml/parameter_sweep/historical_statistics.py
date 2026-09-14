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
        self.trace: list[dict] = []

    def at(self, cutoff_ms: int):
        """Share already-validated immutable outcomes across boundary evaluations."""
        result = object.__new__(HistoricalStatistics)
        result.rows, result.fingerprint = self.rows, self.fingerprint
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
                data = path.read_bytes()
                total_bytes += len(data)
                if total_bytes > 128 * 1024 * 1024:
                    raise ValueError("STATISTICS_ARCHIVE_BUDGET_EXCEEDED")
                target = frozen_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                identities[str(path)] = sha256(data).hexdigest()
        prospective = load_prospective_outcomes(frozen_root, parameter_set_id=parameter_set_id)
    payload = {"schema": "historical-statistics/1", "source_version": STATISTICS_SOURCE_VERSION,
               "source_files": identities, "parameter_set_id": parameter_set_id,
               "paper_count": len(paper), "prospective_count": len(prospective),
               "availability_basis": "OUTCOME_COMPLETION_TIME_FROM_CURRENT_ARCHIVE",
               "historical_source_completeness": "NOT_INDEPENDENTLY_CERTIFIED",
               "outcomes": [asdict(r) for r in (*paper, *prospective)]}
    payload["fingerprint"] = fingerprint(payload)
    ResultSearchService._write(output, payload)
    return payload


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
