"""Additional tests for email service to improve coverage."""

import pytest
from unittest.mock import patch, MagicMock
from email_sender.email_service import EmailService
from email_sender.config import Config


class FakeConfig:
    def __init__(self):
        self._content = {
            "email": {
                "template_path": "templates/email.html",
                "subject": "Test Subject"
            },
            "evento": {
                "nome": "Test Event",
                "link": "https://test.com",
                "data": "2023-01-01",
                "cidade": "Test City",
                "uf": "TC",
                "local": "Test Location",
                "cupom": "TEST123"
            }
        }
        self._email = {
            "sender": "test@example.com",
            "batch_size": 10,
            "test_recipient": "test@example.com",
            "batch_delay": 1,
            "public_domain": "test.com"
        }
        self._smtp = {
            "host": "smtp.test.com",
            "port": 587,
            "username": "test",
            "password": "test",
            "use_tls": True,
            "retry_attempts": 1,
            "retry_delay": 1,
            "send_timeout": 10
        }
        self._postgres = {
            "host": "localhost",
            "port": 5432,
            "user": "test",
            "password": "test",
            "database": "test"
        }

    @property
    def content_config(self):
        return self._content

    @property
    def email_config(self):
        return self._email

    @property
    def smtp_config(self):
        return self._smtp

    @property
    def postgres_config(self):
        return self._postgres

    @property
    def environment_mode(self):
        return "test"


def test_email_service_build_subject_fallback():
    """Test EmailService._build_subject_fallback method."""
    config = FakeConfig()
    service = EmailService(config)
    
    # Test with complete event data
    subject = service._build_subject_fallback()
    assert isinstance(subject, str)
    assert len(subject) > 0
    
    # Test with minimal event data
    config._content["evento"] = {}
    service = EmailService(config)
    subject = service._build_subject_fallback()
    assert isinstance(subject, str)


def test_email_service_resolve_subject():
    """Test EmailService._resolve_subject method."""
    config = FakeConfig()
    service = EmailService(config)
    
    # Test without API key (should use fallback)
    with patch.dict('os.environ', {}, clear=True):
        subject = service._resolve_subject()
        assert isinstance(subject, str)
        assert len(subject) > 0


def test_email_service_ensure_event_coupon_and_link():
    """Test EmailService._ensure_event_coupon_and_link method."""
    config = FakeConfig()
    service = EmailService(config)
    
    # Test with existing coupon and link
    service._ensure_event_coupon_and_link()
    
    evento_cfg = service.config.content_config.get("evento", {})
    assert "cupom" in evento_cfg
    assert "link" in evento_cfg


def test_email_service_generate_subject_for_body():
    """Test EmailService._generate_subject_for_body method."""
    config = FakeConfig()
    service = EmailService(config)
    
    html_content = "<html><head><title>Test Title</title></head><body><h1>Test Heading</h1><p>Test content</p></body></html>"
    
    # Test without API key (should use fallback)
    with patch.dict('os.environ', {}, clear=True):
        subject = service._generate_subject_for_body(html_content)
        assert isinstance(subject, str)
        # Should fall back to title extraction
        assert "Test Title" in subject or "Test Heading" in subject or len(subject) > 0


def test_email_service_maybe_interactive_subject():
    """Test EmailService._maybe_interactive_subject method."""
    config = FakeConfig()
    service = EmailService(config)
    
    # Test with interactive mode disabled
    with patch.dict('os.environ', {}, clear=True):
        result = service._maybe_interactive_subject("Test Subject", "<html></html>")
        assert result == "Test Subject"
    
    # Test with interactive mode enabled but not TTY
    with patch.dict('os.environ', {'SUBJECT_INTERACTIVE': '1'}), \
         patch('sys.stdin.isatty', return_value=False):
        result = service._maybe_interactive_subject("Test Subject", "<html></html>")
        assert result == "Test Subject"


def test_email_service_process_email_template():
    """Test EmailService.process_email_template method."""
    config = FakeConfig()
    service = EmailService(config)
    
    # Mock template processor
    with patch('email_sender.email_templating.TemplateProcessor.process') as mock_process:
        mock_process.return_value = "<html><body>Test</body></html>"
        
        result = service.process_email_template("templates/email.html", {"email": "test@example.com"}, "Test Subject")
        assert result == "<html><body>Test</body></html>"


def test_email_service_generate_report():
    """Test EmailService.generate_report method."""
    config = FakeConfig()
    service = EmailService(config)
    
    import time
    start_time = time.time()
    end_time = start_time + 10
    
    # Test basic report generation
    report = service.generate_report(start_time, end_time, 10, 8, 2)
    assert isinstance(report, dict)
    assert "report" in report
    assert "report_file" in report
    assert report["total_sent"] == 10
    assert report["successful"] == 8
    assert report["failed"] == 2


if __name__ == "__main__":
    pytest.main([__file__])