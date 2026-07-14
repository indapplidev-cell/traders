"""Build proxy OOS metrics and a blind manual-label template for stage 19."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.market_reader.engine_trend.oos_validation import (
    build_manual_annotation_template,
    run_balanced_oos_validation,
)

ROOT = Path("reports/engine_trend/technical_analysis_hardening")
REPLAY = ROOT / "replay" / "json"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    items = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(REPLAY.glob("*.json"))]
    if not items:
        raise RuntimeError(f"NO_REPLAY_ITEMS:{REPLAY}")
    result = run_balanced_oos_validation(items)
    write_json(ROOT / "ENGINE_TREND_19_OOS_VALIDATION.json", result.to_dict())
    write_json(
        ROOT / "ENGINE_TREND_19_MANUAL_LABEL_TEMPLATE.json",
        build_manual_annotation_template(items),
    )
    rows = list(result.test_rows)
    with (ROOT / "ENGINE_TREND_19_OOS_TEST_MATRIX.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    metrics = json.dumps(result.metrics, ensure_ascii=False)
    (ROOT / "ENGINE_TREND_19_OOS_VALIDATION.md").write_text(
        f"""# ENGINE-TREND-19 — Balanced Out-of-Sample Validation

Status: **{result.status}**.

- raw rows: {result.raw_count}
- unique periods: {result.unique_count}
- balanced UP/DOWN/FLAT rows: {result.balanced_count}
- chronological train/test: {result.train_count}/{result.test_count}
- independently manual-labelled test rows: {result.manual_test_count}/{result.test_count}
- proxy test metrics: `{metrics}`

The proxy split is suitable for regression diagnostics only. Production acceptance remains blocked until every OOS test period is labelled manually without engine predictions being visible to the reviewer.
""",
        encoding="utf-8",
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
