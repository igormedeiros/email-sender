"""Additional tests for template processor to improve coverage."""

import pytest
from unittest.mock import patch, MagicMock
from email_sender.email_templating import TemplateProcessor
from pathlib import Path
import tempfile


def test_template_processor_initialization():
    """Test TemplateProcessor initialization with different config formats."""
    # Test with dict config
    config_dict = {
        "email": {"template_path": "templates/email.html"},
        "evento": {
            "nome": "Test Event",
            "link": "https://test.com",
            "data": "2023-01-01",
            "cidade": "Test City",
            "local": "Test Location"
        },
        "urls": {
            "unsubscribe": "https://test.com/unsubscribe",
            "subscribe": "https://test.com/subscribe"
        }
    }
    processor = TemplateProcessor(config_dict)
    assert isinstance(processor.content_config, dict)
    
    # Test with object that has content_config attribute
    class FakeConfig:
        def __init__(self):
            self.content_config = config_dict
    
    processor2 = TemplateProcessor(FakeConfig())
    assert isinstance(processor2.content_config, dict)


def test_template_processor_replace_placeholders():
    """Test _replace_placeholders method."""
    config_dict = {
        "email": {"template_path": "templates/email.html"},
        "evento": {
            "nome": "Test Event",
            "link": "https://test.com",
            "data": "2023-01-01",
            "cidade": "Test City",
            "local": "Test Location"
        },
        "urls": {
            "unsubscribe": "https://test.com/unsubscribe",
            "subscribe": "https://test.com/subscribe"
        }
    }
    
    processor = TemplateProcessor(config_dict)
    
    # Test with simple HTML content
    html_content = "<html><body><h1>Hello {name}</h1><p>Email: {email}</p></body></html>"
    recipient = {"name": "John Doe", "email": "john@example.com"}
    urls_config = {
        "unsubscribe": "https://test.com/unsubscribe",
        "subscribe": "https://test.com/subscribe"
    }
    
    result = processor._replace_placeholders(html_content, recipient, urls_config)
    
    # Check that placeholders were replaced
    assert "John Doe" in result
    assert "john@example.com" in result
    # Note: The URLs are handled separately in the process method, not in _replace_placeholders


def test_template_processor_process():
    """Test process method."""
    config_dict = {
        "email": {"template_path": "templates/email.html"},
        "evento": {
            "nome": "Test Event",
            "link": "https://test.com",
            "data": "2023-01-01",
            "cidade": "Test City",
            "local": "Test Location"
        }
    }
    
    processor = TemplateProcessor(config_dict)
    
    # Create a temporary HTML template
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body><h1>Hello {name}</h1><p>Email: {email}</p></body></html>")
        template_path = Path(f.name)
    
    try:
        recipient = {"name": "John Doe", "email": "john@example.com"}
        result = processor.process(template_path, recipient)
        
        # Check that the result contains the expected content
        assert "Hello John Doe" in result
        assert "Email: john@example.com" in result
        assert "<html>" in result
        assert "</html>" in result
    finally:
        # Clean up the temporary file
        template_path.unlink()


def test_template_processor_complex_placeholders():
    """Test processing with complex placeholders."""
    config_dict = {
        "email": {"template_path": "templates/email.html"},
        "evento": {
            "nome": "Test Event",
            "link": "https://test.com?param=value",
            "data": "2023-01-01",
            "cidade": "Test City",
            "local": "Test Location"
        },
        "promocao": {
            "desconto": "30%",
        }
    }
    
    processor = TemplateProcessor(config_dict)
    
    # Create a temporary HTML template with complex placeholders
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("""
        <html>
        <body>
            <h1>{evento.nome}</h1>
            <p>Date: {evento.data}</p>
            <p>Location: {evento.cidade} - {evento.local}</p>
            <p><a href="{evento.link}">Event Link</a></p>
            <p>Discount: {promocao.desconto}</p>
        </body>
        </html>
        """)
        template_path = Path(f.name)
    
    try:
        recipient = {"name": "John Doe", "email": "john@example.com"}
        result = processor.process(template_path, recipient)
        
        # Check that complex placeholders were replaced
        assert "Test Event" in result
        assert "2023-01-01" in result
        assert "Test City" in result
        assert "Test Location" in result
        assert "https://test.com?param=value" in result
        assert "30%" in result
    finally:
        # Clean up the temporary file
        template_path.unlink()


def test_template_processor_missing_config():
    """Test processing with missing configuration."""
    # Test with empty config
    processor = TemplateProcessor({})
    
    # Create a temporary HTML template
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body><h1>Hello {name}</h1></body></html>")
        template_path = Path(f.name)
    
    try:
        recipient = {"name": "John Doe"}
        result = processor.process(template_path, recipient)
        
        # Should still process basic placeholders
        assert "Hello John Doe" in result
    finally:
        # Clean up the temporary file
        template_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])