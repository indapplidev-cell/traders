import json

from typer.testing import CliRunner

from app.cli.commands import build_gate_policy_smoke_payload, cli


def test_build_gate_policy_smoke_payload() -> None:
    payload = build_gate_policy_smoke_payload()

    assert payload["total"] == 5
    assert payload["allowed_total"] == 2
    assert payload["blocked_total"] == 3

    assert payload["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["decision_counts"]["ALLOW_SHORT"] == 1
    assert payload["decision_counts"]["BAD_REGIME"] == 1
    assert payload["decision_counts"]["LOW_CONFIDENCE"] == 1
    assert payload["decision_counts"]["BLOCK"] == 1

    assert payload["reason_counts"]["signal_passed_gate_policy"] == 2
    assert payload["reason_counts"]["regime_is_not_trusted"] == 1
    assert payload["reason_counts"]["confidence_below_threshold"] == 1
    assert payload["reason_counts"]["direction_is_not_tradeable"] == 1


def test_gate_policy_smoke_cli_outputs_json() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["gate-policy-smoke"])

    assert result.exit_code == 0

    payload = json.loads(result.stdout)

    assert payload["total"] == 5
    assert payload["allowed_total"] == 2
    assert payload["blocked_total"] == 3
    assert payload["decision_counts"]["ALLOW_LONG"] == 1
    assert payload["decision_counts"]["ALLOW_SHORT"] == 1
