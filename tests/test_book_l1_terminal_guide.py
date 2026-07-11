from __future__ import annotations

import builtins

import pytest
from typer.testing import CliRunner

import app.cli.commands as commands_module
from app.cli.commands import cli
from app.market_reader.terminal_guide import (
    build_book_l1_terminal_guide,
    get_book_l1_terminal_command_examples,
)


def test_build_book_l1_terminal_guide_returns_string() -> None:
    guide = build_book_l1_terminal_guide()

    assert isinstance(guide, str)
    assert guide


def test_terminal_guide_contains_title_and_commands() -> None:
    guide = build_book_l1_terminal_guide()

    assert "BOOK-L1 Terminal Command Guide" in guide
    assert "book-l1-interactive-preview" in guide
    assert "book-l1-preview" in guide
    assert "book-l1-api-preview" in guide
    assert "book-l1-multi-preview" in guide
    assert "book-l1-history-preview" in guide
    assert "book-l1-timeline-preview" in guide
    assert "book-l1-guide" in guide


def test_terminal_guide_contains_json_export_contract_rules() -> None:
    guide = build_book_l1_terminal_guide()

    assert "--export-json" in guide
    assert "current_preview.json" in guide
    assert "multi_preview.json" in guide
    assert "history_preview.json" in guide
    assert "timeline_preview.json" in guide
    assert "JSON files are overwritten on each export run." in guide
    assert "Filenames are stable." in guide
    assert "Terminal output is for humans." in guide
    assert "JSON export is for API." in guide
    assert "Runtime Markdown export is not used." in guide


def test_terminal_guide_contains_fail_closed_safety_values() -> None:
    guide = build_book_l1_terminal_guide()

    assert "trade_signal = NOT_EVALUATED" in guide
    assert "safe_for_runtime_trading = false" in guide
    assert "orders_enabled = false" in guide
    assert "live_trading_connected = false" in guide
    assert "traders_core_connected = false" in guide
    assert "approved_for_live_trading = false" in guide
    assert "approved_for_auto_activation = false" in guide
    assert "model_training_executed = false" in guide
    assert "binance_download_executed = false" in guide


def test_terminal_guide_does_not_contain_working_trade_action_phrases() -> None:
    guide = build_book_l1_terminal_guide().lower()

    assert "place order" not in guide
    assert "open long" not in guide
    assert "open short" not in guide


def test_command_examples_are_tuple_and_embedded_in_guide() -> None:
    guide = build_book_l1_terminal_guide()
    examples = get_book_l1_terminal_command_examples()

    assert isinstance(examples, tuple)
    assert examples
    assert all(isinstance(example, str) for example in examples)
    for example in examples:
        assert example in guide


def test_cli_book_l1_guide_prints_guide_without_database_or_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_get_session() -> object:
        raise AssertionError("book-l1-guide must not open a database session")

    def fail_input(prompt: str = "") -> str:
        raise AssertionError("book-l1-guide must not call input()")

    monkeypatch.setattr(commands_module, "get_session", fail_get_session)
    monkeypatch.setattr(builtins, "input", fail_input)

    result = CliRunner().invoke(cli, ["book-l1-guide"])

    assert result.exit_code == 0
    assert "BOOK-L1 Terminal Command Guide" in result.stdout
    assert "Runtime Markdown export is not used." in result.stdout


def test_main_help_contains_book_l1_guide() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "book-l1-guide" in result.stdout
    assert "Use `python -m app.cli.commands book-l1-guide` for BOOK-L1 command examples." in result.stdout


def test_book_l1_guide_help_contains_terminal_command_guide() -> None:
    result = CliRunner().invoke(cli, ["book-l1-guide", "--help"])

    assert result.exit_code == 0
    assert "terminal command guide" in result.stdout.lower()
