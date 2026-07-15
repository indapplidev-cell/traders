from pathlib import Path


def test_systemd_documents_auto_restart():
    text = (Path(__file__).parents[1] / "docs/operations/engine_market_data_04_systemd.md").read_text()
    assert "Restart=always" in text and "systemctl enable" in text
