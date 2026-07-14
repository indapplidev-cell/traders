"""Run the fixed replay pack through the hardened ENGINE-TREND-19 core."""

import json
from pathlib import Path

import engine_trend_18_hypothesis_replay as replay
from app.market_reader.engine_trend.data_source_boundary import (
    CandleDataRequest,
    build_candle_data_batch,
    run_engine_trend_from_batch,
)


SOURCE_RESULTS = {
    "ENGINE-TREND-15": Path("reports/engine_trend/historical_validation/results"),
    "ENGINE-TREND-15B": Path(
        "reports/engine_trend/symbol_suitability_validation/results"
    ),
}


def main() -> int:
    replay.STAGE = "ENGINE-TREND-19"
    replay.ROOT = Path("reports/engine_trend/technical_analysis_hardening/replay")
    replay.REPORT = Path(
        "reports/engine_trend/engine_trend_19_hardened_replay_report.md"
    )
    windows = replay.load_rows()
    if len(windows) != 60:
        raise RuntimeError(f"EXPECTED_60_WINDOWS:GOT_{len(windows)}")
    replay.ROOT.mkdir(parents=True, exist_ok=True)
    items = []
    for window in windows:
        source = SOURCE_RESULTS[window["source_stage"]] / f"{window['window_id']}_result.json"
        saved = json.loads(source.read_text(encoding="utf-8"))
        rows = saved["boundary"]["batch"]["rows"]
        request = CandleDataRequest(
            window["symbol"],
            window["interval"],
            int(window["window_length"]),
            window["period_start"],
            window["period_end"],
            "saved_validation_artifact",
        )
        batch = build_candle_data_batch(
            request,
            rows,
            min_candle_count=int(window["window_length"]),
            strict_market_series=True,
        )
        boundary = run_engine_trend_from_batch(batch)
        if boundary.status.value != "READY":
            raise RuntimeError(
                f"WINDOW_REPLAY_FAILED:{window['window_id']}:{boundary.errors}"
            )
        item = replay.build_diagnostic(window, boundary)
        items.append(item)
        replay.write_json(replay.ROOT / "json" / f"{window['window_id']}.json", item)
        markdown_path = replay.ROOT / "markdown" / f"{window['window_id']}.md"
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(replay.markdown(item), encoding="utf-8")
    replay.finish(items)
    print(f"{replay.STAGE}: replayed={len(items)} source=saved_validation_artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
