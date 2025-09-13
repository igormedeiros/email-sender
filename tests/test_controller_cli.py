from email_sender.controller_cli import app
import pytest
from typer.testing import CliRunner

runner = CliRunner()


def test_controller_cli_app_exists():
    assert app is not None


def test_controller_cli_send_emails_help():
    """Test that the send-emails command shows help correctly."""
    result = runner.invoke(app, ["send-emails", "--help"])
    assert result.exit_code == 0
    assert "Send batch HTML emails" in result.output


def test_controller_cli_reset_send_state_help():
    """Test that the reset-send-state command shows help correctly."""
    result = runner.invoke(app, ["reset-send-state", "--help"])
    assert result.exit_code == 0
    assert "Limpa a tabela de estado de envio" in result.output


def test_controller_cli_send_emails_no_args():
    """Test that send-emails command runs without args (should succeed with default config)."""
    result = runner.invoke(app, ["send-emails"])
    # This should succeed because default config files are created
    assert result.exit_code == 0


def test_controller_cli_invalid_command():
    """Test that invalid commands are handled properly."""
    result = runner.invoke(app, ["invalid-command"])
    assert result.exit_code != 0
