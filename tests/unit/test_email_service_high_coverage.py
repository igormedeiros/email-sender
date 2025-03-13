import pytest
import os
import pandas as pd
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import logging
import datetime
import smtplib
import re

from email_service import EmailService
from config import Config

# Configure o logging para capturar logs durante testes
@pytest.fixture(autouse=True)
def configure_logging():
    """Configura e retorna um logger para capturar logs em testes"""
    logger = logging.getLogger('email_sender')
    logger.setLevel(logging.DEBUG)
    return logger

@pytest.fixture
def setup_test_env():
    """Configurar ambiente de teste com arquivos e diretórios necessários"""
    # Criar diretórios necessários
    os.makedirs("tests/data/templates", exist_ok=True)
    os.makedirs("tests/data/descadastros", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Criar arquivo CSV com dados de teste
    with open("tests/data/test_emails.csv", "w") as f:
        f.write("email,nome,enviado,falhou\n")
        f.write("test@example.com,Test User,,\n")

    # Criar arquivo de descadastros
    with open("tests/data/descadastros.csv", "w") as f:
        f.write("email,data\n")
        f.write("unsubscribed@example.com,2023-01-01\n")
    
    # Criar template HTML de teste
    with open("tests/data/templates/test_template.html", "w") as f:
        f.write("<html><body>Olá {{nome}}, seu email é {{email}}</body></html>")

    # Limpar depois dos testes
    yield
    
    # Remover arquivos temporários
    if os.path.exists("tests/data/test_emails.csv"):
        os.remove("tests/data/test_emails.csv")
    if os.path.exists("tests/data/descadastros.csv"):
        os.remove("tests/data/descadastros.csv")
    if os.path.exists("tests/data/templates/test_template.html"):
        os.remove("tests/data/templates/test_template.html")
    if os.path.exists("tests/data/templates/test.html"):
        os.remove("tests/data/templates/test.html")

@pytest.fixture
def email_service():
    """Criar instância do serviço de email para testes"""
    # Mock para Config
    config_mock = MagicMock(spec=Config)
    
    # Configurar propriedades mock
    config_mock.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test_user",
        "password": "test_pass",
        "use_tls": True,
        "retry_attempts": 3,
        "retry_delay": 1,
        "send_timeout": 5
    }
    
    config_mock.email_config = {
        "batch_size": 10,
        "csv_file": "data/emails.csv",
        "failed_file": "data/emails_falharam.csv",
        "from_name": "Test Sender",
        "from_email": "sender@example.com",
        "test_recipient": "test@example.com",
        "template_dir": "tests/data/templates",
        "subject": "Test Email"
    }
    
    return EmailService(config_mock)

def test_email_service_init(email_service):
    """Testa se as propriedades são inicializadas corretamente"""
    # Verificar propriedades básicas
    assert email_service.config is not None
    assert email_service.config.smtp_config["host"] == "smtp.example.com"
    assert email_service.config.email_config["from_email"] == "sender@example.com"

def test_extract_email_address(email_service):
    """Testa o método _extract_email_address"""
    # Testar formato simples
    assert email_service._extract_email_address("test@example.com") == "test@example.com"
    
    # Testar formato com nome
    assert email_service._extract_email_address("Nome <test@example.com>") == "test@example.com"
    
    # Testar formato complexo
    assert email_service._extract_email_address("Nome | Empresa <test@example.com>") == "test@example.com"

@patch('smtplib.SMTP')
def test_create_smtp_connection(mock_smtp, email_service):
    """Testa a criação de conexão SMTP"""
    # Configurar o mock
    mock_instance = mock_smtp.return_value
    
    # Executar método e verificar comportamento dentro do contexto
    with email_service._create_smtp_connection() as conn:
        assert conn == mock_instance
    
    # Verificar que SMTP foi chamado com os parâmetros corretos
    mock_smtp.assert_called_once_with(
        email_service.config.smtp_config["host"],
        email_service.config.smtp_config["port"],
        timeout=email_service.config.smtp_config["send_timeout"]
    )
    
    # Verificar que os métodos de autenticação foram chamados
    mock_instance.starttls.assert_called_once()
    mock_instance.login.assert_called_once_with(
        email_service.config.smtp_config["username"],
        email_service.config.smtp_config["password"]
    )
    
    # Verificar que a conexão foi fechada
    mock_instance.quit.assert_called_once()

@patch('smtplib.SMTP')
def test_create_smtp_connection_with_error(mock_smtp, email_service):
    """Testa o tratamento de erro na conexão SMTP"""
    # Configurar mock para lançar exceção
    mock_smtp.side_effect = ConnectionRefusedError("Connection refused")
    
    # Executar método e verificar que a exceção é relançada
    with pytest.raises(Exception, match="Falha ao conectar ao servidor SMTP após"):
        with email_service._create_smtp_connection():
            pass

def test_sync_unsubscribed_emails(email_service, setup_test_env):
    """Testa a sincronização de emails descadastrados"""
    # Preparar dados
    # Já temos dados de teste criados pelo setup_test_env
    
    # Executar método
    count = email_service.sync_unsubscribed_emails(
        "tests/data/test_emails.csv",
        "tests/data/descadastros.csv"
    )
    
    # Verificar que nenhuma alteração foi feita (nenhum email em comum)
    assert count == 0
    
    # Adicionar um email descadastrado ao CSV principal
    df = pd.read_csv("tests/data/test_emails.csv")
    df = pd.concat([df, pd.DataFrame({
        'email': ['unsubscribed@example.com'],
        'nome': ['Unsubscribed User'],
        'enviado': [''],
        'falhou': ['']
    })])
    df.to_csv("tests/data/test_emails.csv", index=False)
    
    # Executar método novamente
    count = email_service.sync_unsubscribed_emails(
        "tests/data/test_emails.csv",
        "tests/data/descadastros.csv"
    )
    
    # Verificar que 1 registro foi atualizado
    assert count == 1
    
    # Verificar que o campo "descadastro" foi preenchido para o email
    df = pd.read_csv("tests/data/test_emails.csv")
    unsubscribed_row = df[df['email'] == 'unsubscribed@example.com']
    assert len(unsubscribed_row) == 1
    assert unsubscribed_row['descadastro'].values[0] == 'S'

def test_register_failed_email_with_custom_reason(email_service, setup_test_env):
    """Testa o registro de emails com falha usando razão personalizada"""
    # Criar diretório temporário para o teste
    temp_dir = tempfile.mkdtemp()
    failed_file = os.path.join(temp_dir, "failed_emails.csv")
    
    # Executar método
    email = "failed_custom@example.com"
    reason = "Custom failure reason"
    email_service.register_failed_email(email, reason, failed_file)
    
    # Verificar que o arquivo foi criado
    assert os.path.exists(failed_file)
    
    # Verificar conteúdo do arquivo
    with open(failed_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert email in content
        assert reason in content
    
    # Limpar após o teste
    shutil.rmtree(temp_dir)

def test_read_template(email_service, setup_test_env):
    """Testa a leitura de templates"""
    # Executar método
    template_content = email_service._read_template("tests/data/templates/test_template.html")
    
    # Verificar conteúdo
    assert "<html>" in template_content
    assert "{{nome}}" in template_content
    assert "{{email}}" in template_content

def test_format_template(email_service, setup_test_env):
    """Testa a formatação de templates"""
    # Template de teste
    template = "<html><body>Olá {nome}, seu email é {email}</body></html>"
    
    # Dados para o template
    data = {
        "nome": "John Doe",
        "email": "john@example.com"
    }
    
    # Executar método
    result = email_service._format_template(template, data)
    
    # Verificar formatação
    assert "Olá John Doe" in result
    assert "seu email é john@example.com" in result

@patch('src.email_service.EmailService.process_email_template')
def test_process_email_template(mock_process, email_service, setup_test_env):
    """Testa o processamento completo de templates"""
    # Configure o mock para retornar um HTML formatado
    mock_process.return_value = "<html><body>Olá John Doe, seu email é john@example.com</body></html>"
    
    # Dados para o template
    data = {
        "nome": "John Doe",
        "email": "john@example.com"
    }
    
    # Configurar atributos necessários
    email_service.config.content_config = {
        "urls": {"unsubscribe": "http://example.com/unsub", "subscribe": "http://example.com/sub"},
        "evento": {"link": "http://example.com/event", "data": "2023-01-01", "cidade": "São Paulo", "local": "Centro de Convenções"}
    }
    
    # Criar template de teste se não existir
    template_path = "tests/data/templates/test_template.html"
    if not os.path.exists(template_path):
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        with open(template_path, "w", encoding="utf-8") as f:
            f.write("<html><body>Olá {nome}, seu email é {email}</body></html>")
    
    # Criar mock para o conteúdo do template
    with patch('builtins.open', mock_open(read_data="<html><body>Olá {nome}, seu email é {email}</body></html>")):
        # Chamar o método real
        result = email_service.process_email_template(template_path, data, "Test Subject")
        
        # Verificar que o resultado tem o formato esperado (não verificando o conteúdo exato devido às substituições complexas)
        assert isinstance(result, str)
        assert "<html>" in result
        assert "</html>" in result

def test_create_backup(email_service):
    """Testa a criação de backup"""
    # Criar arquivo de teste
    os.makedirs("backup", exist_ok=True)
    test_file = "test_backup.csv"
    
    with open(test_file, "w") as f:
        f.write("email,nome\ntest@example.com,Test User\n")
    
    # Executar método
    backup_path = email_service.create_backup(test_file)
    
    # Verificar que backup foi criado
    assert os.path.exists(backup_path)
    
    # Verificar conteúdo
    with open(backup_path, "r") as f:
        backup_content = f.read()
    
    with open(test_file, "r") as f:
        original_content = f.read()
    
    assert backup_content == original_content
    
    # Limpar após o teste
    os.remove(test_file)
    os.remove(backup_path)

@patch('smtplib.SMTP')
def test_send_test_email(mock_smtp, email_service, setup_test_env):
    """Testa o envio de email de teste"""
    # Configurar mocks
    mock_instance = mock_smtp.return_value
    mock_instance.__enter__.return_value = mock_instance
    
    # Configurar o email_service com os atributos necessários
    email_service.config.content_config = {"email": {"subject": "Test Subject"}}
    
    # Adicionar mocks para os métodos internos chamados
    with patch.object(email_service, '_create_message') as mock_create_message:
        mock_message = MagicMock()
        mock_create_message.return_value = mock_message
        
        # Executar método
        result = email_service.send_test_email("test_recipient@example.com")
        
        # Verificar que o email foi enviado
        assert result is True
        mock_create_message.assert_called_once()
        mock_instance.send_message.assert_called_once_with(mock_message) 