import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from src.email_service import EmailService
from src.config import Config

# Fixtures para configurar e limpar os testes
@pytest.fixture
def setup_test_env():
    """Configura o ambiente de teste e limpa no final"""
    # Criar diretórios de teste
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("tests/backup", exist_ok=True)
    
    # Cria um arquivo CSV de teste
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
    if os.path.exists("tests/backup"):
        shutil.rmtree("tests/backup")

@pytest.fixture
def email_service():
    """Cria uma instância mockada do EmailService"""
    config_mock = MagicMock(spec=Config)
    config_mock.email_config = {
        "csv_file": "tests/data/test_emails.csv",
        "unsubscribe_file": "tests/data/descadastros.csv",
        "batch_size": 10
    }
    config_mock.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "password": "password",
        "use_tls": True
    }
    config_mock.content_config = {
        "email": {
            "subject": "Test Email"
        },
        "urls": {
            "unsubscribe": "https://example.com/unsubscribe",
            "subscribe": "https://example.com/subscribe"
        }
    }
    
    return EmailService(config_mock)

# Testes para create_backup

def test_create_backup_creates_backup_directory(email_service, setup_test_env):
    """Testa se a função create_backup cria o diretório de backup se ele não existir"""
    # Remover diretório de backup se existir
    if os.path.exists("backup"):
        shutil.rmtree("backup")
    
    # Executar função
    email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar se o diretório foi criado
    assert os.path.exists("backup")

def test_create_backup_returns_correct_path(email_service, setup_test_env):
    """Testa se a função create_backup retorna o caminho correto do arquivo de backup"""
    # Executar função
    backup_path = email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar o caminho retornado
    assert backup_path == "backup/test_emails.csv.bak"

def test_create_backup_creates_file(email_service, setup_test_env):
    """Testa se a função create_backup cria o arquivo de backup"""
    # Executar função
    email_service.create_backup("tests/data/test_emails.csv")
    
    # Verificar se o arquivo foi criado
    assert os.path.exists("backup/test_emails.csv.bak")

def test_create_backup_file_content_matches_original(email_service, setup_test_env):
    """Testa se o conteúdo do arquivo de backup é igual ao original"""
    # Executar função
    email_service.create_backup("tests/data/test_emails.csv")
    
    # Ler os dois arquivos
    original_df = pd.read_csv("tests/data/test_emails.csv")
    backup_df = pd.read_csv("backup/test_emails.csv.bak")
    
    # Verificar se são iguais
    assert original_df.equals(backup_df)

def test_create_backup_raises_error_when_file_not_found(email_service, setup_test_env):
    """Testa se a função create_backup lança FileNotFoundError quando o arquivo não existe"""
    with pytest.raises(FileNotFoundError):
        email_service.create_backup("nonexistent_file.csv")

# Testes para clear_sent_flags

def test_clear_sent_flags_clears_enviado_flag(email_service, setup_test_env):
    """Testa se a função clear_sent_flags limpa a flag 'enviado'"""
    # Executar função
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar se a flag foi limpa
    df = pd.read_csv("tests/data/test_emails.csv")
    assert not df['enviado'].any()

def test_clear_sent_flags_clears_falhou_flag(email_service, setup_test_env):
    """Testa se a função clear_sent_flags limpa a flag 'falhou'"""
    # Executar função
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar se a flag foi limpa
    df = pd.read_csv("tests/data/test_emails.csv")
    assert not df['falhou'].any()

def test_clear_sent_flags_returns_correct_count(email_service, setup_test_env):
    """Testa se a função clear_sent_flags retorna o número correto de registros modificados"""
    # Executar função
    count = email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar o número retornado (2 'enviado' e 1 'falhou')
    assert count == 3

def test_clear_sent_flags_creates_backup(email_service, setup_test_env):
    """Testa se a função clear_sent_flags cria um backup do arquivo"""
    # Executar função
    email_service.clear_sent_flags("tests/data/test_emails.csv")
    
    # Verificar se o backup foi criado
    assert os.path.exists("backup/test_emails.csv.bak")

def test_clear_sent_flags_raises_error_when_file_not_found(email_service, setup_test_env):
    """Testa se a função clear_sent_flags lança FileNotFoundError quando o arquivo não existe"""
    with pytest.raises(FileNotFoundError):
        email_service.clear_sent_flags("nonexistent_file.csv")

# Testes para load_unsubscribed_emails

def test_load_unsubscribed_emails_returns_empty_list_when_file_not_found(email_service):
    """Testa se a função load_unsubscribed_emails retorna uma lista vazia quando o arquivo não existe"""
    # Executar função com um arquivo que não existe
    emails = email_service.load_unsubscribed_emails("nonexistent_file.csv")
    
    # Verificar se o resultado é uma lista vazia
    assert emails == []

def test_load_unsubscribed_emails_reads_csv_with_header(email_service, setup_test_env):
    """Testa se a função load_unsubscribed_emails lê corretamente um CSV com cabeçalho"""
    # Criar um arquivo CSV de teste com cabeçalho
    test_data = pd.DataFrame({
        'email': ['unsubscribed1@example.com', 'unsubscribed2@example.com'],
        'data_descadastro': ['2023-01-01', '2023-01-02']
    })
    test_data.to_csv("tests/data/descadastros.csv", index=False)
    
    # Executar função
    emails = email_service.load_unsubscribed_emails("tests/data/descadastros.csv")
    
    # Verificar se a lista contém os emails corretos
    assert emails == ['unsubscribed1@example.com', 'unsubscribed2@example.com']

def test_load_unsubscribed_emails_handles_case_insensitive(email_service, setup_test_env):
    """Testa se a função load_unsubscribed_emails converte emails para lowercase"""
    # Criar um arquivo CSV de teste com emails em diferentes casos
    test_data = pd.DataFrame({
        'email': ['UPPER@example.com', 'lower@example.com', 'Mixed@Example.com'],
        'data_descadastro': ['2023-01-01', '2023-01-02', '2023-01-03']
    })
    test_data.to_csv("tests/data/descadastros.csv", index=False)
    
    # Executar função
    emails = email_service.load_unsubscribed_emails("tests/data/descadastros.csv")
    
    # Verificar se todos os emails estão em lowercase
    assert all(email == email.lower() for email in emails)

def test_load_unsubscribed_emails_without_header(email_service, setup_test_env):
    """Testa se a função load_unsubscribed_emails lê a primeira coluna quando não há cabeçalho 'email'"""
    # Criar um arquivo CSV sem o cabeçalho 'email'
    with open("tests/data/descadastros.csv", 'w', encoding='utf-8') as f:
        f.write("col1,col2\n")
        f.write("unsubscribed1@example.com,data1\n")
        f.write("unsubscribed2@example.com,data2\n")
    
    # Executar função
    emails = email_service.load_unsubscribed_emails("tests/data/descadastros.csv")
    
    # Verificar se a lista contém os emails corretos
    assert emails == ['unsubscribed1@example.com', 'unsubscribed2@example.com']

@patch('pandas.read_csv')
def test_load_unsubscribed_emails_handles_csv_error(mock_read_csv, email_service, setup_test_env):
    """Testa se a função load_unsubscribed_emails trata erros ao ler o CSV"""
    # Configurar o mock para lançar uma exceção
    mock_read_csv.side_effect = Exception("CSV error")
    
    # Criar um arquivo de texto simples
    with open("tests/data/descadastros.csv", 'w', encoding='utf-8') as f:
        f.write("unsubscribed1@example.com\n")
        f.write("unsubscribed2@example.com\n")
    
    # Executar função
    emails = email_service.load_unsubscribed_emails("tests/data/descadastros.csv")
    
    # Verificar se a função tentou ler como texto simples
    assert emails == ['unsubscribed1@example.com', 'unsubscribed2@example.com']

# Testes para register_failed_email

def test_register_failed_email_creates_directory(email_service):
    """Testa se a função register_failed_email cria o diretório se não existir"""
    # Remover diretório se existir
    if os.path.exists("tests/data/failed"):
        shutil.rmtree("tests/data/failed")
    
    # Executar função
    email_service.register_failed_email("failed@example.com", "Test reason", "tests/data/failed/emails.csv")
    
    # Verificar se o diretório foi criado
    assert os.path.exists("tests/data/failed")

def test_register_failed_email_creates_file_with_header(email_service, setup_test_env):
    """Testa se a função register_failed_email cria o arquivo com cabeçalho quando não existe"""
    file_path = "tests/data/failed_emails.csv"
    
    # Remover arquivo se existir
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função
    email_service.register_failed_email("failed@example.com", "Test reason", file_path)
    
    # Verificar se o arquivo foi criado e tem o cabeçalho correto
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        assert first_line == "email;data;motivo"

def test_register_failed_email_adds_entry(email_service, setup_test_env):
    """Testa se a função register_failed_email adiciona a entrada corretamente"""
    file_path = "tests/data/failed_emails.csv"
    
    # Remover arquivo se existir
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função
    email_service.register_failed_email("failed@example.com", "Test reason", file_path)
    
    # Verificar se a entrada foi adicionada
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        assert len(lines) == 2  # Cabeçalho + entrada
        assert "failed@example.com" in lines[1]
        assert "Test reason" in lines[1]

def test_register_failed_email_uses_default_reason(email_service, setup_test_env):
    """Testa se a função register_failed_email usa a razão padrão quando não fornecida"""
    file_path = "tests/data/failed_emails.csv"
    
    # Remover arquivo se existir
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Executar função sem fornecer razão
    email_service.register_failed_email("failed@example.com", file_path=file_path)
    
    # Verificar se a razão padrão foi usada
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        assert "Falha no envio" in lines[1] 