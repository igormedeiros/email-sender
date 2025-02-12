import pytest
from unittest.mock import Mock, patch, mock_open
from src.email_sender.email_service import EmailService
from src.email_sender.config import Config

@pytest.fixture
def mock_config():
    config = Mock(spec=Config)
    config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "test_user",
        "password": "test_pass",
        "use_tls": True
    }
    config.email_config = {
        "sender": "sender@test.com",
        "batch_size": 50
    }
    return config

@pytest.fixture
def email_service(mock_config):
    return EmailService(mock_config)

def test_create_message(email_service):
    message = email_service._create_message(
        to_email="recipient@test.com",
        subject="Test Subject",
        text_content="Test email content"
    )
    
    assert message["To"] == "recipient@test.com"
    assert message["Subject"] == "Test Subject"
    assert message["From"] == "sender@test.com"

@patch('builtins.open', new_callable=mock_open, read_data="Hello {name}!")
@patch('src.email_sender.email_service.smtplib.SMTP')
def test_send_batch(mock_smtp, mock_file, email_service):
    # Setup
    mock_smtp_instance = Mock()
    mock_smtp.return_value = mock_smtp_instance
    mock_smtp.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
    mock_smtp.return_value.__exit__ = Mock()
    
    recipients = [
        {"email": "test1@example.com", "name": "Test 1"},
        {"email": "test2@example.com", "name": "Test 2"}
    ]
    
    # Execute
    email_service.send_batch(recipients, "email.txt", "Test Subject")
    
    # Assert
    assert mock_smtp_instance.send_message.call_count == 2
    mock_file.assert_called_once_with("email.txt", "r", encoding="utf-8")
    
    # Verificar se starttls é chamado apenas quando use_tls é True
    if email_service.config.smtp_config["use_tls"]:
        mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with(
        email_service.config.smtp_config["username"],
        email_service.config.smtp_config["password"]
    )