"""Additional tests for SMTP manager to improve coverage."""

import pytest
from unittest.mock import patch, MagicMock
from email_sender.smtp_manager import SmtpManager
import smtplib


def test_smtp_manager_initialization():
    """Test SmtpManager initialization."""
    mock_config = MagicMock()
    mock_config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpass",
        "use_tls": True,
        "retry_attempts": 3,
        "retry_delay": 5,
        "send_timeout": 10
    }
    mock_config.email_config = {
        "sender": "Test Sender <test@example.com>"
    }
    
    smtp_manager = SmtpManager(mock_config)
    assert smtp_manager is not None
    assert smtp_manager.config == mock_config


def test_extract_email_address():
    """Test _extract_email_address method."""
    mock_config = MagicMock()
    smtp_manager = SmtpManager(mock_config)
    
    # Test with standard format
    result = smtp_manager._extract_email_address("Test Sender <test@example.com>")
    assert result == "test@example.com"
    
    # Test with just email
    result = smtp_manager._extract_email_address("test@example.com")
    assert result == "test@example.com"
    
    # Test with empty string
    result = smtp_manager._extract_email_address("")
    assert result == ""


def test_create_message():
    """Test _create_message method."""
    mock_config = MagicMock()
    mock_config.email_config = {
        "sender": "Test Sender <test@example.com>"
    }
    
    smtp_manager = SmtpManager(mock_config)
    
    # Test creating HTML message
    message = smtp_manager._create_message(
        to_email="recipient@example.com",
        subject="Test Subject",
        content="<html><body><h1>Test</h1></body></html>",
        is_html=True
    )
    
    assert message["Subject"] == "Test Subject"
    assert message["From"] == "Test Sender <test@example.com>"
    assert message["To"] == "recipient@example.com"
    # Should have both text and HTML parts
    assert len(message.get_payload()) == 2


def test_create_message_text_only():
    """Test _create_message method with text only."""
    mock_config = MagicMock()
    mock_config.email_config = {
        "sender": "Test Sender <test@example.com>"
    }
    
    smtp_manager = SmtpManager(mock_config)
    
    # Test creating text message
    message = smtp_manager._create_message(
        to_email="recipient@example.com",
        subject="Test Subject",
        content="Test content",
        is_html=False
    )
    
    assert message["Subject"] == "Test Subject"
    assert message["From"] == "Test Sender <test@example.com>"
    assert message["To"] == "recipient@example.com"
    # Should have only one part
    assert len(message.get_payload()) == 1


def test_create_smtp_connection():
    """Test _create_smtp_connection context manager."""
    mock_config = MagicMock()
    mock_config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpass",
        "use_tls": True,
        "retry_attempts": 1,  # Reduce for testing
        "retry_delay": 0,     # No delay for testing
        "send_timeout": 10
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_conn = MagicMock()
        mock_smtp.return_value = mock_conn
        
        smtp_manager = SmtpManager(mock_config)
        
        # Test connection creation
        with smtp_manager._create_smtp_connection() as conn:
            assert conn == mock_conn
        
        # Should call SMTP with correct parameters
        mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=10)
        # Should call starttls for TLS connection
        mock_conn.starttls.assert_called_once()
        # Should login with credentials
        mock_conn.login.assert_called_once_with("testuser", "testpass")
        # Should quit connection when done
        mock_conn.quit.assert_called_once()


def test_create_smtp_connection_failure():
    """Test _create_smtp_connection context manager with failure."""
    mock_config = MagicMock()
    mock_config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpass",
        "use_tls": True,
        "retry_attempts": 1,  # Reduce for testing
        "retry_delay": 0,     # No delay for testing
        "send_timeout": 10
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        # Make SMTP connection fail
        mock_smtp.side_effect = Exception("Connection failed")
        
        smtp_manager = SmtpManager(mock_config)
        
        # Should raise exception when connection fails
        with pytest.raises(Exception, match="Connection failed"):
            with smtp_manager._create_smtp_connection() as conn:
                pass


def test_send_email():
    """Test send_email method."""
    mock_config = MagicMock()
    mock_config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpass",
        "use_tls": True,
        "retry_attempts": 1,
        "retry_delay": 0,
        "send_timeout": 10
    }
    mock_config.email_config = {
        "sender": "Test Sender <test@example.com>"
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_conn = MagicMock()
        mock_smtp.return_value = mock_conn
        
        smtp_manager = SmtpManager(mock_config)
        
        # Test sending email
        smtp_manager.send_email(
            to_email="recipient@example.com",
            subject="Test Subject",
            content="<html><body><h1>Test</h1></body></html>",
            is_html=True
        )
        
        # Should create SMTP connection
        mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=10)
        # Should send message
        mock_conn.send_message.assert_called_once()


def test_send_email_with_smtp_error():
    """Test send_email method with SMTP error."""
    mock_config = MagicMock()
    mock_config.smtp_config = {
        "host": "smtp.test.com",
        "port": 587,
        "username": "testuser",
        "password": "testpass",
        "use_tls": True,
        "retry_attempts": 1,
        "retry_delay": 0,
        "send_timeout": 10
    }
    mock_config.email_config = {
        "sender": "Test Sender <test@example.com>"
    }
    
    with patch('smtplib.SMTP') as mock_smtp:
        mock_conn = MagicMock()
        mock_smtp.return_value = mock_conn
        # Make send_message fail
        mock_conn.send_message.side_effect = Exception("Send failed")
        
        smtp_manager = SmtpManager(mock_config)
        
        # Should raise exception when send fails
        with pytest.raises(Exception, match="Send failed"):
            smtp_manager.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                content="<html><body><h1>Test</h1></body></html>",
                is_html=True
            )


if __name__ == "__main__":
    pytest.main([__file__])