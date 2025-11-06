"""
Testes unitários para o módulo utils/ui.
"""
from unittest.mock import patch

import pytest

from src.email_sender.utils.ui import get_console, print_banner


class TestUI:
    """Testes para as funções de UI."""

    def test_get_console(self):
        """Testa função get_console."""
        console = get_console()
        assert console is not None
        # Deve retornar a mesma instância
        console2 = get_console()
        assert console is console2

    @pytest.fixture
    def mock_console(self):
        """Fixture para console mockado."""
        with patch('src.email_sender.utils.ui.get_console') as mock_get_console:
            mock_console = mock_get_console.return_value
            yield mock_console

    def test_print_banner(self, mock_console):
        """Testa função print_banner."""
        ascii_art = "TREINEINSITE"
        subtitle = "Email Sender"

        print_banner(ascii_art, subtitle)

        # Deve ter chamado print múltiplas vezes
        assert mock_console.print.call_count >= 3

    def test_print_banner_no_subtitle(self, mock_console):
        """Testa função print_banner sem subtítulo."""
        ascii_art = "TREINEINSITE"

        print_banner(ascii_art)

        # Deve ter chamado print para o banner
        assert mock_console.print.call_count >= 2
