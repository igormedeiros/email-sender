import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import time

from email_service import EmailService
from config import Config

@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa ao final"""
    # Criar diretórios necessários
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("backup", exist_ok=True)
    
    # Criar arquivo CSV de teste
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'nome': ['Test 1', 'Test 2', 'Test 3'],
        'enviado': ['ok', '', 'ok'],
        'falhou': ['', 'ok', '']
    })
    test_data.to_csv("tests/data/test_emails.csv", index=False)
    
    yield
    
    # Limpar diretórios após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")
    
    # Limpar backup após os testes
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

# Testes para a funcionalidade de backup no método clear_sent_flags

@pytest.mark.backup
def test_clear_sent_flags_creates_backup_directory(email_service, setup_test_env):
    """Testa se o método clear_sent_flags cria o diretório de backup se não existir"""
    # Remover diretório de backup se existir
    if os.path.exists("backup"):
        shutil.rmtree("backup")
    
    # Verificar que diretório não existe
    assert not os.path.exists("backup")
    
    # Executar método
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que diretório foi criado
    assert os.path.exists("backup")
    assert os.path.exists("backup/test_emails.csv.bak")

@pytest.mark.backup
def test_clear_sent_flags_backup_is_exact_copy(email_service, setup_test_env):
    """Testa se o backup criado é uma cópia exata do arquivo original"""
    # Ler conteúdo original
    original_df = pd.read_csv("tests/data/test_emails.csv")
    
    # Executar método
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que backup existe
    assert os.path.exists("backup/test_emails.csv.bak")
    
    # Ler conteúdo do backup
    backup_df = pd.read_csv("backup/test_emails.csv.bak")
    
    # Verificar que conteúdo é idêntico
    pd.testing.assert_frame_equal(original_df, backup_df)

@pytest.mark.backup
def test_clear_sent_flags_replaces_existing_backup(email_service, setup_test_env):
    """Testa se o método clear_sent_flags substitui um backup existente"""
    # Criar backup inicial
    os.makedirs("backup", exist_ok=True)

    # Criar um backup com conteúdo diferente
    initial_backup_df = pd.DataFrame({
        'email': ['old1@example.com', 'old2@example.com'],
        'nome': ['Old 1', 'Old 2'],
        'enviado': ['ok', 'ok']
    })
    initial_backup_df.to_csv("backup/test_emails.csv.bak", index=False)

    # Registrar o conteúdo do backup inicial
    with open("backup/test_emails.csv.bak", "r") as f:
        initial_content = f.read()

    # Forçar um delay e então alterar o tempo de criação manualmente para garantir que seja diferente
    time.sleep(1.5)
    
    # Criar o arquivo CSV original com dados diferentes do backup
    test_df = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'nome': ['Test 1', 'Test 2'],
        'enviado': ['', '']
    })
    test_df.to_csv("tests/data/test_emails.csv", index=False)

    # Executar método
    email_service.clear_sent_flags("tests/data/test_emails.csv")

    # Verificar que o backup foi substituído (conteúdo diferente)
    with open("backup/test_emails.csv.bak", "r") as f:
        new_content = f.read()
    
    # Verificar que o conteúdo do backup é diferente do inicial
    assert new_content != initial_content, "O conteúdo do backup deve ter sido alterado"
    
    # Verificar que o novo backup reflete o conteúdo do arquivo original
    backup_df = pd.read_csv("backup/test_emails.csv.bak")
    assert len(backup_df) == 2
    assert 'test1@example.com' in backup_df['email'].values
    assert 'test2@example.com' in backup_df['email'].values

@pytest.mark.backup
def test_clear_sent_flags_keeps_only_one_backup(email_service, setup_test_env):
    """Testa se apenas um arquivo de backup é mantido ao chamar clear_sent_flags múltiplas vezes"""
    # Executar método pela primeira vez
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que backup existe
    assert os.path.exists("backup/test_emails.csv.bak")
    
    # Executar método novamente
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que apenas um arquivo de backup existe
    backup_files = [f for f in os.listdir("backup") if f.startswith("test_emails.csv")]
    assert len(backup_files) == 1, f"Apenas um arquivo de backup deveria existir, encontrados: {backup_files}"

@pytest.mark.backup
def test_clear_sent_flags_backup_maintains_metadata(email_service, setup_test_env):
    """Testa se o backup mantém os metadados do arquivo original (permissões)"""
    # Definir permissões específicas para o arquivo original
    os.chmod("tests/data/test_emails.csv", 0o644)
    original_mode = os.stat("tests/data/test_emails.csv").st_mode & 0o777
    
    # Executar método
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que o backup mantém as mesmas permissões
    backup_mode = os.stat("backup/test_emails.csv.bak").st_mode & 0o777
    assert backup_mode == original_mode, f"Permissões originais: {oct(original_mode)}, permissões do backup: {oct(backup_mode)}"

@pytest.mark.backup
def test_clear_sent_flags_handles_special_characters(email_service, setup_test_env):
    """Testa se o método clear_sent_flags lida corretamente com nomes de arquivo contendo caracteres especiais"""
    # Criar arquivo com caracteres especiais
    special_filename = "tests/data/arquivo-#especial!.csv"
    
    # Copiar arquivo de teste para o novo nome
    shutil.copy2("tests/data/test_emails.csv", special_filename)
    
    # Executar método
    email_service.clear_sent_flags(special_filename)
    
    # Verificar que backup existe com nome correto
    expected_backup = "backup/arquivo-#especial!.csv.bak"
    assert os.path.exists(expected_backup), f"Backup não encontrado: {expected_backup}"

@pytest.mark.backup
def test_clear_sent_flags_modifies_original_file(email_service, setup_test_env):
    """Testa se o método clear_sent_flags modifica corretamente o arquivo original"""
    # Executar método
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que o arquivo original foi modificado
    modified_df = pd.read_csv("tests/data/test_emails.csv")
    
    # Verificar que as flags foram limpas
    assert not modified_df['enviado'].any()
    assert not modified_df['falhou'].any()

@pytest.mark.backup
def test_clear_sent_flags_return_value(email_service, setup_test_env):
    """Testa se o método clear_sent_flags retorna o número correto de registros modificados"""
    # Executar método
    count = email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar que o número retornado é correto (2 registros 'enviado'=ok e 1 registro 'falhou'=ok)
    assert count == 3

@pytest.mark.backup
def test_clear_sent_flags_with_empty_file(email_service, setup_test_env):
    """Testa se o método clear_sent_flags lida corretamente com arquivos vazios"""
    # Criar arquivo CSV vazio
    empty_file = "tests/data/empty.csv"
    pd.DataFrame(columns=['email', 'nome', 'enviado', 'falhou']).to_csv(empty_file, index=False)
    
    # Executar método
    count = email_service.clear_sent_flags(empty_file)
    
    # Verificar que o número retornado é zero
    assert count == 0
    
    # Verificar que backup foi criado
    assert os.path.exists("backup/empty.csv.bak")

@pytest.mark.backup
def test_clear_sent_flags_recovers_from_error(email_service, setup_test_env):
    """Testa a recuperação após um erro durante o processamento"""
    # Criar um CSV válido
    valid_file = "tests/data/valid.csv"
    test_data = pd.DataFrame({
        'email': ['test1@example.com', 'test2@example.com'],
        'enviado': ['ok', 'ok']
    })
    test_data.to_csv(valid_file, index=False)
    
    # Criar um backup do arquivo
    email_service.create_backup(valid_file)
    
    # Verificar que o backup existe
    assert os.path.exists("backup/valid.csv.bak")
    
    # Tentar limpar um arquivo inexistente deve lançar FileNotFoundError
    with pytest.raises(FileNotFoundError):
        email_service.clear_sent_flags("nonexistent_file.csv")
    
    # Verificar que o backup anterior permanece intacto
    assert os.path.exists("backup/valid.csv.bak") 