import pytest
import json
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock
from flask import Flask, url_for
import jwt
import datetime

from src.api.app import create_app
from src.api.auth import generate_token, verify_token, token_required, role_required
from src.api.routes.email_routes import get_email_service
from src.email_service import EmailService
from src.config import Config

@pytest.fixture
def app_config():
    """Fixture que cria uma configuração REST para testes"""
    config_data = {
        "server": {
            "host": "127.0.0.1",
            "port": 5000,
            "debug": False
        },
        "timeout": {
            "request": 30
        },
        "security": {
            "require_api_key": True,
            "api_key_header": "X-API-Key",
            "api_keys": ["test-key-1", "test-key-2"],
            "jwt_secret": "test-secret",
            "jwt_expiry_hours": 24
        },
        "cors": {
            "enabled": True,
            "origins": ["*"]
        },
        "rate_limit": {
            "enabled": True,
            "limit": 100,
            "period": 60
        },
        "health": {
            "path": "/api/health",
            "methods": ["GET"],
            "enabled": True
        },
        "docs": {
            "path": "/api/docs",
            "enabled": True
        }
    }
    
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False) as temp:
        yaml.dump(config_data, temp)
        config_path = temp.name
    
    yield config_path
    
    # Limpar
    os.unlink(config_path)

@pytest.fixture
def test_app(app_config):
    """Fixture que cria uma instância da aplicação Flask para testes"""
    # Patches para evitar dependências externas
    with patch('src.api.app.Config') as mock_config:
        with patch('src.api.utils.load_api_config') as mock_load_config:
            # Configurar mocks
            mock_load_config.return_value = yaml.safe_load(open(app_config))
            
            # Criar aplicação
            app = create_app(app_config)
            app.config['TESTING'] = True
            app.config['JWT_SECRET_KEY'] = 'test-secret'
            
            # Usar contexto de teste
            with app.test_client() as client:
                with app.app_context():
                    yield client

@pytest.fixture
def valid_token():
    """Fixture que gera um token JWT válido para testes"""
    payload = {
        'sub': 'test-user',
        'roles': ['admin', 'user'],
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, 'test-secret', algorithm='HS256')
    return token

def test_create_app(app_config):
    """Testa a criação da aplicação Flask"""
    with patch('src.api.app.Config'):
        with patch('src.api.utils.load_api_config') as mock_load:
            # Configurar mock para retornar configuração válida
            mock_load.return_value = {
                'server': {'host': '127.0.0.1', 'port': 5000, 'debug': False},
                'security': {'require_api_key': False},
                'cors': {'enabled': True, 'origins': ['*']},
                'health': {'enabled': True, 'path': '/api/health'},
                'rate_limit': {'enabled': False},
                'docs': {'enabled': True, 'path': '/api/docs'}
            }
            
            # Criar aplicação
            app = create_app(app_config)
            
            # Verificar configuração
            assert isinstance(app, Flask)
            assert app.config['SERVER_HOST'] == '127.0.0.1'
            assert app.config['SERVER_PORT'] == 5000
            assert app.config['DEBUG'] is False

def test_health_check(test_app, valid_token):
    """Testa o endpoint de health check"""
    headers = {'Authorization': f'Bearer {valid_token}'}
    response = test_app.get('/api/health', headers=headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'uptime' in data['data']

def test_health_check_without_token(test_app):
    """Testa o endpoint de health check sem token"""
    response = test_app.get('/api/health')
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'Token inválido ou ausente' in data['message']

@patch('src.api.auth.verify_token')
def test_token_required_decorator(mock_verify_token, test_app):
    """Testa o decorator token_required"""
    # Configurar mock
    mock_verify_token.return_value = {
        'sub': 'test-user',
        'roles': ['user']
    }
    
    # Testar com token válido
    headers = {'Authorization': 'Bearer valid-token'}
    response = test_app.get('/api/health', headers=headers)
    
    assert response.status_code == 200
    mock_verify_token.assert_called_once()

@patch('src.api.auth.verify_token')
def test_role_required_decorator(mock_verify_token, test_app):
    """Testa o decorator role_required"""
    # Configurar mock para retornar payload com role admin
    mock_verify_token.return_value = {
        'sub': 'test-user',
        'roles': ['admin']
    }
    
    # A maioria das rotas protegidas por role estão em email_routes
    headers = {'Authorization': 'Bearer valid-token', 'Content-Type': 'application/json'}
    response = test_app.post('/api/emails/clear-flags', 
                            headers=headers, 
                            data=json.dumps({'csv_file': 'test.csv'}))
    
    # Não esperamos 403, então se o status não for 403, o teste de role passou
    assert response.status_code != 403
    mock_verify_token.assert_called()

def test_generate_token():
    """Testa a geração de tokens JWT"""
    # Configurar ambiente
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    
    with app.app_context():
        # Gerar token simples
        token = generate_token('test-user')
        assert token is not None
        
        # Gerar token com dados adicionais
        token_with_data = generate_token('test-user', {'roles': ['admin']})
        assert token_with_data is not None
        
        # Verificar token
        with patch('jwt.decode') as mock_decode:
            mock_decode.return_value = {'sub': 'test-user', 'roles': ['admin']}
            payload = verify_token(token_with_data)
            assert payload is not None
            assert payload['sub'] == 'test-user'
            assert 'roles' in payload

def test_get_email_service():
    """Testa a função de obtenção do serviço de email"""
    with patch('src.api.routes.email_routes.Config') as mock_config:
        with patch('src.api.routes.email_routes.EmailService') as mock_service:
            # Configurar retorno do mock
            instance = mock_service.return_value
            
            # Chamar a função
            service = get_email_service()
            
            # Verificar resultados
            assert service == instance
            mock_config.assert_called_once()
            mock_service.assert_called_once() 