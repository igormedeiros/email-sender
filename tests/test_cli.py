import pytest
from typer.testing import CliRunner
from datetime import datetime
from unittest.mock import Mock, patch, mock_open, MagicMock
from email_sender.fast_cli import app, generate_report
from email_sender.config import Config
from email_sender.email_service import EmailService
from pathlib import Path
import smtplib

runner = CliRunner()

@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "test_user",
        "password": "test_pass",
        "use_tls": True,
        "retry_attempts": 3,
        "retry_delay": 0,  # Zero para os testes serem mais rápidos
        "send_timeout": 10
    }
    config.email_config = {
        "sender": "test@example.com",
        "batch_size": 50,
        "xlsx_file": "test.xlsx",
        "test_recipient": "test@recipient.com",
        "default_subject": "Test Subject",
        "batch_delay": 0  # Zero para os testes serem mais rápidos
    }
    return config

@patch('pathlib.Path.mkdir')  # Mock directory creation
@patch('email_sender.fast_cli.time.sleep')  # Patch sleep at module level
@patch('email_sender.email_service.time.sleep')  # Also patch sleep in email_service
@patch('email_sender.fast_cli.Config')
@patch('email_sender.fast_cli.EmailService')
@patch('email_sender.fast_cli.XLSXReader')
def test_send_emails_command(mock_xlsx_reader_cls, mock_email_service_cls, mock_config_cls, 
                           mock_email_sleep, mock_cli_sleep, mock_mkdir, mock_config, tmp_path):
    # Setup mocks
    mock_config_cls.return_value = mock_config
    mock_email_service = Mock()
    mock_email_service_cls.return_value = mock_email_service
    
    mock_xlsx_reader = Mock()
    mock_xlsx_reader.total_records = 2
    mock_xlsx_reader.get_batches.return_value = [[
        {"email": "user1@test.com"},
        {"email": "user2@test.com"}
    ]]
    mock_xlsx_reader_cls.return_value = mock_xlsx_reader
    
    template_file = tmp_path / "template.txt"
    template_file.write_text("Test template")
    
    # Run command
    with patch('builtins.open', mock_open(read_data="Test template")):
        result = runner.invoke(app, ["send-emails", str(template_file)])
    
    # Verify
    assert result.exit_code == 0
    assert "Email sending completed!" in result.stdout
    assert "Report saved to:" in result.stdout
    mock_email_service.send_batch.assert_called()
    mock_cli_sleep.assert_not_called()  # Ensure no real delays happened
    mock_email_sleep.assert_not_called()  # Ensure no real delays happened
    mock_mkdir.assert_called_once_with(exist_ok=True)

@patch('pathlib.Path.mkdir')  # Mock directory creation
@patch('email_sender.fast_cli.time.sleep')  # Patch sleep at module level
@patch('email_sender.email_service.time.sleep')  # Also patch sleep in email_service
@patch('email_sender.email_service.smtplib.SMTP')  # Patch at the correct module level
@patch('email_sender.fast_cli.Config')
@patch('email_sender.fast_cli.EmailService')
def test_test_smtp_command(mock_email_service_cls, mock_config_cls, mock_smtp, 
                          mock_email_sleep, mock_cli_sleep, mock_mkdir, mock_config):
    # Setup mocks
    mock_config_cls.return_value = mock_config
    mock_email_service = Mock()
    mock_email_service_cls.return_value = mock_email_service
    
    # Configure mock SMTP connection
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__ = Mock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = Mock(return_value=None)
    mock_smtp.return_value = mock_smtp_instance
    
    mock_email_service._create_smtp_connection.return_value = mock_smtp_instance
    
    # Run command
    result = runner.invoke(app, ["test-smtp"])
    
    # Verify
    assert result.exit_code == 0
    assert "SMTP test successful!" in result.stdout
    mock_cli_sleep.assert_not_called()
    mock_email_sleep.assert_not_called()

@patch('email_sender.fast_cli.time.sleep')  # Patch sleep at module level
@patch('email_sender.email_service.time.sleep')  # Also patch sleep in email_service
@patch('email_sender.fast_cli.Config')
def test_test_smtp_command_no_recipient(mock_config_cls, mock_email_sleep, mock_cli_sleep, mock_config):
    # Modify mock to not have test_recipient
    mock_config.email_config["test_recipient"] = None
    mock_config_cls.return_value = mock_config
    
    # Run command
    result = runner.invoke(app, ["test-smtp"])
    
    # Verify
    assert result.exit_code == 1
    assert "test_recipient not configured" in result.stdout
    mock_cli_sleep.assert_not_called()  # Ensure no real delays happened
    mock_email_sleep.assert_not_called()  # Ensure no real delays happened

@patch('pathlib.Path.mkdir')  # Mock directory creation
@patch('email_sender.fast_cli.time.sleep')  # Patch sleep at module level
@patch('email_sender.email_service.time.sleep')  # Also patch sleep in email_service
@patch('email_sender.fast_cli.Config')
@patch('email_sender.fast_cli.EmailService')
@patch('email_sender.fast_cli.XLSXReader')
def test_send_emails_with_custom_subject(mock_xlsx_reader_cls, mock_email_service_cls, mock_config_cls, 
                                       mock_email_sleep, mock_cli_sleep, mock_mkdir, mock_config, tmp_path):
    # Setup mocks
    mock_config_cls.return_value = mock_config
    mock_email_service = Mock()
    mock_email_service_cls.return_value = mock_email_service
    
    # Setup XLSXReader mock
    mock_xlsx_reader = Mock()
    mock_xlsx_reader.total_records = 2
    mock_xlsx_reader.get_batches.return_value = [[
        {"email": "user1@test.com"},
        {"email": "user2@test.com"}
    ]]
    mock_xlsx_reader_cls.return_value = mock_xlsx_reader
    
    template_file = tmp_path / "template.txt"
    template_file.write_text("Test template")
    custom_subject = "Custom Subject"
    
    # Run command with custom subject
    with patch('builtins.open', mock_open(read_data="Test template")):
        result = runner.invoke(app, [
            "send-emails",
            str(template_file),
            "--subject", custom_subject
        ])
    
    # Verify
    assert result.exit_code == 0
    assert "Email sending completed!" in result.stdout
    mock_email_service.send_batch.assert_called()
    args = mock_email_service.send_batch.call_args[0]
    assert args[2] == custom_subject  # Third argument should be the subject
    mock_cli_sleep.assert_not_called()  # Ensure no real delays happened
    mock_email_sleep.assert_not_called()  # Ensure no real delays happened