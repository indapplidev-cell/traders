from app.market_reader.engine_trend.oos_validation import (
    build_manual_annotation_template,
    run_balanced_oos_validation,
)


def item(index: int, label: str, predicted: str, manual: str | None = None) -> dict:
    return {
        "source_stage": "ENGINE-TREND-15B",
        "window": {
            "window_id": f"w{index}",
            "symbol": "TEST",
            "interval": "15m",
            "period_start": f"2026-01-{index:02d}T00:00:00Z",
            "period_end": f"2026-01-{index:02d}T23:45:00Z",
            "reference_label": label,
            "selection_reason": "deterministic proxy",
            "manual_label": manual,
        },
        "composer": {"regime": predicted},
    }


def dataset(manual: bool = False) -> list[dict]:
    rows = []
    index = 1
    for label, regime in (("EXPECTED_UP", "UP"), ("EXPECTED_DOWN", "DOWN"), ("EXPECTED_FLAT", "FLAT")):
        for _ in range(4):
            rows.append(item(index, label, regime, regime if manual else None))
            index += 1
    return rows


def test_proxy_labels_cannot_authorize_acceptance() -> None:
    result = run_balanced_oos_validation(dataset())
    assert result.status == "BLOCKED_MANUAL_LABELS"
    assert result.balanced_count == 12
    assert result.test_count == 6
    assert result.metrics["exact_match_rate"] == 1.0


def test_manual_balanced_oos_can_reach_decision_gate() -> None:
    result = run_balanced_oos_validation(dataset(manual=True))
    assert result.status == "READY_FOR_ACCEPTANCE_DECISION"
    assert result.manual_test_count == result.test_count


def test_manual_template_hides_predictions() -> None:
    template = build_manual_annotation_template(dataset())
    assert len(template["windows"]) == 12
    assert all(row["manual_label"] is None for row in template["windows"])
    assert all("predicted_regime" not in row for row in template["windows"])
