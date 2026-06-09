import json

from typer.testing import CliRunner

from app.cli.commands import build_gate_policy_adapter_preview_payload, cli


def test_build_gate_policy_adapter_preview_payload() -> None:
    payload = build_gate_policy_adapter_preview_payload()

    assert payload["raw_payload_count"] == 4
    assert payload["input_count"] == 4
    assert payload["result_count"] == 4

    assert payload["report"]["total"] == 4
    assert payload["report"]["allowed_total"] == 2
    assert payload["report"]["blocked_total"] == 2

    assert payload["decision_sequence"] == [
        "ALLOW_LONG",
        "ALLOW_SHORT",
        "BAD_REGIME",
        "LOW_CONFIDENCE",
    ]

    assert payload["allowed_sequence"] == [
        True,
        True,
        False,
        False,
    ]

    assert payload["report"]["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["report"]["decision_counts"]["ALLOW_SHORT"] == 1
    assert payload["report"]["decision_counts"]["BAD_REGIME"] == 1
    assert payload["report"]["decision_counts"]["LOW_CONFIDENCE"] == 1


def test_gate_policy_adapter_preview_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["gate-policy-adapter-preview"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["raw_payload_count"] == 4
    assert payload["input_count"] == 4
    assert payload["result_count"] == 4

    assert payload["report"]["total"] == 4
    assert payload["report"]["allowed_total"] == 2
    assert payload["report"]["blocked_total"] == 2

    assert payload["decision_sequence"] == [
        "ALLOW_LONG",
        "ALLOW_SHORT",
        "BAD_REGIME",
        "LOW_CONFIDENCE",
    ]
