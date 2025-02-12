import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock
from email_sender.email_service import EmailService
from email_sender.config import Config
import smtplib

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
        "sender": "sender@test.com",
        "batch_size": 50,
        "batch_delay": 0  # Zero para os testes serem mais rápidos
    }
    return config

@pytest.fixture
def email_service(mock_config):
    return EmailService(mock_config)

@patch('email_sender.email_service.time.sleep')  # Patch sleep at the correct module level
def test_create_message(mock_sleep, email_service):
    message = email_service._create_message(
        to_email="recipient@test.com",
        subject="Test Subject",
        text_content="Test email content"
    )
    
    assert message["To"] == "recipient@test.com"
    assert message["Subject"] == "Test Subject"
    assert message["From"] == "sender@test.com"
    mock_sleep.assert_not_called()

@patch('email_sender.email_service.time.sleep')  # Patch sleep at the correct module level
@patch('builtins.open', new_callable=mock_open, read_data="Hello {name}!")
@patch('smtplib.SMTP')
def test_send_batch(mock_smtp, mock_file, mock_sleep, email_service):
    # Setup
    mock_smtp_instance = MagicMock()
    mock_smtp_instance.__enter__ = Mock(return_value=mock_smtp_instance)
    mock_smtp_instance.__exit__ = Mock(return_value=None)
    mock_smtp.return_value = mock_smtp_instance
    
    recipients = [
        {"email": "test1@example.com", "name": "Test 1"},
        {"email": "test2@example.com", "name": "Test 2"}
    ]
    
    # Execute
    email_service.send_batch(recipients, "email.txt", "Test Subject")
    
    # Assert
    assert mock_smtp_instance.send_message.call_count == 2
    mock_file.assert_called_once_with("email.txt", "r", encoding="utf-8")
    mock_sleep.assert_not_called()
    
    # Verificar se starttls é chamado apenas quando use_tls é True
    if email_service.config.smtp_config["use_tls"]:
        mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with(
        email_service.config.smtp_config["username"],
        email_service.config.smtp_config["password"]
    )

@patch('email_sender.email_service.time.sleep')  # Patch sleep at the correct module level
@patch('builtins.open', new_callable=mock_open, read_data="Hello {name}!")
@patch('smtplib.SMTP')
def test_smtp_retry_on_disconnect(mock_smtp, mock_file, mock_sleep, email_service):
    # Setup first connection fails, second succeeds
    mock_smtp_instance1 = MagicMock()
    mock_smtp_instance1.send_message.side_effect = smtplib.SMTPServerDisconnected()
    mock_smtp_instance1.__enter__ = Mock(return_value=mock_smtp_instance1)
    mock_smtp_instance1.__exit__ = Mock(return_value=None)
    
    mock_smtp_instance2 = MagicMock()
    mock_smtp_instance2.__enter__ = Mock(return_value=mock_smtp_instance2)
    mock_smtp_instance2.__exit__ = Mock(return_value=None)
    
    mock_smtp.side_effect = [
        mock_smtp_instance1,
        mock_smtp_instance2
    ]
    
    recipients = [{"email": "test1@example.com", "name": "Test 1"}]
    
    # Execute
    email_service.send_batch(recipients, "email.txt", "Test Subject")
    
    # Assert
    # Should try to send twice (once with each connection)
    assert mock_smtp_instance1.send_message.call_count == 1
    assert mock_smtp_instance2.send_message.call_count == 1
    mock_sleep.assert_not_called()

@patch('email_sender.email_service.time.sleep')  # Patch sleep at the correct module level
@patch('builtins.open', new_callable=mock_open, read_data="Hello {name}!")
@patch('smtplib.SMTP')
def test_smtp_retry_on_connection_failure(mock_smtp, mock_file, mock_sleep, email_service):
    # Setup - First two attempts fail, third succeeds
    mock_success = MagicMock()
    mock_success.__enter__ = Mock(return_value=mock_success)
    mock_success.__exit__ = Mock(return_value=None)
    
    mock_smtp.side_effect = [
        smtplib.SMTPConnectError(454, "Connection failed"),
        smtplib.SMTPConnectError(454, "Connection failed"),
        mock_success  # Third attempt succeeds with proper context manager
    ]
    
    recipients = [{"email": "test1@example.com", "name": "Test 1"}]
    
    # Execute
    email_service.send_batch(recipients, "email.txt", "Test Subject")
    
    # Assert
    assert mock_smtp.call_count == 3  # Should attempt connection three times
    mock_sleep.assert_not_called()  # Ensure no real delays happened