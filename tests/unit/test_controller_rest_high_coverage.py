import pytest
import json
import os
import tempfile
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask, request, jsonify

# Patch do Config antes da importação do app
with patch('src.config.Config') as mock_config_class:
    # Configurar o mock do Config
    mock_config = MagicMock()
    mock_config.rest_timeout_config = {"request": 30}
    mock_config_class.return_value = mock_config
    
    # Agora importar o controller_rest, excepto test_smtp para evitar problemas de contexto
    # Importamos a função separadamente para evitar que seja interpretada como um teste
    from src.controller_rest import app, health_check, send_emails, clear_sent_flags, sync_unsubscribed, get_config

@pytest.fixture
def mock_config():
    """Cria um mock do Config para testes"""
    mock_conf = MagicMock()  # Remover spec=Config para evitar InvalidSpecError
    
    # Configurar valores para os atributos necessários
    mock_conf.email_config = {
        "smtp": {
            "host": "smtp.example.com",
            "port": 587,
            "username": "test@example.com",
            "password": "senha_teste",
            "use_tls": True
        },
        "sender": "Email Sender <test@example.com>",
        "reply_to": "no-reply@example.com"
    }
    
    mock_conf.DEFAULT_CSV_PATH = "data/emails.csv"
    mock_conf.DEFAULT_UNSUBSCRIBE_PATH = "data/descadastros.csv"
    mock_conf.smtp_config = mock_conf.email_config["smtp"]
    
    return mock_conf

@pytest.fixture
def mock_email_service():
    """Cria um mock do serviço de email para testes"""
    mock_service = MagicMock()
    
    # Configurar comportamentos padrão para os métodos mais usados
    mock_service.process_email_sending.return_value = {
        "total_sent": 10,
        "successful": 9,
        "failed": 1,
        "duracao_formatada": "00:00:05",
        "report": "Relatório de teste",
        "report_file": "relatorio_teste.html"
    }
    
    mock_service.send_test_email.return_value = True
    mock_service.clear_sent_flags.return_value = 5
    mock_service.sync_unsubscribed_emails.return_value = 3
    
    return mock_service

@pytest.fixture
def test_client():
    """Cria um cliente de teste Flask com configuração mockada"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(test_client):
    """Testa a rota de verificação de saúde"""
    response = test_client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert 'timestamp' in data

def test_send_emails(test_client, mock_email_service):
    """Testa a rota de envio de emails"""
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "test.csv",
            "template": "template.html",
            "mode": "test",
            "skip_unsubscribed_sync": False
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/send', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'report' in data
        
        # Verificar que o serviço foi chamado com os parâmetros corretos
        mock_email_service.process_email_sending.assert_called_once()
        args, kwargs = mock_email_service.process_email_sending.call_args
        assert kwargs["csv_file"] == "test.csv"
        assert kwargs["template"] == "template.html"
        assert kwargs["is_test_mode"] is True  # modo "test"
        assert kwargs["skip_unsubscribed_sync"] is False

def test_send_emails_with_error(test_client, mock_email_service):
    """Testa a rota de envio de emails com erro"""
    # Configurar o mock para lançar uma exceção
    mock_email_service.process_email_sending.side_effect = Exception("Erro de teste")
    
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "test.csv",
            "template": "template.html"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/send', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta de erro
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert "Erro de teste" in data['error']

def test_test_smtp(test_client, mock_email_service):
    """Testa a rota de teste SMTP"""
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "recipient": "test@example.com"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/test-smtp', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert "test@example.com" in data['message']
        
        # Verificar que o serviço foi chamado com os parâmetros corretos
        mock_email_service.send_test_email.assert_called_once_with("test@example.com")

def test_test_smtp_with_error(test_client, mock_email_service):
    """Testa a rota de teste SMTP com erro"""
    # Configurar o mock para lançar uma exceção
    mock_email_service.send_test_email.side_effect = Exception("Erro de conexão SMTP")
    
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "recipient": "test@example.com"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/test-smtp', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta de erro
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert "Erro de conexão SMTP" in data['error']

def test_clear_sent_flags(test_client, mock_email_service):
    """Testa a rota para limpar flags"""
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "test.csv"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/clear-flags', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert '5 flags' in data['message']  # Verificar que a mensagem contém o número de flags
        
        # Verificar que o serviço foi chamado com os parâmetros corretos
        mock_email_service.clear_sent_flags.assert_called_once_with("test.csv")

def test_clear_sent_flags_with_error(test_client, mock_email_service):
    """Testa a rota para limpar flags com erro"""
    # Configurar o mock para lançar uma exceção
    mock_email_service.clear_sent_flags.side_effect = Exception("Erro ao limpar flags")
    
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "test.csv"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/clear-flags', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta de erro
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert "Erro ao limpar flags" in data['error']

def test_sync_unsubscribed(test_client, mock_email_service):
    """Testa a rota para sincronizar lista de descadastros"""
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "emails.csv",
            "unsubscribe_file": "descadastros.csv"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/sync-unsubscribed', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert '3 emails' in data['message']  # Verificar que a mensagem contém o número de emails
        assert data['csv_file'] == 'emails.csv'
        assert data['unsubscribe_file'] == 'descadastros.csv'
        
        # Verificar que o serviço foi chamado com os parâmetros corretos
        mock_email_service.sync_unsubscribed_emails.assert_called_once_with(
            "emails.csv", "descadastros.csv"
        )

def test_sync_unsubscribed_with_error(test_client, mock_email_service):
    """Testa a rota para sincronizar lista de descadastros com erro"""
    # Configurar o mock para lançar uma exceção
    mock_email_service.sync_unsubscribed_emails.side_effect = Exception("Erro de sincronização")
    
    # Mock para o serviço de email
    with patch('src.controller_rest.get_email_service', return_value=mock_email_service):
        # Dados da requisição
        request_data = {
            "csv_file": "emails.csv",
            "unsubscribe_file": "descadastros.csv"
        }
        
        # Enviar requisição
        response = test_client.post('/api/emails/sync-unsubscribed', 
                                   data=json.dumps(request_data),
                                   content_type='application/json')
        
        # Verificar resposta de erro
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
        assert "Erro de sincronização" in data['error']

def test_get_email_service():
    """Testa a obtenção do serviço de email"""
    with patch('src.controller_rest.Config') as mock_config_class:
        with patch('src.controller_rest.EmailService') as mock_email_service_class:
            # Configurar mock do Config e EmailService
            mock_conf = MagicMock()
            mock_config_class.return_value = mock_conf
            
            mock_service = MagicMock()
            mock_email_service_class.return_value = mock_service
            
            # Obter o serviço
            from src.controller_rest import get_email_service
            service = get_email_service()
            
            # Verificar resultado
            assert service == mock_service
            mock_email_service_class.assert_called_once_with(mock_conf) 