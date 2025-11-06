"""
Testes unitários para o módulo CLI.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.email_sender.cli import app


class TestCli:
    """Testes para a interface de linha de comando."""

    @pytest.fixture
    def runner(self):
        """Fixture para CliRunner."""
        return CliRunner()

    def test_cli_help(self, runner):
        """Testa comando help."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "Treineinsite • Email Sender CLI" in result.output
        assert "1 - Enviar emails" in result.output
        assert "2 - Testar SMTP" in result.output
        assert "3 - Ver contatos" in result.output
        assert "4 - Importar contatos (CSV)" in result.output
        assert "5 - Sair" in result.output

    @patch('src.email_sender.cli.EmailService')
    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_send_emails_interactive_test_mode(self, mock_print, mock_input, mock_config_class,
                                                   mock_smtp_class, mock_db_class, mock_service_class, runner):
        """Testa envio de emails no modo interativo (teste)."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()
        mock_smtp = MagicMock()
        mock_service = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp
        mock_service_class.return_value = mock_service

        # Mock do resultado do serviço
        mock_service.send_batch.return_value = {
            "total": 5,
            "sent": 4,
            "failed": 1,
            "duplicates": 0,
            "blocked": 0,
            "time_seconds": 2.5,
            "batches_processed": 1
        }

        # Simular entrada do usuário: escolher opção 1 (enviar), depois 'test', depois 's' para confirmar
        mock_input.side_effect = ["1", "test", "s"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que o serviço foi chamado
        mock_service.send_batch.assert_called_once_with(message_id=None, dry_run=False)

        # Verificar que prints foram feitos
        mock_print.assert_called()

    @patch('src.email_sender.cli.EmailService')
    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_send_emails_interactive_production_mode(self, mock_print, mock_input, mock_config_class,
                                                         mock_smtp_class, mock_db_class, mock_service_class, runner):
        """Testa envio de emails no modo interativo (produção)."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()
        mock_smtp = MagicMock()
        mock_service = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp
        mock_service_class.return_value = mock_service

        # Mock do resultado do serviço
        mock_service.send_batch.return_value = {
            "total": 10,
            "sent": 9,
            "failed": 1,
            "duplicates": 0,
            "blocked": 0,
            "time_seconds": 5.0,
            "batches_processed": 2
        }

        # Simular entrada do usuário: escolher opção 1 (enviar), depois 'production', depois 's' para confirmar
        mock_input.side_effect = ["1", "production", "s"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que o serviço foi chamado
        mock_service.send_batch.assert_called_once_with(message_id=None, dry_run=False)

    @patch('src.email_sender.cli.EmailService')
    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_send_emails_cancel_operation(self, mock_print, mock_input, mock_config_class,
                                              mock_smtp_class, mock_db_class, mock_service_class, runner):
        """Testa cancelamento da operação de envio."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()
        mock_smtp = MagicMock()
        mock_service = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp
        mock_service_class.return_value = mock_service

        # Simular entrada do usuário: escolher opção 1 (enviar), depois 'test', depois 'n' para cancelar
        mock_input.side_effect = ["1", "test", "n"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que o serviço NÃO foi chamado
        mock_service.send_batch.assert_not_called()

    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_test_smtp_success(self, mock_print, mock_config_class, mock_smtp_class, runner):
        """Testa comando de teste SMTP bem-sucedido."""
        # Mock das classes
        mock_config = MagicMock()
        mock_smtp = MagicMock()

        mock_config_class.return_value = mock_config
        mock_smtp_class.return_value = mock_smtp

        # Mock do teste SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        # Executar comando
        result = runner.invoke(app, ["test-smtp"])

        assert result.exit_code == 0

        # Verificar que o SMTP foi testado
        mock_smtp.send_email.assert_called_once()

    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_test_smtp_failure(self, mock_print, mock_config_class, mock_smtp_class, runner):
        """Testa comando de teste SMTP com falha."""
        # Mock das classes
        mock_config = MagicMock()
        mock_smtp = MagicMock()

        mock_config_class.return_value = mock_config
        mock_smtp_class.return_value = mock_smtp

        # Mock do teste SMTP com falha
        mock_smtp.send_email.return_value = False

        # Executar comando
        result = runner.invoke(app, ["test-smtp"])

        assert result.exit_code == 1  # Deve sair com erro

        # Verificar que o SMTP foi testado
        mock_smtp.send_email.assert_called_once()

    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_check_contacts(self, mock_print, mock_config_class, mock_db_class, runner):
        """Testa comando de verificação de contatos."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db

        # Mock dos contatos
        mock_contacts = [
            {"id": 1, "email": "user1@test.com", "unsubscribed": False},
            {"id": 2, "email": "user2@test.com", "unsubscribed": True},
        ]
        mock_db.fetch_all.return_value = mock_contacts

        # Executar comando
        result = runner.invoke(app, ["check-contacts"])

        assert result.exit_code == 0

        # Verificar que a query foi executada
        mock_db.fetch_all.assert_called_once()

    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_check_db(self, mock_print, mock_config_class, mock_db_class, runner):
        """Testa comando de verificação de banco de dados."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db

        # Mock da verificação do banco
        mock_db.fetch_one.return_value = {"version": "PostgreSQL 15.0"}

        # Executar comando
        result = runner.invoke(app, ["check-db"])

        assert result.exit_code == 0

        # Verificar que a query foi executada
        mock_db.fetch_one.assert_called_once()

    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_exit_option(self, mock_print, mock_input, runner):
        """Testa opção de sair do menu."""
        # Simular entrada do usuário: escolher opção 5 (sair)
        mock_input.side_effect = ["5"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que prints foram feitos
        mock_print.assert_called()

    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_invalid_option(self, mock_print, mock_input, runner):
        """Testa opção inválida no menu."""
        # Simular entrada do usuário: escolher opção inválida, depois 5 para sair
        mock_input.side_effect = ["99", "5"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que prints foram feitos (incluindo mensagem de erro)
        mock_print.assert_called()

    @patch('src.email_sender.cli.EmailService')
    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.SmtpManager')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_cli_send_emails_with_message_id(self, mock_print, mock_input, mock_config_class,
                                             mock_smtp_class, mock_db_class, mock_service_class, runner):
        """Testa envio de emails com ID de mensagem específico."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()
        mock_smtp = MagicMock()
        mock_service = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp
        mock_service_class.return_value = mock_service

        # Mock do resultado do serviço
        mock_service.send_batch.return_value = {
            "total": 3,
            "sent": 3,
            "failed": 0,
            "duplicates": 0,
            "blocked": 0,
            "time_seconds": 1.5,
            "batches_processed": 1
        }

        # Simular entrada do usuário: escolher opção 1 (enviar), depois 'test', depois 's' para confirmar
        mock_input.side_effect = ["1", "test", "s"]

        # Executar CLI
        result = runner.invoke(app, [])

        assert result.exit_code == 0

        # Verificar que o serviço foi chamado com message_id=None (padrão)
        mock_service.send_batch.assert_called_once_with(message_id=None, dry_run=False)

    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_error_handling(self, mock_print, mock_config_class, runner):
        """Testa tratamento de erros na CLI."""
        # Mock da configuração lançando erro
        mock_config_class.side_effect = Exception("Configuration error")

        # Executar comando que usa configuração
        result = runner.invoke(app, ["check-db"])

        assert result.exit_code == 1  # Deve sair com erro

        # Verificar que erro foi tratado
        mock_print.assert_called()

    @patch('src.email_sender.cli.Database')
    @patch('src.email_sender.cli.Config')
    @patch('builtins.print')
    def test_cli_database_connection_error(self, mock_print, mock_config_class, mock_db_class, runner):
        """Testa erro de conexão com banco de dados."""
        # Mock das classes
        mock_config = MagicMock()
        mock_db = MagicMock()

        mock_config_class.return_value = mock_config
        mock_db_class.return_value = mock_db

        # Mock de erro na conexão
        mock_db.fetch_one.side_effect = Exception("Connection failed")

        # Executar comando
        result = runner.invoke(app, ["check-db"])

        assert result.exit_code == 1  # Deve sair com erro

        # Verificar que erro foi tratado
        mock_print.assert_called()
