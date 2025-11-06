"""
Configurações compartilhadas para testes unitários.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from src.email_sender.config import Config
from src.email_sender.db import Database
from src.email_sender.smtp_manager import SmtpManager


@pytest.fixture
def temp_dir():
    """Diretório temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Dados de configuração de exemplo."""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db"
        },
        "smtp": {
            "host": "smtp.test.com",
            "port": 587,
            "username": "test@test.com",
            "password": "test_password",
            "use_tls": True,
            "retry_attempts": 2,
            "retry_delay": 5,
            "send_timeout": 10
        },
        "email": {
            "sender": "Test Sender <test@test.com>",
            "batch_size": 200,
            "batch_delay": 5,
            "test_recipient": "test@example.com"
        }
    }


@pytest.fixture
def mock_config(sample_config_data, temp_dir):
    """Mock de configuração."""
    # Criar arquivo de config temporário
    config_file = temp_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config_data, f)

    # Criar arquivo de email temporário
    email_file = temp_dir / "email.yaml"
    email_data = {
        "email": {
            "subject": "Test Subject"
        }
    }
    with open(email_file, 'w') as f:
        yaml.dump(email_data, f)

    # Retornar config carregada
    return Config(str(config_file), str(email_file))


@pytest.fixture
def mock_db():
    """Mock do banco de dados."""
    db = MagicMock(spec=Database)
    db.fetch_all.return_value = [
        {"id": 1, "email": "test1@example.com"},
        {"id": 2, "email": "test2@example.com"}
    ]
    db.fetch_one.return_value = None  # Por padrão, não encontrou
    db.execute.return_value = None
    return db


@pytest.fixture
def mock_smtp():
    """Mock do gerenciador SMTP."""
    smtp = MagicMock(spec=SmtpManager)
    smtp.send_email.return_value = None
    smtp.connect.return_value = None
    return smtp


@pytest.fixture
def sample_email_data():
    """Dados de exemplo para emails."""
    return {
        "id": 1,
        "email": "test@example.com",
        "name": "Test User"
    }


@pytest.fixture
def mock_db_connection():
    """Mock de conexão de banco de dados."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=None)
    return mock_conn, mock_cursor


@pytest.fixture
def mock_smtp_connection():
    """Mock de conexão SMTP."""
    mock_smtp = MagicMock()
    mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
    mock_smtp.__exit__ = MagicMock(return_value=None)
    return mock_smtp


@pytest.fixture
def sample_email_data():
    """Dados de email de exemplo."""
    return {
        "subject": "Test Subject",
        "html_body": "<h1>Test Email</h1>",
        "sender": "Test Sender <test@test.com>",
        "recipient": "recipient@test.com"
    }


@pytest.fixture
def sample_contact_data():
    """Dados de contato de exemplo."""
    return {
        "id": 1,
        "email": "test@example.com",
        "unsubscribed": False,
        "is_buyer": False
    }


@pytest.fixture
def sample_message_data():
    """Dados de mensagem de exemplo."""
    return {
        "id": 1,
        "subject": "Test Message",
        "html_body": "<p>Test content</p>",
        "created_at": "2025-01-01T00:00:00Z"
    }
