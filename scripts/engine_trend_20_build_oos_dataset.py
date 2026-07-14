"""Deterministic ENGINE-TREND-20 dataset-builder entry point (audit only)."""

from __future__ import annotations

import json

from app.db.session import get_session
from engine_trend_20_trend_only_down_oos_audit import build_dataset_specs


def main() -> int:
    session = get_session()
    try:
        specs = build_dataset_specs(session)
    finally:
        session.close()
    print(json.dumps({"count": len(specs), "windows": specs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
