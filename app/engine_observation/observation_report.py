from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .observation_models import jsonable

ARTIFACTS = {
    "summary": "ONLINE_PIPELINE_OBSERVATION_01_SUMMARY.json",
    "coverage": "ONLINE_PIPELINE_OBSERVATION_01_COVERAGE.json",
    "funnel": "ONLINE_PIPELINE_OBSERVATION_01_FUNNEL.json",
    "reasons": "ONLINE_PIPELINE_OBSERVATION_01_REASONS.json",
    "latency": "ONLINE_PIPELINE_OBSERVATION_01_LATENCY.json",
    "integrity": "ONLINE_PIPELINE_OBSERVATION_01_INTEGRITY.json",
    "safety": "ONLINE_PIPELINE_OBSERVATION_01_SAFETY.json",
    "trace": "ONLINE_PIPELINE_OBSERVATION_01_TRACE.json",
}


def render_markdown(report: dict) -> str:
    summary, coverage, funnel = report["summary"], report["coverage"], report["funnel"]
    latency, integrity, safety = report["latency"], report["integrity"], report["safety"]
    lines = ["# ONLINE-PIPELINE-OBSERVATION-01 Report", "", f"## 1. Final verdict\n\n`{summary['verdict']}`",
        f"\n## 2. Observation interval UTC\n\n`{summary['start_utc']}` — `{summary['end_utc']}` ([start, end)).",
        "\n## 3. Runtime/service state", "", f"```json\n{json.dumps(jsonable(report['runtime']), indent=2)}\n```",
        "\n## 4–5. Expected vs observed windows / coverage by symbol", "",
        "| Symbol | Expected | Observed | Completed | Skipped | Missing | Duplicates | Coverage |",
        "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for symbol, row in coverage["by_symbol"].items():
        lines.append(f"| {symbol} | {row['expected_windows']} | {row['observed_windows']} | {row['completed_windows']} | {row['skipped_windows']} | {row['missing_windows']} | {row['duplicate_windows']} | {row['coverage_ratio']:.2%} |")
    lines += ["\n## 6–8. Status, funnel and final-result distribution", "",
              f"```json\n{json.dumps(funnel, indent=2)}\n```", "\n## 9. Top reason codes by module", "",
              f"```json\n{json.dumps(report['reasons'], indent=2)}\n```",
              "\n## 10. Freshness skips and recovery", "", f"Freshness skips: **{summary['freshness_skip_count']}**.",
              "\n## 11. Errors and stale reservations", "", f"Module/errors: **{summary['error_count']}**; stale reservations: **{summary['stale_reservation_count']}**.",
              "\n## 12–13. Latency percentiles and slowest windows", "", f"```json\n{json.dumps(latency, indent=2)}\n```",
              "\n## 14. DB integrity checks", "", f"```json\n{json.dumps(integrity, indent=2)}\n```",
              "\n## 15. Safety audit", "", f"```json\n{json.dumps(safety, indent=2)}\n```",
              "\n## 16. Current market_data_sync_state", "", f"```json\n{json.dumps(jsonable(report['sync_state']), indent=2)}\n```",
              "\n## 17. Operational blockers", ""]
    lines += [f"- {item}" for item in summary["failures"]] or ["No hard operational blockers detected."]
    lines += ["\n## 18. Research observations that are not operational failures", "",
              "`NO_PLAN`, `NO_ACTION`, `NO_SETUP`, strategy rejection, and zero `PAPER_PLAN_READY` are research outcomes, not operational defects.",
              "\n## 19. Recommended next stage", "", summary["recommended_next_stage"], ""]
    return "\n".join(lines)


def write_artifacts(output_dir: Path, report: dict, report_md: str, report_json: str) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    mapping = dict(ARTIFACTS); mapping["summary"] = report_json
    for key, filename in mapping.items():
        path = output_dir / filename
        path.write_text(json.dumps(jsonable(report[key]), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        paths.append(str(path))
    md_path = output_dir / report_md
    md_path.write_text(render_markdown(report), encoding="utf-8"); paths.append(str(md_path))
    manifest = {"stage": "ONLINE-PIPELINE-OBSERVATION-01", "artifacts": sorted(Path(p).name for p in paths),
                "contains_full_payload_dumps": False, "runtime_database_writes": False}
    manifest_path = output_dir / "ONLINE_PIPELINE_OBSERVATION_01_ARTIFACT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8"); paths.append(str(manifest_path))
    return paths
