import pytest
import json
import datetime
import jwt
from unittest.mock import patch, MagicMock
from functools import wraps
from flask import Flask, request, jsonify, g, Response

from src.api.auth import (
    generate_token, 
    verify_token, 
    token_required, 
    role_required, 
    get_token_from_request
)

@pytest.fixture
def app():
    """Fixture que cria uma app Flask para testes"""
    app = Flask(__name__)
    app.config['JWT_SECRET_KEY'] = 'test-secret'
    app.config['JWT_EXPIRY_HOURS'] = 24
    
    # Rota protegida por token
    @app.route('/protected')
    @token_required
    def protected():
        return jsonify({"status": "success", "message": "Authenticated"})
    
    # Rota protegida por role
    @app.route('/admin-only')
    @token_required
    @role_required('admin')
    def admin_only():
        return jsonify({"status": "success", "message": "Admin access"})
    
    # Rota protegida com múltiplas roles
    @app.route('/multi-role')
    @token_required
    @role_required(['admin', 'editor'])
    def multi_role():
        return jsonify({"status": "success", "message": "Role access"})
    
    return app

@pytest.fixture
def valid_token(app):
    """Fixture que gera um token JWT válido para testes"""
    with app.app_context():
        return generate_token(
            'test-user', 
            {'roles': ['user']}
        )

@pytest.fixture
def admin_token(app):
    """Fixture que gera um token de admin para testes"""
    with app.app_context():
        return generate_token(
            'admin-user', 
            {'roles': ['admin']}
        )

def test_generate_token(app):
    """Testa a geração de token JWT"""
    with app.app_context():
        # Gerar token básico
        token = generate_token('test-user')
        
        # Verificar que é uma string não vazia
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decodificar e verificar conteúdo
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        assert payload['sub'] == 'test-user'
        assert 'exp' in payload
        assert 'iat' in payload

def test_generate_token_with_custom_data(app):
    """Testa a geração de token JWT com dados customizados"""
    with app.app_context():
        # Dados customizados
        custom_data = {
            'roles': ['admin', 'user'],
            'email': 'test@example.com',
            'name': 'Test User'
        }
        
        # Gerar token com dados customizados
        token = generate_token('test-user', custom_data)
        
        # Decodificar e verificar conteúdo
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        assert payload['sub'] == 'test-user'
        assert payload['roles'] == ['admin', 'user']
        assert payload['email'] == 'test@example.com'
        assert payload['name'] == 'Test User'

def test_generate_token_with_custom_expiry(app):
    """Testa a geração de token JWT com tempo de expiração customizado"""
    with app.app_context():
        # Gerar token com expiração curta
        token = generate_token('test-user', expiry_hours=1)
        
        # Decodificar e verificar expiração
        payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
        
        # Calcular tempo aproximado de expiração (1 hora)
        iat = datetime.datetime.fromtimestamp(payload['iat'])
        exp = datetime.datetime.fromtimestamp(payload['exp'])
        diff = exp - iat
        
        # Verificar que a diferença é próxima de 1 hora
        assert abs(diff.total_seconds() - 3600) < 10  # Permitir variação de alguns segundos

def test_verify_token_valid(app):
    """Testa a verificação de token válido"""
    with app.app_context():
        # Gerar token
        token = generate_token('test-user', {'roles': ['user']})
        
        # Verificar token
        payload = verify_token(token)
        
        # Verificar resultado
        assert payload is not None
        assert payload['sub'] == 'test-user'
        assert payload['roles'] == ['user']

def test_verify_token_invalid_signature(app):
    """Testa a verificação de token com assinatura inválida"""
    with app.app_context():
        # Gerar token válido
        token = generate_token("user123")
        
        # Modificar a assinatura do token
        token_parts = token.split('.')
        if len(token_parts) == 3:  # header.payload.signature
            # Modificar a assinatura (última parte)
            token_parts[2] = token_parts[2][:-5] + 'xxxxx'
            modified_token = '.'.join(token_parts)
            
            # Verificar token com assinatura inválida
            result = verify_token(modified_token)
            
            # Deve retornar None para token inválido, não lançar exceção
            assert result is None

def test_verify_token_expired(app):
    """Testa a verificação de token expirado"""
    with app.app_context():
        # Gerar token com expiração no passado
        past_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        
        # Mock para datetime.utcnow para simular token gerado no passado
        with patch('jwt.encode') as mock_encode:
            # Simular token expirado manipulando o payload
            payload = {
                'sub': 'user123',
                'iat': past_time,
                'exp': past_time  # Expirado
            }
            
            # Criar token já expirado
            secret_key = app.config['JWT_SECRET_KEY']
            expired_token = jwt.encode(payload, secret_key, algorithm='HS256')
            
            # Verificar token expirado
            result = verify_token(expired_token)
            
            # Deve retornar None para token expirado, não lançar exceção
            assert result is None

def test_get_token_from_request(app):
    """Testa a extração de token do cabeçalho Authorization"""
    with app.app_context():
        # Caso 1: Cabeçalho Authorization válido
        with app.test_request_context(headers={'Authorization': 'Bearer valid-token'}):
            token = get_token_from_request()
            assert token == 'valid-token'
        
        # Caso 2: Sem cabeçalho Authorization
        with app.test_request_context():
            token = get_token_from_request()
            assert token is None
        
        # Caso 3: Cabeçalho Authorization sem prefixo Bearer
        with app.test_request_context(headers={'Authorization': 'valid-token'}):
            token = get_token_from_request()
            assert token is None
        
        # Caso 4: Cabeçalho Authorization vazio
        with app.test_request_context(headers={'Authorization': ''}):
            token = get_token_from_request()
            assert token is None

def test_token_required_decorator(app, valid_token):
    """Testa o decorador que exige token"""
    with app.test_client() as client:
        # Acessar rota protegida com token válido
        response = client.get(
            '/protected',
            headers={'Authorization': f'Bearer {valid_token}'}
        )
        
        # Verificar resposta
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['message'] == 'Authenticated'

def test_role_required_decorator(app, valid_token, admin_token):
    """Testa o decorador que exige role específica"""
    with app.test_client() as client:
        # Tentar acessar rota admin com token comum (deve falhar)
        response1 = client.get(
            '/admin-only',
            headers={'Authorization': f'Bearer {valid_token}'}
        )
        assert response1.status_code == 403
        
        # Acessar rota admin com token de admin (deve funcionar)
        response2 = client.get(
            '/admin-only',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response2.status_code == 200
        data = json.loads(response2.data)
        assert data['status'] == 'success'
        assert data['message'] == 'Admin access'

def test_token_required_with_invalid_token(app):
    """Testa o comportamento quando um token inválido é fornecido"""
    with app.test_client() as client:
        # Acessar rota protegida com token inválido
        response = client.get(
            '/protected',
            headers={'Authorization': 'Bearer invalid.token.here'}
        )
        
        # Deve retornar erro de não autorizado
        assert response.status_code == 401

def test_role_required_with_missing_roles(app):
    """Testa o comportamento quando um usuário não tem as roles necessárias"""
    # Gerar token sem a role necessária
    with app.app_context():
        token = generate_token("user123", {"roles": ["user"]})
    
    with app.test_client() as client:
        # Tentar acessar rota que exige role admin
        response = client.get(
            '/admin-only',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Deve retornar erro de acesso negado
        assert response.status_code == 403 