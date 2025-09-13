import pytest
from email_sender.tracking import EmailTracker, TrackingUrlValidator, extract_tracking_params


def test_email_tracker_inject_tracking_pixel():
    """Test that EmailTracker correctly injects tracking pixel."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test with HTML that has body tag
    html_content = "<html><body><h1>Hello</h1></body></html>"
    result = tracker.inject_tracking_pixel(html_content, 123, 456)
    
    # Should contain the tracking pixel
    assert "api.example.com/api/tracking/open" in result
    assert "contact_id=123" in result
    assert "message_id=456" in result
    # Should be injected before closing body tag
    assert "<h1>Hello</h1><img" in result


def test_email_tracker_inject_tracking_pixel_without_body():
    """Test that EmailTracker injects tracking pixel even without body tag."""
    tracker = EmailTracker("https://api.example.com")
    
    # Test with HTML that has no body tag
    html_content = "<html><h1>Hello</h1></html>"
    result = tracker.inject_tracking_pixel(html_content, 123, 456)
    
    # Should contain the tracking pixel
    assert "api.example.com/api/tracking/open" in result
    assert "contact_id=123" in result
    assert "message_id=456" in result
    # Should be appended to the end
    assert "<img" in result


def test_email_tracker_process_email_for_tracking():
    """Test that EmailTracker processes email for tracking."""
    tracker = EmailTracker("https://api.example.com")
    
    html_content = "<html><body><h1>Hello</h1></body></html>"
    result = tracker.process_email_for_tracking(html_content, 123, 456)
    
    # Should contain the tracking pixel
    assert "api.example.com/api/tracking/open" in result
    assert "contact_id=123" in result
    assert "message_id=456" in result


def test_tracking_url_validator_with_allowed_domains():
    """Test TrackingUrlValidator with specific allowed domains."""
    validator = TrackingUrlValidator(["example.com", "test.com"])
    
    # Should allow URLs from allowed domains
    assert validator.is_safe_url("https://example.com/page")
    assert validator.is_safe_url("https://subdomain.test.com/page")
    # Note: localhost is not automatically allowed when allowed_domains is specified
    
    # Should reject URLs from other domains
    assert not validator.is_safe_url("https://malicious.com/page")
    assert not validator.is_safe_url("ftp://example.com/page")


def test_tracking_url_validator_without_allowed_domains():
    """Test TrackingUrlValidator without specific allowed domains."""
    validator = TrackingUrlValidator()
    
    # Should allow HTTPS URLs
    assert validator.is_safe_url("https://example.com/page")
    
    # Should allow HTTP for localhost
    assert validator.is_safe_url("http://localhost/page")
    assert validator.is_safe_url("http://127.0.0.1/page")
    
    # Should reject HTTP for other domains
    assert not validator.is_safe_url("http://example.com/page")
    
    # Should reject invalid schemes
    assert not validator.is_safe_url("ftp://example.com/page")


def test_extract_tracking_params():
    """Test that extract_tracking_params correctly extracts and validates parameters."""
    query_params = {
        "contact_id": "123",
        "message_id": "456",
        "url": "https://example.com/page"
    }
    
    result = extract_tracking_params(query_params)
    
    # Should extract valid parameters
    assert result["contact_id"] == 123
    assert result["message_id"] == 456
    assert result["url"] == "https://example.com/page"


def test_extract_tracking_params_with_invalid_values():
    """Test that extract_tracking_params handles invalid parameter values."""
    query_params = {
        "contact_id": "invalid",
        "message_id": "456",
        "url": "https://example.com/page"
    }
    
    result = extract_tracking_params(query_params)
    
    # Should skip invalid contact_id
    assert "contact_id" not in result
    # Should still extract valid parameters
    assert result["message_id"] == 456
    assert result["url"] == "https://example.com/page"


def test_extract_tracking_params_with_missing_params():
    """Test that extract_tracking_params handles missing parameters."""
    query_params = {
        "contact_id": "123"
        # Missing message_id and url
    }
    
    result = extract_tracking_params(query_params)
    
    # Should extract only valid parameters
    assert result["contact_id"] == 123
    assert "message_id" not in result
    assert "url" not in result


def test_tracking_url_validator_with_malformed_url():
    """Test that TrackingUrlValidator handles malformed URLs gracefully."""
    validator = TrackingUrlValidator()
    
    # Should reject malformed URLs
    assert not validator.is_safe_url("not-a-url")
    assert not validator.is_safe_url("")
    assert not validator.is_safe_url(None)


def test_email_tracker_with_complex_html():
    """Test that EmailTracker handles complex HTML correctly."""
    tracker = EmailTracker("https://api.example.com")
    
    # Complex HTML with multiple tags
    html_content = """
    <html>
        <head>
            <title>Test</title>
        </head>
        <body>
            <h1>Welcome</h1>
            <p>This is a <strong>test</strong> email.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </body>
    </html>
    """
    
    result = tracker.inject_tracking_pixel(html_content, 123, 456)
    
    # Should contain the tracking pixel
    assert "api.example.com/api/tracking/open" in result
    assert "contact_id=123" in result
    assert "message_id=456" in result
    # Should preserve the original content
    assert "<h1>Welcome</h1>" in result
    assert "<p>This is a <strong>test</strong> email.</p>" in result


def test_tracking_url_validator_case_insensitive():
    """Test that TrackingUrlValidator handles domain matching case-insensitively."""
    validator = TrackingUrlValidator(["EXAMPLE.COM"])
    
    # Should match regardless of case
    assert validator.is_safe_url("https://example.com/page")
    assert validator.is_safe_url("https://EXAMPLE.COM/page")
    assert validator.is_safe_url("https://ExAmPlE.CoM/page")