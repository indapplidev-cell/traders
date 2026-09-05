from pathlib import Path


def test_desktop_projection_separates_active_and_closed_positions() -> None:
    client = Path(__file__).resolve().parents[3] / "traders-client" / "src" / "traders_client"
    controller = (client / "application" / "app_controller.py").read_text(encoding="utf-8")
    view = (client / "ui" / "paper_trading_view.py").read_text(encoding="utf-8")
    assert 'item.state in {"OPEN", "CLOSING"}' in controller
    assert "last_closed_position" in controller
    assert "paper.paper_positions = active_positions" in controller
    assert "count: {len(p.paper_positions)}" in view
