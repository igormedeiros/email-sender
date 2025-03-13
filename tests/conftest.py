import pytest
import os
import shutil
import pandas as pd
from unittest.mock import MagicMock
from pathlib import Path

from config import Config

@pytest.fixture(scope="session", autouse=True)
def setup_test_directories():
    """
    Configuração global dos diretórios de teste.
    Esta fixture é executada automaticamente uma vez por sessão de teste.
    """
    # Criar diretórios necessários
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("tests/backup", exist_ok=True)
    os.makedirs("backup", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    
    yield
    
    # Limpar diretórios após todos os testes
    for dir_path in ["tests/data", "tests/backup", "backup", "reports"]:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
            except Exception as e:
                print(f"Erro ao limpar diretório {dir_path}: {e}")

@pytest.fixture
def mock_config():
    """
    Cria uma instância mock da classe Config para testes.
    """
    config_mock = MagicMock(spec=Config)
    
    # Configurações de email
    config_mock.email_config = {
        "csv_file": "tests/data/test_emails.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10,
        "test_recipient": "test@example.com"
    }
    
    # Configurações SMTP
    config_mock.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "password": "password",
        "use_tls": True,
        "send_timeout": 10,
        "retry_attempts": 3,
        "retry_delay": 5
    }
    
    # Configurações de conteúdo
    config_mock.content_config = {
        "email": {
            "subject": "Test Email"
        },
        "urls": {
            "unsubscribe": "https://example.com/unsubscribe",
            "subscribe": "https://example.com/subscribe"
        },
        "evento": {
            "link": "https://example.com/evento",
            "data": "01/01/2023",
            "cidade": "Test City",
            "local": "Test Location"
        }
    }
    
    return config_mock

@pytest.fixture
def test_csv_file():
    """
    Cria um arquivo CSV de teste para os testes.
    """
    file_path = "tests/data/test_emails.csv"
    
    # Criar dados de teste
    data = {
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'nome': ['Test 1', 'Test 2', 'Test 3'],
        'enviado': ['ok', '', 'ok'],
        'falhou': ['', 'ok', ''],
        'descadastro': ['', '', '']
    }
    
    # Criar DataFrame e salvar como CSV
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    
    return file_path 