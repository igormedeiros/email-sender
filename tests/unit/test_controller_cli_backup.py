import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import typer
import time

from controller_cli import clear_sent_flags
from config import Config
from email_service import EmailService

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

# Fixture para real EmailService
@pytest.fixture
def email_service():
    """Cria uma instância real de EmailService para testes de integração"""
    config = MagicMock(spec=Config)
    config.email_config = {
        "csv_file": "tests/data/test_csv.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10
    }
    return EmailService(config)

# Testes para funcionalidade de backup

@pytest.mark.backup
def test_backup_creates_only_one_backup_file(setup_test_env):
    """Testa se ao chamar clear_sent_flags múltiplas vezes, apenas um arquivo de backup é mantido"""
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Executar comando duas vezes em sequência
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar que arquivo de backup foi criado
            assert os.path.exists("backup/test_csv.csv.bak")
            backup_created_time = os.path.getmtime("backup/test_csv.csv.bak")
            
            # Alterar o arquivo original para garantir um backup diferente
            test_df = pd.read_csv("tests/data/test_csv.csv")
            # Modificar algum valor para forçar um backup diferente
            if 'enviado' in test_df.columns:
                # Definir todos como 'ok' para forçar uma mudança
                test_df['enviado'] = 'ok'
                test_df.to_csv("tests/data/test_csv.csv", index=False)

            # Esperar um pouco para garantir timestamp diferente
            time.sleep(1.5)
            
            # Executar novamente
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar que ainda existe apenas um arquivo de backup com tempo de criação diferente
            backup_files = [f for f in os.listdir("backup") if f.startswith("test_csv.csv")]
            assert len(backup_files) == 1, f"Deve haver apenas um arquivo de backup, encontrado: {backup_files}"
            
            # Verificar que o tempo do arquivo foi atualizado (é um novo backup)
            new_backup_time = os.path.getmtime("backup/test_csv.csv.bak")
            assert new_backup_time > backup_created_time, "Um novo backup deve ter sido criado"

@pytest.mark.backup
def test_backup_content_matches_original(setup_test_env):
    """Testa se o conteúdo do backup é exatamente o mesmo do arquivo original antes da modificação"""
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Ler conteúdo original do CSV
    original_df = pd.read_csv("tests/data/test_csv.csv")
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Executar comando
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar que arquivo de backup foi criado
            assert os.path.exists("backup/test_csv.csv.bak")
            
            # Ler conteúdo do backup
            backup_df = pd.read_csv("backup/test_csv.csv.bak")
            
            # Verificar se o conteúdo do backup é igual ao original
            pd.testing.assert_frame_equal(original_df, backup_df)
            
            # Verificar que o arquivo original foi modificado (não é igual ao backup)
            modified_df = pd.read_csv("tests/data/test_csv.csv")
            assert not modified_df.equals(backup_df), "O arquivo original deve ser diferente do backup após modificação"

@pytest.mark.backup
def test_backup_directory_is_created_if_not_exists(setup_test_env):
    """Testa se o diretório de backup é criado automaticamente se não existir"""
    # Remover diretório de backup se existir
    if os.path.exists("backup"):
        shutil.rmtree("backup")
    
    # Verificar que o diretório de backup não existe
    assert not os.path.exists("backup")
    
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Executar comando
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar que o diretório de backup foi criado
            assert os.path.exists("backup")
            
            # Verificar que arquivo de backup foi criado
            assert os.path.exists("backup/test_csv.csv.bak")

@pytest.mark.backup
def test_clear_sent_flags_handles_file_not_found(setup_test_env):
    """Testa se o comando clear_sent_flags trata corretamente o caso de arquivo não encontrado"""
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Mock para capturar saída do print
            with patch('builtins.print') as mock_print:
                # Mock para sys.exit
                with patch('sys.exit') as mock_exit:
                    # Executar comando com arquivo inexistente
                    clear_sent_flags(
                        csv_file="nonexistent_file.csv",
                        config_file="config/config.yaml",
                        content_file="config/email.yaml"
                    )
                    
                    # Verificar que mensagem de erro apropriada foi exibida
                    error_calls = [call for call in mock_print.call_args_list if "❌ Error" in str(call)]
                    assert any("não encontrado" in str(call) for call in error_calls)
                    
                    # Verificar que sys.exit foi chamado
                    mock_exit.assert_called_once_with(1)

@pytest.mark.backup
def test_backup_maintains_file_permissions(setup_test_env):
    """Testa se as permissões do arquivo original são mantidas no backup"""
    # Definir permissões específicas no arquivo original (modo 0o644)
    os.chmod("tests/data/test_csv.csv", 0o644)
    original_mode = os.stat("tests/data/test_csv.csv").st_mode & 0o777
    
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Executar comando
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Verificar que arquivo de backup foi criado
            assert os.path.exists("backup/test_csv.csv.bak")
            
            # Verificar que as permissões foram mantidas
            backup_mode = os.stat("backup/test_csv.csv.bak").st_mode & 0o777
            assert backup_mode == original_mode, f"Permissões originais: {oct(original_mode)}, permissões do backup: {oct(backup_mode)}"

@pytest.mark.backup
def test_modified_file_structure_is_valid(setup_test_env):
    """Testa se o arquivo CSV modificado mantém uma estrutura válida e pode ser lido novamente"""
    # Criar config mock
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_csv.csv"
    }
    
    # Usar EmailService real para testar a funcionalidade de backup
    email_service = EmailService(config_mock)
    
    # Mock para Config e usar EmailService real
    with patch('controller_cli.Config', return_value=config_mock):
        with patch('controller_cli.EmailService', return_value=email_service):
            # Executar comando
            clear_sent_flags(
                csv_file="tests/data/test_csv.csv",
                config_file="config/config.yaml",
                content_file="config/email.yaml"
            )
            
            # Tentar ler o arquivo modificado
            try:
                modified_df = pd.read_csv("tests/data/test_csv.csv")
                # Verificar se o DataFrame tem as colunas esperadas
                assert all(col in modified_df.columns for col in ['email', 'nome', 'enviado', 'falhou'])
                # Verificar se as flags foram limpas
                assert not modified_df['enviado'].any()
                assert not modified_df['falhou'].any()
            except Exception as e:
                pytest.fail(f"Falha ao ler ou validar o arquivo CSV modificado: {str(e)}") 