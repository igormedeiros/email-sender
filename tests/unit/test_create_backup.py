import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import tempfile
import time

from email_service import EmailService
from config import Config

@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretórios necessários
    os.makedirs("tests/data", exist_ok=True)
    
    # Criar arquivo CSV de teste
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'nome': ['Test 1', 'Test 2', 'Test 3'],
        'enviado': ['ok', '', 'ok'],
        'falhou': ['', 'ok', '']
    })
    test_data.to_csv("tests/data/test_emails.csv", index=False)
    
    # Garantir que o diretório de backup não exista
    if os.path.exists("backup"):
        shutil.rmtree("backup")
    
    yield
    
    # Limpar diretórios após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")
    
    if os.path.exists("backup"):
        shutil.rmtree("backup")

@pytest.fixture
def email_service():
    """Cria uma instância de EmailService para testes"""
    config = MagicMock(spec=Config)
    config.email_config = {
        "csv_file": "tests/data/test_emails.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10
    }
    return EmailService(config)

# Testes para a funcionalidade do método create_backup

def test_create_backup_creates_directory(email_service, setup_test_env):
    """Testa se o método create_backup cria o diretório de backup se não existir"""
    # Verificar que o diretório não existe
    assert not os.path.exists("backup")
    
    # Executar método
    email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar que o diretório foi criado
    assert os.path.exists("backup")

def test_create_backup_creates_file(email_service, setup_test_env):
    """Testa se o método create_backup cria o arquivo de backup corretamente"""
    # Executar método
    backup_path = email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar que o arquivo foi criado
    assert os.path.exists(backup_path)
    
    # Verificar que o caminho retornado é correto
    assert backup_path == "backup/test_emails.csv.bak"

def test_create_backup_preserves_content(email_service, setup_test_env):
    """Testa se o conteúdo do arquivo de backup é idêntico ao original"""
    # Ler conteúdo original
    original_df = pd.read_csv("tests/data/test_emails.csv")
    
    # Executar método
    backup_path = email_service.create_backup("tests/data/test_emails.csv")
    
    # Ler conteúdo do backup
    backup_df = pd.read_csv(backup_path)
    
    # Verificar que o conteúdo é idêntico
    pd.testing.assert_frame_equal(original_df, backup_df)

def test_create_backup_raises_error_for_nonexistent_file(email_service, setup_test_env):
    """Testa se o método lança FileNotFoundError para arquivo inexistente"""
    with pytest.raises(FileNotFoundError):
        email_service.create_backup("nonexistent_file.csv")

def test_create_backup_preserves_permissions(email_service, setup_test_env):
    """Testa se as permissões do arquivo são preservadas no backup"""
    # Definir permissões específicas
    os.chmod("tests/data/test_emails.csv", 0o644)
    original_mode = os.stat("tests/data/test_emails.csv").st_mode & 0o777
    
    # Executar método
    backup_path = email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar permissões
    backup_mode = os.stat(backup_path).st_mode & 0o777
    assert backup_mode == original_mode, f"Permissões originais: {oct(original_mode)}, permissões do backup: {oct(backup_mode)}"

def test_create_backup_preserves_timestamps(email_service, setup_test_env):
    """Testa se os timestamps do arquivo são preservados no backup (usando shutil.copy2)"""
    # Obter timestamps originais
    original_stat = os.stat("tests/data/test_emails.csv")
    
    # Executar método
    backup_path = email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar timestamps
    backup_stat = os.stat(backup_path)
    
    # Comparar timestamps (pode haver pequenas diferenças devido ao sistema de arquivos)
    # Na maioria dos sistemas, os timestamps de acesso e modificação são preservados por copy2
    assert abs(backup_stat.st_mtime - original_stat.st_mtime) < 2.0

def test_create_backup_overwrites_existing_backup(email_service, setup_test_env):
    """Testa se o método sobrescreve um backup existente"""
    # Criar diretório e backup inicial
    os.makedirs("backup", exist_ok=True)

    # Criar um backup com conteúdo diferente
    initial_backup_df = pd.DataFrame({
        'email': ['old1@example.com', 'old2@example.com'],
        'nome': ['Old 1', 'Old 2'],
        'enviado': ['ok', 'ok']
    })
    initial_backup_df.to_csv("backup/test_emails.csv.bak", index=False)

    # Capturar o conteúdo inicial do backup
    with open("backup/test_emails.csv.bak", "r") as f:
        initial_content = f.read()

    # Criar arquivo de teste com conteúdo diferente
    test_df = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'nome': ['Test 1', 'Test 2'],
        'enviado': ['', '']
    })
    os.makedirs("tests/data", exist_ok=True)
    test_df.to_csv("tests/data/test_emails.csv", index=False)

    # Executar método
    backup_path = email_service.create_backup("tests/data/test_emails.csv")

    # Verificar que o caminho retornado é o mesmo
    assert backup_path == "backup/test_emails.csv.bak"

    # Verificar que o conteúdo foi atualizado
    with open(backup_path, "r") as f:
        new_content = f.read()
    
    assert new_content != initial_content, "O conteúdo do arquivo deve ser diferente após a sobrescrita"
    
    # Verificar que o novo conteúdo corresponde ao arquivo original
    backup_df = pd.read_csv(backup_path)
    assert 'test1@example.com' in backup_df['email'].values
    assert 'test2@example.com' in backup_df['email'].values

def test_create_backup_with_deep_path(email_service, setup_test_env):
    """Testa se o método funciona com caminhos profundos"""
    # Criar estrutura de diretórios profunda
    deep_dir = "tests/data/deep/nested/structure"
    os.makedirs(deep_dir, exist_ok=True)
    
    # Copiar arquivo de teste para o diretório profundo
    deep_file = f"{deep_dir}/deep_file.csv"
    shutil.copy2("tests/data/test_emails.csv", deep_file)
    
    # Executar método
    backup_path = email_service.create_backup(deep_file)
    
    # Verificar que o backup foi criado corretamente
    assert backup_path == "backup/deep_file.csv.bak"
    assert os.path.exists(backup_path)

def test_create_backup_with_absolute_path(email_service, setup_test_env):
    """Testa se o método funciona com caminhos absolutos"""
    # Obter caminho absoluto do arquivo de teste
    abs_path = os.path.abspath("tests/data/test_emails.csv")
    
    # Executar método
    backup_path = email_service.create_backup(abs_path)
    
    # Verificar que o backup foi criado corretamente
    assert os.path.exists(backup_path)
    assert backup_path == "backup/test_emails.csv.bak"

def test_create_backup_with_special_characters(email_service, setup_test_env):
    """Testa se o método lida corretamente com nomes de arquivo contendo caracteres especiais"""
    # Criar arquivo com caracteres especiais
    special_filename = "tests/data/arquivo-#especial!.csv"
    shutil.copy2("tests/data/test_emails.csv", special_filename)
    
    # Executar método
    backup_path = email_service.create_backup(special_filename)
    
    # Verificar que o backup foi criado corretamente
    assert backup_path == "backup/arquivo-#especial!.csv.bak"
    assert os.path.exists(backup_path)

def test_create_backup_in_custom_directory(setup_test_env):
    """Testa se podemos criar backup em diretório personalizado modificando a implementação"""
    # Criar diretório personalizado
    custom_dir = "tests/custom_backup"
    os.makedirs(custom_dir, exist_ok=True)
    
    try:
        # Criar uma subclasse que modifica o diretório de backup
        class CustomBackupEmailService(EmailService):
            def create_backup(self, file_path: str) -> str:
                try:
                    # Verificar se o arquivo existe
                    if not Path(file_path).exists():
                        raise FileNotFoundError(f"Arquivo para backup não encontrado: {file_path}")
                        
                    # Usar diretório personalizado
                    backup_dir = Path(custom_dir)
                    backup_dir.mkdir(exist_ok=True)
                    
                    # Gerar nome do arquivo de backup
                    file_name = Path(file_path).name
                    backup_path = backup_dir / f"{file_name}.bak"
                    
                    # Copiar o arquivo
                    shutil.copy2(file_path, backup_path)
                    
                    return str(backup_path)
                except Exception as e:
                    raise
        
        # Criar instância do serviço personalizado
        config = MagicMock(spec=Config)
        custom_service = CustomBackupEmailService(config)
        
        # Executar método
        backup_path = custom_service.create_backup("tests/data/test_emails.csv")
        
        # Verificar que o backup foi criado no diretório personalizado
        assert backup_path == f"{custom_dir}/test_emails.csv.bak"
        assert os.path.exists(backup_path)
    
    finally:
        # Limpar diretório personalizado
        if os.path.exists(custom_dir):
            shutil.rmtree(custom_dir) 