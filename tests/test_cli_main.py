"""Tests for the main CLI function."""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from email_sender.cli import main


def test_cli_main_function_with_env_option():
    """Test CLI main function with environment option."""
    # Test that main function can be called with env option
    with patch('email_sender.cli.print_banner'), \
         patch('email_sender.cli._run_interactive_menu') as mock_menu, \
         patch.dict(os.environ, {'ENVIRONMENT': 'test'}, clear=True):
        
        # Mock the menu to return "Sair" immediately
        mock_menu.return_value = ("test", "Sair")
        
        # Should not raise any exceptions
        result = main(env="test")
        assert result == 0


def test_cli_main_function_without_env_option():
    """Test CLI main function without environment option."""
    # Test that main function can be called without env option
    with patch('email_sender.cli.print_banner'), \
         patch('email_sender.cli._run_interactive_menu') as mock_menu, \
         patch.dict(os.environ, {'ENVIRONMENT': 'test'}, clear=True):
        
        # Mock the menu to return "Sair" immediately
        mock_menu.return_value = ("test", "Sair")
        
        # Should not raise any exceptions
        result = main()
        assert result == 0


def test_cli_main_function_with_production_env():
    """Test CLI main function with production environment."""
    # Test that main function can be called with production env
    with patch('email_sender.cli.print_banner'), \
         patch('email_sender.cli._run_interactive_menu') as mock_menu, \
         patch.dict(os.environ, {'ENVIRONMENT': 'production'}, clear=True):
        
        # Mock the menu to return "Sair" immediately
        mock_menu.return_value = ("production", "Sair")
        
        # Should not raise any exceptions
        result = main(env="production")
        assert result == 0