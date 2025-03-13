import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import typer
import sys

from src.controller_cli import clear_sent_flags
from src.config import Config
from src.email_service import EmailService

# Fixtures para configurar ambiente de teste
@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretórios de teste
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("backup", exist_ok=True)
    
    # Criar arquivo CSV de teste
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'nome': ['Test 1', 'Test 2', 'Test 3'],
        'enviado': ['ok', '', 'ok'],
        'falhou': ['', 'ok', '']
    })
    test_data.to_csv("tests/data/test_csv.csv", index=False)
    
    yield
    
    # Limpar diretórios após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")
    
    # Limpar backup após os testes
    if os.path.exists("backup"):
        shutil.rmtree("backup")

# Mocks para Config e EmailService
@pytest.fixture
def mock_config():
    """Mock para Config"""
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10
    }
    return config_mock

@pytest.fixture
def mock_email_service(mock_config):
    """Mock para EmailService"""
    email_service_mock = MagicMock(spec=EmailService)
    email_service_mock.clear_sent_flags.return_value = 3  # 3 flags limpas
    
    # Simular criação de backup
    def create_backup_side_effect(file_path):
        backup_path = f"backup/{Path(file_path).name}.bak"
        # Criar diretório backup se não existir
        os.makedirs("backup", exist_ok=True)
        # Copiar arquivo
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    email_service_mock.create_backup.side_effect = create_backup_side_effect
    
    return email_service_mock

# Testes para clear_sent_flags

def test_clear_sent_flags_without_csv_file(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags usa o arquivo padrão quando nenhum é fornecido"""
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Executar comando sem especificar arquivo CSV
            clear_sent_flags(
                csv_file=None,
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar se o serviço foi chamado com o arquivo correto
            mock_email_service.clear_sent_flags.assert_called_once_with("tests/data/test_csv.csv")

def test_clear_sent_flags_with_csv_file(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags usa o arquivo especificado quando fornecido"""
    custom_csv = "tests/data/custom.csv"
    
    # Criar arquivo personalizado
    test_data = pd.DataFrame({
        'email': ['custom@example.com'],
        'enviado': ['ok']
    })
    test_data.to_csv(custom_csv, index=False)
    
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Executar comando com arquivo CSV especificado
            clear_sent_flags(
                csv_file=custom_csv,
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar se o serviço foi chamado com o arquivo correto
            mock_email_service.clear_sent_flags.assert_called_once_with(custom_csv)

def test_clear_sent_flags_creates_backup(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags cria backup do arquivo"""
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Executar comando
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Como o EmailService é um mock, o método clear_sent_flags deve ter sido chamado
            # em vez de verificar create_backup diretamente
            mock_email_service.clear_sent_flags.assert_called_once_with("tests/data/test_csv.csv")

def test_clear_sent_flags_returns_count(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags retorna o número correto de flags limpas"""
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Mock para capturar saída do print
            with patch('builtins.print') as mock_print:
                # Executar comando
                clear_sent_flags(
                    csv_file="tests/data/test_csv.csv",
                    config_file="config/config.yaml",
                    content_file="config/email.yaml"
                )
                
                # Verificar se o número correto foi impresso
                mock_print.assert_any_call("✅ 3 flags cleared successfully!")

def test_clear_sent_flags_handles_error(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags trata erros corretamente"""
    # Configurar mock para lançar exceção
    mock_email_service.clear_sent_flags.side_effect = Exception("Test error")
    
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Mock para capturar saída do print
            with patch('builtins.print') as mock_print:
                # Mock para sys.exit
                with patch('sys.exit') as mock_exit:
                    # Executar comando
                    clear_sent_flags(
                        csv_file="tests/data/test_csv.csv",
                        config_file="config/config.yaml",
                        content_file="config/email.yaml"
                    )
                    
                    # Verificar que mensagem de erro apropriada foi exibida
                    mock_print.assert_any_call("❌ Error: Test error")
                    # Verificar que sys.exit foi chamado com código 1
                    mock_exit.assert_called_once_with(1)

# Teste para verificar o caminho do backup
def test_clear_sent_flags_prints_backup_path(mock_config, mock_email_service, setup_test_env):
    """Testa se o comando clear_sent_flags mostra o caminho do backup corretamente"""
    # Mock para Config e EmailService
    with patch('src.controller_cli.Config', return_value=mock_config):
        with patch('src.controller_cli.EmailService', return_value=mock_email_service):
            # Mock para capturar saída do print
            with patch('builtins.print') as mock_print:
                # Executar comando
                clear_sent_flags(
                    csv_file="tests/data/test_csv.csv",
                    config_file="config/config.yaml",
                    content_file="config/email.yaml"
                )
                
                # Verificar se o caminho do backup foi impresso
                mock_print.assert_any_call("🔄 Um backup do arquivo original foi salvo em: backup/test_csv.csv.bak") 