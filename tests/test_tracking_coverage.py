"""Additional tests for tracking module to improve coverage."""

import pytest
from unittest.mock import patch, MagicMock
from email_sender.tracking import EmailTracker, TrackingUrlValidator, extract_tracking_params
from urllib.parse import urlencode


def test_email_tracker_initialization():
    """Test EmailTracker initialization."""
    tracker = EmailTracker("https://api.example.com")
    assert tracker is not None
    assert tracker.base_url == "https://api.example.com"


def test_extract_tracking_params():
    """Test extract_tracking_params function."""
    # Test with valid parameters
    params = {
        "contact_id": "123",
        "message_id": "456",
        "url": "https://example.com"
    }
    
    extracted = extract_tracking_params(params)
    assert extracted["contact_id"] == 123
    assert extracted["message_id"] == 456
    assert extracted["url"] == "https://example.com"


def test_extract_tracking_params_with_missing_params():
    """Test extract_tracking_params function with missing parameters."""
    # Test with missing parameters
    params = {
        "contact_id": "123"
        # message_id and url are missing
    }
    
    extracted = extract_tracking_params(params)
    assert extracted["contact_id"] == 123
    assert "message_id" not in extracted
    assert "url" not in extracted


def test_extract_tracking_params_with_invalid_values():
    """Test extract_tracking_params function with invalid values."""
    # Test with invalid parameter values
    params = {
        "contact_id": "invalid",
        "message_id": "0",
        "url": "https://example.com"
    }
    
    extracted = extract_tracking_params(params)
    assert "contact_id" not in extracted  # Invalid should be excluded
    assert extracted["message_id"] == 0   # Zero is valid
    assert extracted["url"] == "https://example.com"


def test_tracking_url_validator_initialization():
    """Test TrackingUrlValidator initialization."""
    # Test with allowed domains
    validator = TrackingUrlValidator(["example.com", "test.com"])
    assert validator is not None
    assert validator.allowed_domains == ["example.com", "test.com"]
    
    # Test without allowed domains
    validator2 = TrackingUrlValidator()
    assert validator2 is not None
    assert validator2.allowed_domains == []


def test_tracking_url_validator_safe_url():
    """Test TrackingUrlValidator.is_safe_url method."""
    # Test with allowed domains
    validator = TrackingUrlValidator(["example.com", "test.com"])
    
    # Test allowed domains
    assert validator.is_safe_url("https://example.com/path") is True
    assert validator.is_safe_url("https://test.com/path") is True
    assert validator.is_safe_url("https://subdomain.example.com/path") is True
    
    # Test disallowed domains
    assert validator.is_safe_url("https://malicious.com/path") is False
    assert validator.is_safe_url("https://phishing.com/path") is False
    
    # Test invalid URLs
    assert validator.is_safe_url("invalid-url") is False
    assert validator.is_safe_url("ftp://example.com") is False


def test_tracking_url_validator_safe_url_without_domains():
    """Test TrackingUrlValidator.is_safe_url method without domain restrictions."""
    # Test with no domain restrictions (should allow HTTPS)
    validator = TrackingUrlValidator()
    
    # Test HTTPS URLs (should be allowed)
    assert validator.is_safe_url("https://example.com/path") is True
    assert validator.is_safe_url("https://test.com/path") is True
    
    # Test HTTP URLs (should be allowed only for localhost)
    assert validator.is_safe_url("http://localhost/path") is True
    assert validator.is_safe_url("http://127.0.0.1/path") is True
    assert validator.is_safe_url("http://192.168.1.1/path") is True
    
    # Test disallowed HTTP URLs
    assert validator.is_safe_url("http://example.com/path") is False
    
    # Test invalid URLs
    assert validator.is_safe_url("invalid-url") is False
    assert validator.is_safe_url("ftp://example.com") is False


def test_email_tracker_inject_tracking_pixel():
    """Test EmailTracker.inject_tracking_pixel method."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test with valid parameters
    html_content = "<html><body><h1>Test Email</h1></body></html>"
    
    result = tracker.inject_tracking_pixel(html_content, 123, 456)
    
    # Should contain the tracking pixel
    assert '<img src="' in result
    assert 'contact_id=123' in result
    assert 'message_id=456' in result
    # Should preserve original content
    assert '<h1>Test Email</h1>' in result


def test_email_tracker_inject_tracking_pixel_without_body():
    """Test EmailTracker.inject_tracking_pixel method without body tag."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test with content that has no body tag
    html_content = "<html><h1>Test Email</h1></html>"
    
    result = tracker.inject_tracking_pixel(html_content, 123, 456)
    
    # Should still contain the tracking pixel
    assert '<img src="' in result
    assert 'contact_id=123' in result
    assert 'message_id=456' in result


def test_email_tracker_rewrite_links_for_tracking():
    """Test EmailTracker.rewrite_links_for_tracking method."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test that method returns original content (tracking disabled)
    html_content = "<html><body><a href='https://example.com'>Link</a></body></html>"
    result = tracker.rewrite_links_for_tracking(html_content, 123, 456)
    
    # Should return original content unchanged
    assert result == html_content


def test_email_tracker_process_email_for_tracking():
    """Test EmailTracker.process_email_for_tracking method."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test with recipient data
    html_content = "<html><body><h1>Test Email</h1></body></html>"
    
    result = tracker.process_email_for_tracking(html_content, 123, 456)
    
    # Should contain tracking information
    assert '<img src="' in result
    assert 'contact_id=123' in result
    assert 'message_id=456' in result


if __name__ == "__main__":
    pytest.main([__file__])