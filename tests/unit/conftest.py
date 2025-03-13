import pytest
import os
import pandas as pd
import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path

@pytest.fixture
def setup_test_env(tmp_path):
    """Configura ambiente temporário para testes"""
    # Criar diretórios temporários para testes
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "templates").mkdir(exist_ok=True)
    (tmp_path / "backup").mkdir(exist_ok=True)
    (tmp_path / "reports").mkdir(exist_ok=True)
    
    # Criar arquivo de emails de teste
    test_emails = pd.DataFrame({
        "email": ["test1@example.com", "test2@example.com"],
        "nome": ["Test 1", "Test 2"],
        "enviado": ["", ""],
        "falhou": ["", ""],
        "data_envio": [None, None],
        "erro": ["", ""]
    })
    
    test_emails.to_csv(tmp_path / "data" / "test_emails.csv", index=False)
    
    # Criar arquivo de unsubscribe de teste
    unsubscribe = pd.DataFrame({
        "email": ["unsub@example.com"],
        "data": [datetime.datetime.now().strftime("%Y-%m-%d")]
    })
    
    unsubscribe.to_csv(tmp_path / "data" / "descadastros.csv", index=False)
    
    # Criar template de teste
    template_content = "<html><body>Olá {{ nome }}, seu email é {{ email }}</body></html>"
    template_path = tmp_path / "templates" / "test.html"
    template_path.write_text(template_content)
    
    # Patch temporário para usar o diretório temporário em os.path.exists
    with patch('os.path.exists', side_effect=lambda path: Path(tmp_path / path).exists() or os.path.exists(path)):
        yield tmp_path

@pytest.fixture
def mock_config():
    """Cria mock de configuração para testes"""
    mock_conf = MagicMock()
    
    # Configurar valores para os atributos mais usados
    mock_conf.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "password": "password123",
        "use_tls": True,
        "retry_attempts": 3,
        "retry_delay": 1,
        "send_timeout": 10
    }
    
    mock_conf.email_config = {
        "smtp": mock_conf.smtp_config,
        "sender": "Test Sender <test@example.com>",
        "reply_to": "no-reply@example.com",
        "default_title": "Test Email",
        "batch_size": 10,
        "csv_file": "data/emails.csv",
        "unsubscribe_file": "data/descadastros.csv"
    }
    
    mock_conf.content_config = {
        "email": {"subject": "Test Email"},
        "urls": {
            "unsubscribe": "https://example.com/unsubscribe?email={email}",
            "subscribe": "https://example.com/subscribe"
        }
    }
    
    mock_conf.DEFAULT_CSV_PATH = "data/emails.csv"
    mock_conf.DEFAULT_UNSUBSCRIBE_PATH = "data/descadastros.csv"
    mock_conf.TEMPLATE_DIR = "templates"
    
    return mock_conf 