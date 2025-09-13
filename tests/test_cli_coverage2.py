"""Additional tests for CLI module to improve coverage."""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from email_sender.cli import (
    get_menu_style, 
    _ensure_or_create_default_config,
    _ensure_valid_sender
)
from pathlib import Path


def test_get_menu_style():
    """Test get_menu_style function."""
    style = get_menu_style()
    assert style is not None
    # Should return a Style object
    from prompt_toolkit.styles import Style
    assert isinstance(style, Style)


def test_ensure_or_create_default_config():
    """Test _ensure_or_create_default_config function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
            config_path, content_path = _ensure_or_create_default_config()
            
            # Should create config directory structure
            assert config_path.exists()
            assert content_path.exists()
            
            # Should create config files
            config_dir = Path(tmpdir) / "config"
            templates_dir = config_dir / "templates"
            data_dir = Path(tmpdir) / "data"
            
            assert config_dir.exists()
            assert templates_dir.exists()
            assert data_dir.exists()
            
            # Should create .env file
            env_path = Path(tmpdir) / ".env"
            assert env_path.exists()


def test_ensure_valid_sender_with_empty_config():
    """Test _ensure_valid_sender with empty config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("email:\n  sender: ''\n", encoding="utf-8")
        
        with patch('typer.prompt', return_value="Test Sender <test@example.com>"):
            _ensure_valid_sender(config_path)
            
            # Should update the config file with sender
            content = config_path.read_text(encoding="utf-8")
            assert "test@example.com" in content


def test_ensure_valid_sender_with_invalid_input():
    """Test _ensure_valid_sender with invalid input."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("email:\n  sender: ''\n", encoding="utf-8")
        
        with patch('typer.prompt', return_value="invalid-email"):
            _ensure_valid_sender(config_path)
            
            # Should not update config with invalid email
            content = config_path.read_text(encoding="utf-8")
            assert "invalid-email" not in content


def test_ensure_valid_sender_with_existing_sender():
    """Test _ensure_valid_sender with existing sender."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("email:\n  sender: 'Existing Sender <existing@example.com>'\n", encoding="utf-8")
        
        # Should not prompt when sender already exists
        with patch('typer.prompt') as mock_prompt:
            _ensure_valid_sender(config_path)
            # Should not call prompt
            mock_prompt.assert_not_called()


def test_ensure_valid_sender_env_override():
    """Test _ensure_valid_sender with EMAIL_SENDER environment variable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_path.write_text("email:\n  sender: ''\n", encoding="utf-8")
        
        with patch.dict(os.environ, {"EMAIL_SENDER": "Env Sender <env@example.com>"}, clear=False):
            with patch('typer.prompt') as mock_prompt:
                _ensure_valid_sender(config_path)
                # Should not call prompt when EMAIL_SENDER is set
                mock_prompt.assert_not_called()
                
                # Should update config with environment sender
                content = config_path.read_text(encoding="utf-8")
                assert "env@example.com" in content


if __name__ == "__main__":
    pytest.main([__file__])