import pytest
import json
from unittest.mock import patch, MagicMock
import flask
from werkzeug.exceptions import BadRequest

from src.api.schemas.models import (
    SendEmailRequest, SendEmailResponse, TestSmtpRequest,
    ClearFlagsRequest, ClearFlagsResponse, SyncUnsubscribedRequest,
    SyncUnsubscribedResponse, ReportData, ApiResponse,
    validate_request, to_dict
)
from src.api.utils import error_response, success_response
from src.api.routes.email_routes import email_bp

@pytest.fixture
def mock_email_service():
    """Fixture que cria um mock para o serviço de email"""
    with patch('src.api.routes.email_routes.get_email_service') as mock_get_service:
        service = MagicMock()
        mock_get_service.return_value = service
        yield service

@pytest.fixture
def app():
    """Fixture que cria uma app Flask de teste com as rotas de email registradas"""
    app = flask.Flask(__name__)
    app.register_blueprint(email_bp)
    app.config['TESTING'] = True
    
    # Desabilitar verificação de token para os testes
    with patch('src.api.auth.token_required', lambda f: f):
        with patch('src.api.auth.role_required', lambda role: lambda f: f):
            yield app

@pytest.fixture
def client(app):
    """Fixture que cria um cliente de teste"""
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_send_emails_route(client, mock_email_service):
    """Testa a rota de envio de emails"""
    # Configurar mock
    process_result = {
        "total_sent": 2,
        "successful": 2,
        "failed": 0,
        "duracao_formatada": "00:00:01",
        "report": "Test report",
        "report_file": "report.txt"
    }
    mock_email_service.process_email_sending.return_value = process_result
    
    # Dados da requisição
    request_data = {
        "csv_file": "data/test.csv",
        "template": "test_template.html",
        "mode": "test",
        "skip_unsubscribed_sync": True
    }
    
    # Fazer requisição
    response = client.post(
        '/api/emails/send',
        data=json.dumps(request_data),
        content_type='application/json'
    )
    
    # Verificar resposta
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'data' in data
    
    # Verificar que o serviço foi chamado com os parâmetros corretos
    mock_email_service.process_email_sending.assert_called_once()
    args, kwargs = mock_email_service.process_email_sending.call_args
    assert kwargs['csv_file'] == 'data/test.csv'
    assert kwargs['template'] == 'test_template.html'
    assert kwargs['is_test_mode'] is True
    assert kwargs['skip_unsubscribed_sync'] is True

def test_send_emails_invalid_json(client):
    """Testa a rota de envio de emails com JSON inválido"""
    # Fazer requisição com dados inválidos
    response = client.post(
        '/api/emails/send',
        data="invalid json",
        content_type='application/json'
    )
    
    # Verificar resposta de erro
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'O corpo da requisição deve ser JSON' in data['message']

def test_test_smtp_route(client, mock_email_service):
    """Testa a rota de teste SMTP"""
    # Configurar mock
    mock_email_service.send_test_email.return_value = True
    
    # Dados da requisição
    request_data = {
        "recipient": "test@example.com"
    }
    
    # Fazer requisição
    response = client.post(
        '/api/emails/test-smtp',
        data=json.dumps(request_data),
        content_type='application/json'
    )
    
    # Verificar resposta
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    
    # Verificar que o serviço foi chamado com os parâmetros corretos
    mock_email_service.send_test_email.assert_called_once_with('test@example.com')

def test_clear_flags_route(client, mock_email_service):
    """Testa a rota de limpeza de flags"""
    # Configurar mock
    mock_email_service.clear_sent_flags.return_value = 10
    
    # Dados da requisição
    request_data = {
        "csv_file": "data/test.csv"
    }
    
    # Fazer requisição
    response = client.post(
        '/api/emails/clear-flags',
        data=json.dumps(request_data),
        content_type='application/json'
    )
    
    # Verificar resposta
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['rows_affected'] == 10
    
    # Verificar que o serviço foi chamado com os parâmetros corretos
    mock_email_service.clear_sent_flags.assert_called_once_with('data/test.csv')

def test_sync_unsubscribed_route(client, mock_email_service):
    """Testa a rota de sincronização de descadastros"""
    # Configurar mock
    mock_email_service.sync_unsubscribed_emails.return_value = 5
    
    # Dados da requisição
    request_data = {
        "csv_file": "data/test.csv",
        "unsubscribe_file": "data/descadastros.csv"
    }
    
    # Fazer requisição
    response = client.post(
        '/api/emails/sync-unsubscribed',
        data=json.dumps(request_data),
        content_type='application/json'
    )
    
    # Verificar resposta
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data']['rows_synced'] == 5
    
    # Verificar que o serviço foi chamado com os parâmetros corretos
    mock_email_service.sync_unsubscribed_emails.assert_called_once_with(
        'data/test.csv', 'data/descadastros.csv'
    )

def test_get_email_config_route(client):
    """Testa a rota de obtenção da configuração de email"""
    # Configurar mock para Config
    config_mock = MagicMock()
    config_mock.email_config = {
        "csv_file": "data/emails.csv",
        "template_dir": "templates",
        "batch_size": 10
    }
    
    with patch('src.api.routes.email_routes.Config', return_value=config_mock):
        # Fazer requisição
        response = client.get('/api/emails/config')
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'csv_file' in data['data']
        assert data['data']['csv_file'] == 'data/emails.csv'

def test_validate_request():
    """Testa a validação de requisições"""
    # Dados de exemplo
    data = {
        "csv_file": "test.csv",
        "template": "template.html",
        "mode": "test",
        "skip_unsubscribed_sync": True
    }
    
    # Validar contra o esquema
    validated = validate_request(data, SendEmailRequest)
    
    # Verificar resultado
    assert validated['csv_file'] == 'test.csv'
    assert validated['template'] == 'template.html'
    assert validated['mode'] == 'test'
    assert validated['skip_unsubscribed_sync'] is True

def test_validate_request_invalid():
    """Testa a validação de requisições inválidas"""
    # Dados inválidos (faltando campos obrigatórios)
    data = {
        "csv_file": "test.csv"  # falta template
    }
    
    # Tentar validar deve lançar exceção
    with pytest.raises(BadRequest):
        validate_request(data, SendEmailRequest)

def test_to_dict():
    """Testa a conversão de objetos para dicionários"""
    # Criar objeto
    report = ReportData(
        total_sent=10,
        successful=8,
        failed=2,
        duracao_formatada="00:00:05"
    )
    
    # Converter para dict
    result = to_dict(report)
    
    # Verificar resultado
    assert isinstance(result, dict)
    assert result['total_sent'] == 10
    assert result['successful'] == 8
    assert result['failed'] == 2
    assert result['duracao_formatada'] == "00:00:05"

def test_error_response():
    """Testa a geração de respostas de erro"""
    # Criar resposta de erro
    response = error_response("Erro de teste", 400)
    
    # Verificar resultado
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == 'Erro de teste'

def test_success_response():
    """Testa a geração de respostas de sucesso"""
    # Criar resposta de sucesso
    test_data = {"key": "value"}
    response = success_response(test_data)
    
    # Verificar resultado
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['data'] == test_data 