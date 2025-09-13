"""Additional tests for CLI module to improve coverage."""

import os
import pytest
from unittest.mock import patch, MagicMock
from email_sender.cli import (
    _ensure_or_create_default_config, 
    _self_test, 
    _update_event_from_sympla,
    _ensure_valid_sender
)
import tempfile
from pathlib import Path


def test_ensure_or_create_default_config():
    """Test _ensure_or_create_default_config function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
            config_path, content_path = _ensure_or_create_default_config()
            
            # Check that config files were created
            assert config_path.exists()
            assert content_path.exists()
            
            # Check that .env file was created
            env_path = Path(tmpdir) / ".env"
            assert env_path.exists()


def test_self_test_function():
    """Test _self_test function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
            # Create config files first
            config_dir = Path(tmpdir) / "config"
            config_dir.mkdir()
            (config_dir / "config.yaml").write_text("smtp:\n  host: smtp.test.com\n  port: 587\nemail:\n  test_recipient: test@example.com\n", encoding="utf-8")
            (config_dir / "email.yaml").write_text("email:\n  template_path: templates/email.html\n", encoding="utf-8")
            templates_dir = config_dir / "templates"
            templates_dir.mkdir()
            (templates_dir / "email.html").write_text("<html><body>Test</body></html>", encoding="utf-8")
            
            with patch.dict(os.environ, {'ENVIRONMENT': 'test'}, clear=True), \
                 patch('socket.getaddrinfo') as mock_socket, \
                 patch('psycopg.connect') as mock_psycopg:
                
                # Mock socket and database connections
                mock_socket.return_value = None
                mock_psycopg_instance = MagicMock()
                mock_psycopg.return_value = mock_psycopg_instance
                
                # Should not raise any exceptions
                _self_test()


def test_ensure_valid_sender_with_existing_sender():
    """Test _ensure_valid_sender function with existing sender."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("email:\n  sender: \"Test Sender <test@example.com>\"\n", encoding="utf-8")
        
        # Should not prompt when sender already exists
        _ensure_valid_sender(config_path)
        
        # Config should remain unchanged
        content = config_path.read_text(encoding="utf-8")
        assert "Test Sender <test@example.com>" in content


if __name__ == "__main__":
    pytest.main([__file__])