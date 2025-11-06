"""
Testes unitários para o módulo de serviço de email.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.email_sender.config import Config
from src.email_sender.email_service import EmailService


class TestEmailService:
    """Testes para a classe EmailService."""

    def test_email_service_initialization(self, mock_config, mock_db_connection, mock_smtp_connection):
        """Testa inicialização do EmailService."""
        mock_db, mock_cursor = mock_db_connection
        mock_smtp = mock_smtp_connection

        with patch('src.email_sender.email_service.Database') as mock_db_class, \
             patch('src.email_sender.email_service.SmtpManager') as mock_smtp_class:

            mock_db_class.return_value = mock_db
            mock_smtp_class.return_value = mock_smtp

            service = EmailService(mock_config, mock_db, mock_smtp)

            assert service.config == mock_config
            assert service.db == mock_db
            assert service.smtp == mock_smtp

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_empty_recipients(self, mock_smtp_class, mock_db_class, mock_config):
        """Testa envio em lote sem destinatários."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar lista vazia de destinatários
        mock_db.fetch_all.return_value = []

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 0
        assert result["sent"] == 0
        assert result["failed"] == 0

        # Verifica que não tentou enviar emails
        mock_smtp.send_email.assert_not_called()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_dry_run(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa envio em lote no modo dry-run."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=True)

        assert result["total"] == 1
        assert result["sent"] == 0  # Não envia no dry-run
        assert result["failed"] == 0

        # Verifica que não tentou enviar emails
        mock_smtp.send_email.assert_not_called()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_success(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa envio em lote bem-sucedido."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificações de duplicata (retornam None = não duplicado)
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        # Mock para criação de mensagem
        mock_db.execute.return_value = 1

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 1
        assert result["sent"] == 1
        assert result["failed"] == 0

        # Verifica que tentou enviar email
        mock_smtp.send_email.assert_called_once()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_duplicate_prevention(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa prevenção de duplicatas."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificação de duplicata (já foi enviado)
        mock_db.fetch_one.return_value = {"id": 1, "event_type": "sent"}

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 1
        assert result["sent"] == 0
        assert result["failed"] == 0
        assert result["duplicates"] == 1

        # Verifica que não tentou enviar email duplicado
        mock_smtp.send_email.assert_not_called()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_exclusion_filtering(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa filtragem de contatos excluídos."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificação de exclusão (contato excluído)
        mock_db.fetch_one.return_value = {
            "id": 1,
            "unsubscribed": True,
            "is_buyer": False,
            "excluded_tags": ["bounce"]
        }

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 1
        assert result["sent"] == 0
        assert result["failed"] == 0
        assert result["blocked"] == 1

        # Verifica que não tentou enviar para contato excluído
        mock_smtp.send_email.assert_not_called()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_smtp_failure(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa falha no envio SMTP."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificações de duplicata (não duplicado)
        mock_db.fetch_one.return_value = None

        # Mock para falha no envio SMTP
        mock_smtp.send_email.return_value = False

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 1
        assert result["sent"] == 0
        assert result["failed"] == 1

        # Verifica que tentou enviar email
        mock_smtp.send_email.assert_called_once()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_batch_processing(self, mock_smtp_class, mock_db_class, mock_config):
        """Testa processamento em lotes."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar múltiplos destinatários
        contacts = [
            {"id": 1, "email": "user1@test.com", "unsubscribed": False, "is_buyer": False},
            {"id": 2, "email": "user2@test.com", "unsubscribed": False, "is_buyer": False},
            {"id": 3, "email": "user3@test.com", "unsubscribed": False, "is_buyer": False},
        ]
        mock_db.fetch_all.return_value = contacts

        # Mock para verificações (não duplicado, não excluído)
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        # Configurar batch_size pequeno para testar lotes
        with patch.object(mock_config, 'get_email_config') as mock_get_config:
            mock_get_config.return_value = {
                "batch_size": 2,
                "batch_delay": 0,  # Sem delay para teste
                "sender": "test@test.com"
            }

            service = EmailService(mock_config, mock_db, mock_smtp)

            result = service.send_batch(message_id=1, dry_run=False)

            assert result["total"] == 3
            assert result["sent"] == 3
            assert result["failed"] == 0

            # Verifica que send_email foi chamado 3 vezes
            assert mock_smtp.send_email.call_count == 3

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    @patch('time.sleep')
    def test_send_batch_batch_delay(self, mock_sleep, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa delay entre lotes."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar múltiplos destinatários
        contacts = [sample_contact_data] * 3
        mock_db.fetch_all.return_value = contacts

        # Mock para verificações
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        # Configurar batch_size=1 e batch_delay=2
        with patch.object(mock_config, 'get_email_config') as mock_get_config:
            mock_get_config.return_value = {
                "batch_size": 1,
                "batch_delay": 2,
                "sender": "test@test.com"
            }

            service = EmailService(mock_config, mock_db, mock_smtp)

            result = service.send_batch(message_id=1, dry_run=False)

            assert result["total"] == 3
            assert result["sent"] == 3

            # Verifica que sleep foi chamado 2 vezes (entre lotes)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(2)

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_memory_deduplication(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa deduplicação em memória."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mesmo contato aparece duas vezes
        contacts = [sample_contact_data, sample_contact_data]
        mock_db.fetch_all.return_value = contacts

        # Mock para verificações
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 2
        assert result["sent"] == 1  # Apenas um envio devido à deduplicação
        assert result["duplicates"] == 1

        # Verifica que send_email foi chamado apenas 1 vez
        assert mock_smtp.send_email.call_count == 1

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_template_processing(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa processamento de templates."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificações
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        service = EmailService(mock_config, mock_db, mock_smtp)

        # Template com placeholders
        template = "Olá {{name}}, seu email é {{email}}"
        expected_body = "Olá John, seu email é test@example.com"

        with patch('src.email_sender.email_service.process_email_template') as mock_process:
            mock_process.return_value = expected_body

            result = service.send_batch(message_id=1, dry_run=False)

            assert result["sent"] == 1

            # Verifica que o template foi processado
            mock_process.assert_called_once()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_error_handling(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa tratamento de erros durante o processamento."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para erro na verificação de duplicata
        mock_db.fetch_one.side_effect = Exception("Database error")

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        assert result["total"] == 1
        assert result["sent"] == 0
        assert result["failed"] == 1

        # Verifica que tentou enviar mesmo com erro na verificação
        mock_smtp.send_email.assert_called_once()

    @patch('src.email_sender.email_service.Database')
    @patch('src.email_sender.email_service.SmtpManager')
    def test_send_batch_logging_and_reporting(self, mock_smtp_class, mock_db_class, mock_config, sample_contact_data):
        """Testa logging e geração de relatórios."""
        mock_db = MagicMock()
        mock_smtp = MagicMock()

        mock_db_class.return_value = mock_db
        mock_smtp_class.return_value = mock_smtp

        # Mock para retornar destinatários
        mock_db.fetch_all.return_value = [sample_contact_data]

        # Mock para verificações
        mock_db.fetch_one.return_value = None

        # Mock para envio SMTP bem-sucedido
        mock_smtp.send_email.return_value = True

        service = EmailService(mock_config, mock_db, mock_smtp)

        result = service.send_batch(message_id=1, dry_run=False)

        # Verifica estrutura do resultado
        assert "total" in result
        assert "sent" in result
        assert "failed" in result
        assert "duplicates" in result
        assert "blocked" in result
        assert "time_seconds" in result
        assert "batches_processed" in result

        assert result["total"] == 1
        assert result["sent"] == 1
        assert result["failed"] == 0
        assert result["duplicates"] == 0
        assert result["blocked"] == 0
        assert result["batches_processed"] == 1
        assert isinstance(result["time_seconds"], float)
