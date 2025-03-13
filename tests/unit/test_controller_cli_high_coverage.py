import pytest
import os
import pandas as pd
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import typer
import sys
from typing import List, Dict

from src.controller_cli import (
    send_emails, 
    test_smtp, 
    sync_unsubscribed_command,
    interrupt_handler
)
from src.config import Config
from src.email_service import EmailService

@pytest.fixture
def setup_test_env():
    """Configurar ambiente de teste com diretórios e arquivos necessários"""
    # Criar diretórios
    os.makedirs("tests/data", exist_ok=True)
    os.makedirs("tests/data/templates", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    
    # Criar arquivo CSV com dados de teste
    with open("tests/data/test_csv.csv", "w") as f:
        f.write("email,nome,enviado,falhou\n")
        f.write("test@example.com,Test User,,\n")
    
    # Criar template de teste
    with open("tests/data/templates/test_template.html", "w") as f:
        f.write("<html><body>Olá {{nome}}, seu email é {{email}}</body></html>")
    
    # Criar arquivos de configuração
    config_data = {
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "test_user",
            "password": "test_pass",
            "use_tls": True
        },
        "email": {
            "csv_file": "tests/data/test_csv.csv",
            "template_dir": "tests/data/templates",
            "test_recipient": "test@example.com"
        }
    }
    
    email_content = {
        "email": {
            "subject": "Test Subject",
            "preview": "Test Preview"
        }
    }
    
    # Escrever arquivos de configuração
    import yaml
    with open("config/config.yaml", "w") as f:
        yaml.dump(config_data, f)
    
    with open("config/email.yaml", "w") as f:
        yaml.dump(email_content, f)
    
    yield
    
    # Limpar após os testes
    if os.path.exists("tests/data"):
        shutil.rmtree("tests/data")
    if os.path.exists("config"):
        shutil.rmtree("config")

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_send_emails_basic(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa o comando básico de envio de emails"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.content_config = {}
    
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.process_email_sending.return_value = {
        "total_sent": 1,
        "successful": 1,
        "failed": 0,
        "duracao_formatada": "00:00:01",
        "report": "Test report",
        "report_file": "test_report.html"
    }
    
    # Executar comando
    with patch('sys.exit'):
        send_emails(
            csv_file="tests/data/test_csv.csv",
            template="test_template.html",
            config_file="config/config.yaml",
            content_file="config/email.yaml",
            mode="test"
        )
    
    # Verificar que o serviço foi inicializado corretamente
    mock_config_class.assert_called_once_with("config/config.yaml", "config/email.yaml")
    mock_email_service_class.assert_called_once_with(mock_config)
    
    # Verificar que o método de envio foi chamado com os parâmetros corretos
    mock_email_service.process_email_sending.assert_called_once()
    args, kwargs = mock_email_service.process_email_sending.call_args
    assert kwargs["csv_file"] == "tests/data/test_csv.csv"
    assert kwargs["template"] == "test_template.html"
    assert kwargs["is_test_mode"] is True

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_send_emails_with_titulo(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa envio de emails com título personalizado"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.content_config = {"email": {}}
    
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.process_email_sending.return_value = {
        "total_sent": 1,
        "successful": 1,
        "failed": 0,
        "duracao_formatada": "00:00:01",
        "report": "Test report",
        "report_file": "test_report.html"
    }
    
    # Executar comando com título personalizado
    with patch('sys.exit'):
        send_emails(
            csv_file="tests/data/test_csv.csv",
            template="test_template.html",
            titulo="Título Personalizado",
            config_file="config/config.yaml",
            content_file="config/email.yaml",
            mode="test"
        )
    
    # Verificar que o título foi passado para o método de envio
    assert mock_config.content_config["email"]["subject"] == "Título Personalizado"

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_send_emails_production_mode(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa envio de emails em modo de produção"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.content_config = {}
    
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.process_email_sending.return_value = {
        "total_sent": 1,
        "successful": 1,
        "failed": 0,
        "duracao_formatada": "00:00:01",
        "report": "Test report",
        "report_file": "test_report.html"
    }
    
    # Executar comando em modo de produção
    with patch('sys.exit'):
        send_emails(
            csv_file="tests/data/test_csv.csv",
            template="test_template.html",
            mode="production",
            config_file="config/config.yaml",
            content_file="config/email.yaml"
        )
    
    # Verificar que o modo de produção foi passado para o método de envio
    mock_email_service.process_email_sending.assert_called_once()
    _, kwargs = mock_email_service.process_email_sending.call_args
    assert kwargs["is_test_mode"] is False

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
@patch("builtins.print")
def test_send_emails_error_handling(mock_print, mock_email_service_class, mock_config_class, setup_test_env):
    """Testa tratamento de erros no envio de emails"""
    # Configurar mock para lançar exceção
    mock_config = mock_config_class.return_value
    mock_config.content_config = {}
    
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.process_email_sending.side_effect = Exception("Test error")
    
    # Executar comando com o tratamento de erro
    with pytest.raises(SystemExit):
        send_emails(
            csv_file="tests/data/test_csv.csv",
            template="test_template.html",
            config_file="config/config.yaml",
            content_file="config/email.yaml",
            mode="test"
        )
    
    # Verificar que a mensagem de erro foi impressa
    mock_print.assert_any_call("\n❌ Error: Test error")

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_test_smtp_basic(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa comando básico de teste SMTP"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.email_config = {"test_recipient": "test@example.com"}
    mock_config.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test_user",
        "password": "test_pass",
        "use_tls": True
    }
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.send_test_email.return_value = True
    
    # Executar comando
    test_smtp(
        config_file="config/config.yaml",
        content_file="config/email.yaml"
    )
    
    # Verificar que o teste SMTP foi executado
    mock_email_service.send_test_email.assert_called_once_with("test@example.com")

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
@patch("builtins.print")
def test_test_smtp_with_debug(mock_print, mock_email_service_class, mock_config_class, setup_test_env):
    """Testa comando SMTP com debug habilitado"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.email_config = {"test_recipient": "test@example.com"}
    mock_config.smtp_config = {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test_user",
        "password": "test_pass",
        "use_tls": True
    }
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.send_test_email.return_value = True
    
    # Executar comando com debug
    test_smtp(
        config_file="config/config.yaml",
        content_file="config/email.yaml",
        debug=True
    )
    
    # Verificar que informações de debug foram impressas
    debug_calls = [call for call in mock_print.call_args_list if "INFORMAÇÕES DE CONEXÃO SMTP" in str(call)]
    assert len(debug_calls) > 0
    
    # Verificar que o teste SMTP foi executado
    mock_email_service.send_test_email.assert_called_once_with("test@example.com")

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
@patch("builtins.print")
def test_test_smtp_error_handling(mock_print, mock_email_service_class, mock_config_class, setup_test_env):
    """Testa tratamento de erros no teste SMTP"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.email_config = {"test_recipient": "test@example.com"}
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.send_test_email.side_effect = Exception("Test SMTP error")
    
    # Executar comando
    with patch('sys.exit'):
        test_smtp(
            config_file="config/config.yaml",
            content_file="config/email.yaml"
        )
    
    # Verificar que a mensagem de erro foi impressa
    found = False
    for call in mock_print.call_args_list:
        if '❌' in str(call) and 'test@example.com' in str(call):
            found = True
            break
    assert found, "Mensagem de erro não foi impressa corretamente"

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_sync_unsubscribed_basic(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa comando básico de sincronização de descadastros"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.sync_unsubscribed_emails.return_value = 1
    
    # Executar comando
    sync_unsubscribed_command(
        csv_file="tests/data/test_csv.csv",
        unsubscribe_file="tests/data/unsubscribe.csv",
        config_file="config/config.yaml",
        content_file="config/email.yaml"
    )
    
    # Verificar que a sincronização foi executada
    mock_email_service.sync_unsubscribed_emails.assert_called_once_with(
        "tests/data/test_csv.csv",
        "tests/data/unsubscribe.csv"
    )

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
def test_sync_unsubscribed_with_default_files(mock_email_service_class, mock_config_class, setup_test_env):
    """Testa sincronização com arquivos padrão"""
    # Configurar mocks
    mock_config = mock_config_class.return_value
    mock_config.email_config = {
        "csv_file": "default_csv.csv",
        "unsubscribe_file": "default_unsubscribe.csv"
    }
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.sync_unsubscribed_emails.return_value = 0
    
    # Usar patch para os parâmetros opcionais
    with patch('typer.Option', return_value=None):
        # Executar comando sem especificar arquivos
        sync_unsubscribed_command(
            config_file="config/config.yaml",
            content_file="config/email.yaml"
        )
    
    # Verificar que os arquivos padrão foram usados
    mock_email_service.sync_unsubscribed_emails.assert_called_once()
    args = mock_email_service.sync_unsubscribed_emails.call_args[0]
    assert "default_csv.csv" in str(args) or "default_csv.csv" in str(mock_email_service.sync_unsubscribed_emails.mock_calls)
    assert "default_unsubscribe.csv" in str(args) or "default_unsubscribe.csv" in str(mock_email_service.sync_unsubscribed_emails.mock_calls)

@patch("src.controller_cli.Config")
@patch("src.controller_cli.EmailService")
@patch("builtins.print")
def test_sync_unsubscribed_error_handling(mock_print, mock_email_service_class, mock_config_class, setup_test_env):
    """Testa tratamento de erros na sincronização"""
    # Configurar mock para lançar exceção
    mock_config = mock_config_class.return_value
    mock_email_service = mock_email_service_class.return_value
    mock_email_service.sync_unsubscribed_emails.side_effect = Exception("Sync error")
    
    # Executar comando com tratamento de erro
    with pytest.raises(SystemExit):
        sync_unsubscribed_command(
            csv_file="tests/data/test_csv.csv",
            unsubscribe_file="tests/data/unsubscribe.csv",
            config_file="config/config.yaml",
            content_file="config/email.yaml"
        )
    
    # Verificar que a mensagem de erro foi impressa
    error_call = [call for call in mock_print.call_args_list if "❌ Error" in str(call)]
    assert len(error_call) > 0

@patch("sys.exit")
@patch("builtins.print")
def test_interrupt_handler(mock_print, mock_exit):
    """Testa o comportamento do interrupt_handler"""
    # Executar handler
    interrupt_handler(None, None)
    
    # Verificar que a mensagem foi impressa e o sistema foi encerrado
    mock_print.assert_called_with("\nProcess interrupted by user. Saving progress...")
    mock_exit.assert_called_with(1) 