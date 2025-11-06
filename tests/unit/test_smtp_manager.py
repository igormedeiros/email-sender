"""
Testes unitários para o módulo SMTP manager.
"""
import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.email_sender.config import Config
from src.email_sender.smtp_manager import SmtpManager


class TestSmtpManager:
    """Testes para a classe SmtpManager."""

    def test_smtp_manager_initialization(self, mock_config):
        """Testa inicialização do SmtpManager."""
        smtp_config = {
            "host": "smtp.test.com",
            "port": 587,
            "user": "test@test.com",
            "password": "test_pass",
            "use_tls": True,
            "retry_attempts": 2,
            "retry_delay": 5,
            "send_timeout": 10
        }

        manager = SmtpManager(mock_config)

        assert manager.config == mock_config
        assert manager._smtp_config == smtp_config

    @patch('smtplib.SMTP')
    def test_smtp_connect_success(self, mock_smtp_class, mock_config):
        """Testa conexão SMTP bem-sucedida."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        with manager.connect() as smtp:
            assert smtp == mock_smtp

        # Verifica que os métodos foram chamados corretamente
        mock_smtp_class.assert_called_once_with("smtp.test.com", 587, timeout=10)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("test@test.com", "test_pass")

    @patch('smtplib.SMTP')
    def test_smtp_connect_no_tls(self, mock_smtp_class, mock_config):
        """Testa conexão SMTP sem TLS."""
        # Modificar config para não usar TLS
        with patch.object(mock_config, 'get_smtp_config') as mock_get_config:
            mock_get_config.return_value = {
                "host": "smtp.test.com",
                "port": 587,
                "user": "test@test.com",
                "password": "test_pass",
                "use_tls": False,
                "retry_attempts": 2,
                "retry_delay": 5,
                "send_timeout": 10
            }

            mock_smtp = MagicMock()
            mock_smtp_class.return_value = mock_smtp

            manager = SmtpManager(mock_config)

            with manager.connect() as smtp:
                assert smtp == mock_smtp

            # Verifica que starttls NÃO foi chamado
            mock_smtp.starttls.assert_not_called()
            mock_smtp.login.assert_called_once_with("test@test.com", "test_pass")

    @patch('smtplib.SMTP')
    def test_smtp_connect_error(self, mock_smtp_class, mock_config):
        """Testa erro na conexão SMTP."""
        mock_smtp_class.side_effect = smtplib.SMTPConnectError(421, "Service not available")

        manager = SmtpManager(mock_config)

        with pytest.raises(smtplib.SMTPConnectError):
            with manager.connect():
                pass

    @patch('smtplib.SMTP')
    def test_smtp_send_email_success(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de email bem-sucedido."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        result = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient=sample_email_data["recipient"]
        )

        assert result is True

        # Verifica que sendmail foi chamado
        mock_smtp.sendmail.assert_called_once()
        call_args = mock_smtp.sendmail.call_args
        assert call_args[0][0] == sample_email_data["sender"]
        assert sample_email_data["recipient"] in call_args[0][1]
        assert "Subject:" in call_args[0][2]
        assert sample_email_data["subject"] in call_args[0][2]
        assert sample_email_data["html_body"] in call_args[0][2]

    @patch('smtplib.SMTP')
    def test_smtp_send_email_with_retry(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de email com retry após falha temporária."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        # Simula falha temporária na primeira tentativa
        mock_smtp.sendmail.side_effect = [
            smtplib.SMTPServerDisconnected("Connection lost"),
            None  # Sucesso na segunda tentativa
        ]

        manager = SmtpManager(mock_config)

        result = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient=sample_email_data["recipient"]
        )

        assert result is True

        # Verifica que sendmail foi chamado 2 vezes (retry)
        assert mock_smtp.sendmail.call_count == 2

    @patch('smtplib.SMTP')
    def test_smtp_send_email_max_retries_exceeded(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de email quando máximo de retries é excedido."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        # Sempre falha
        mock_smtp.sendmail.side_effect = smtplib.SMTPServerDisconnected("Connection lost")

        manager = SmtpManager(mock_config)

        result = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient=sample_email_data["recipient"]
        )

        assert result is False

        # Verifica que sendmail foi chamado 3 vezes (2 retries + 1 tentativa inicial)
        assert mock_smtp.sendmail.call_count == 3

    @patch('smtplib.SMTP')
    def test_smtp_send_email_permanent_error(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de email com erro permanente (sem retry)."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        # Erro permanente (não deve tentar retry)
        mock_smtp.sendmail.side_effect = smtplib.SMTPRecipientsRefused({"user@test.com": (550, "User unknown")})

        manager = SmtpManager(mock_config)

        result = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient=sample_email_data["recipient"]
        )

        assert result is False

        # Verifica que sendmail foi chamado apenas 1 vez (sem retry para erro permanente)
        assert mock_smtp.sendmail.call_count == 1

    @patch('smtplib.SMTP')
    def test_smtp_send_email_invalid_recipient(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de email com destinatário inválido."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        # Email inválido
        result = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient="invalid-email"
        )

        assert result is False

        # sendmail não deve ser chamado para email inválido
        mock_smtp.sendmail.assert_not_called()

    @patch('smtplib.SMTP')
    def test_smtp_send_email_empty_content(self, mock_smtp_class, mock_config):
        """Testa envio de email com conteúdo vazio."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        result = manager.send_email(
            subject="",
            html_body="",
            sender="test@test.com",
            recipient="recipient@test.com"
        )

        assert result is False

        # sendmail não deve ser chamado para conteúdo vazio
        mock_smtp.sendmail.assert_not_called()

    @patch('smtplib.SMTP')
    def test_smtp_context_manager_cleanup(self, mock_smtp_class, mock_config):
        """Testa que o context manager faz cleanup adequado."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        with manager.connect() as smtp:
            pass

        # Verifica que quit foi chamado
        mock_smtp.quit.assert_called_once()

    @patch('smtplib.SMTP')
    def test_smtp_multiple_emails_same_connection(self, mock_smtp_class, mock_config, sample_email_data):
        """Testa envio de múltiplos emails na mesma conexão."""
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        manager = SmtpManager(mock_config)

        # Enviar dois emails
        result1 = manager.send_email(
            subject=sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient="recipient1@test.com"
        )

        result2 = manager.send_email(
            subject="Second " + sample_email_data["subject"],
            html_body=sample_email_data["html_body"],
            sender=sample_email_data["sender"],
            recipient="recipient2@test.com"
        )

        assert result1 is True
        assert result2 is True

        # Verifica que sendmail foi chamado 2 vezes
        assert mock_smtp.sendmail.call_count == 2

    def test_smtp_config_validation(self, mock_config):
        """Testa validação da configuração SMTP."""
        # Configuração válida
        manager = SmtpManager(mock_config)
        assert manager._smtp_config is not None

        # Configuração sem host
        with patch.object(mock_config, 'get_smtp_config') as mock_get_config:
            mock_get_config.return_value = {
                "port": 587,
                "user": "test@test.com",
                "password": "test_pass",
                "use_tls": True
            }

            manager = SmtpManager(mock_config)
            # Deve funcionar mesmo sem host (usa valor padrão ou None)
            assert manager._smtp_config["port"] == 587
