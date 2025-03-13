import pytest
import json
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock, mock_open
from flask import Flask, Response, jsonify, request

from src.api.utils import (
    load_api_config, 
    load_api_spec,
    is_endpoint_enabled,
    error_response, 
    success_response,
    api_key_required
)

@pytest.fixture
def sample_rest_config():
    """Cria um arquivo de configuração REST temporário para testes"""
    # Dados de configuração
    config_data = {
        "server": {
            "host": "127.0.0.1",
            "port": 5000,
            "debug": False
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
            "origins": ["http://localhost:3000", "https://app.example.com"]
        },
        "endpoints": {
            "email": {"enabled": True},
            "test_smtp": {"enabled": False},
            "config": {"enabled": False}
        }
    }
    
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        yaml.dump(config_data, temp_file)
        config_path = temp_file.name
    
    yield (config_path, config_data)
    
    # Limpar
    os.unlink(config_path)

@pytest.fixture
def sample_api_spec():
    """Cria um arquivo de especificação API temporário para testes"""
    # Dados de especificação
    spec_data = {
        "openapi": "3.0.0",
        "info": {
            "title": "Email Sender API",
            "version": "1.0.0"
        },
        "paths": {
            "/api/email/send": {
                "post": {
                    "summary": "Envia emails"
                }
            }
        }
    }
    
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        yaml.dump(spec_data, temp_file)
        spec_path = temp_file.name
    
    yield (spec_path, spec_data)
    
    # Limpar
    os.unlink(spec_path)

@pytest.fixture
def flask_app():
    """Cria uma aplicação Flask para testes"""
    app = Flask(__name__)
    app.config['API_KEYS'] = ['valid-key-1', 'valid-key-2']
    app.config['API_KEY_HEADER'] = 'X-API-Key'
    app.config['REQUIRE_API_KEY'] = True
    
    # Rota protegida por API key
    @app.route('/api-key-protected')
    @api_key_required
    def api_key_protected():
        return jsonify({"status": "success", "message": "API key test"})
    
    return app

def test_load_api_config(sample_rest_config):
    """Testa o carregamento de configuração da API"""
    config_path, expected_data = sample_rest_config
    
    # Carregar configuração
    config = load_api_config(config_path)
    
    # Verificar que os dados foram carregados corretamente
    assert config["server"]["host"] == expected_data["server"]["host"]
    assert config["server"]["port"] == expected_data["server"]["port"]
    assert config["security"]["api_keys"] == expected_data["security"]["api_keys"]
    assert config["cors"]["origins"] == expected_data["cors"]["origins"]

def test_load_api_config_file_not_found():
    """Testa o carregamento de configuração quando o arquivo não existe"""
    # Caminho de arquivo que não existe
    with patch('os.path.exists', return_value=False):
        config = load_api_config("/non/existent/file.yaml")
        
        # Deve retornar dicionário vazio, não lançar exceção
        assert config == {}

def test_load_api_config_invalid_yaml():
    """Testa o carregamento de configuração com YAML inválido"""
    # Mock para open que retorna conteúdo YAML inválido
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data="invalid: yaml: content:")):
            with patch('yaml.safe_load', side_effect=yaml.YAMLError("Erro de YAML")):
                config = load_api_config("config.yaml")
                
                # Deve retornar dicionário vazio, não lançar exceção
                assert config == {}

def test_load_api_spec(sample_api_spec):
    """Testa o carregamento de especificação da API"""
    spec_path, expected_data = sample_api_spec
    
    # Carregar especificação
    spec = load_api_spec(spec_path)
    
    # Verificar que os dados foram carregados corretamente
    assert spec["openapi"] == expected_data["openapi"]
    assert spec["info"]["title"] == expected_data["info"]["title"]
    assert spec["paths"]["/api/email/send"]["post"]["summary"] == "Envia emails"

def test_load_api_spec_file_not_found():
    """Testa o comportamento quando o arquivo de especificação não existe"""
    # Mock para FileNotFoundError
    with patch("builtins.open", side_effect=FileNotFoundError()):
        result = load_api_spec("nonexistent_file.yaml")
        assert result == {}

def test_is_endpoint_enabled():
    """Testa a verificação de ativação de endpoints"""
    # Configuração de exemplo
    config = {
        "endpoints": {
            "email": {"enabled": True},
            "test_smtp": {"enabled": False},
            "not_specified": {}
        }
    }
    
    # Verificar endpoints
    assert is_endpoint_enabled(config, "email") is True
    assert is_endpoint_enabled(config["endpoints"], "test_smtp") is False
    
    # Endpoint não especificado deve ser ativado por padrão
    assert is_endpoint_enabled(config["endpoints"], "not_specified") is True
    
    # Endpoint completamente ausente também deve ser ativado por padrão
    assert is_endpoint_enabled(config["endpoints"], "nonexistent") is True
    
    # Configuração sem seção 'endpoints' deve ativar todos os endpoints
    assert is_endpoint_enabled({}, "any_endpoint") is True

def test_success_response():
    """Testa a geração de resposta de sucesso"""
    # Caso 1: Apenas mensagem
    with Flask(__name__).app_context():
        response = success_response("Operação concluída com sucesso")
        result_data = json.loads(response.get_data(as_text=True))
        
        # Verificar resposta
        assert response.status_code == 200
        assert result_data["status"] == "success"
        assert result_data["message"] == "Operação concluída com sucesso"
    
    # Caso 2: Mensagem e dados
    with Flask(__name__).app_context():
        test_data = {"key1": "value1", "key2": 123}
        response = success_response("Operação concluída", test_data)
        result_data = json.loads(response.get_data(as_text=True))
        
        # Verificar resposta
        assert response.status_code == 200
        assert result_data["status"] == "success"
        assert result_data["message"] == "Operação concluída"
        assert result_data["key1"] == "value1"
        assert result_data["key2"] == 123

def test_error_response():
    """Testa a geração de resposta de erro"""
    # Caso 1: Erro padrão (400)
    with Flask(__name__).app_context():
        response_obj, status_code = error_response("Erro de validação")
        result_data = json.loads(response_obj.get_data(as_text=True))
        
        # Verificar resposta
        assert status_code == 400
        assert result_data["status"] == "error"
        assert result_data["message"] == "Erro de validação"
    
    # Caso 2: Erro personalizado (404)
    with Flask(__name__).app_context():
        response_obj, status_code = error_response("Recurso não encontrado", 404)
        result_data = json.loads(response_obj.get_data(as_text=True))
        
        # Verificar resposta
        assert status_code == 404
        assert result_data["status"] == "error"
        assert result_data["message"] == "Recurso não encontrado"

def test_api_key_required(flask_app):
    """Testa o decorator de proteção por API key"""
    with flask_app.test_client() as client:
        # Requisição sem API key
        response1 = client.get('/api-key-protected')
        assert response1.status_code == 401
        
        # Requisição com API key inválida
        response2 = client.get('/api-key-protected', headers={'X-API-Key': 'invalid-key'})
        assert response2.status_code == 403
        
        # Requisição com API key válida
        response3 = client.get('/api-key-protected', headers={'X-API-Key': 'valid-key-1'})
        assert response3.status_code == 200
        data = json.loads(response3.data)
        assert data["status"] == "success"

def test_api_key_required_disabled(flask_app):
    """Testa o decorator de proteção por API key quando desabilitado"""
    # Configurar app com proteção desabilitada
    flask_app.config['REQUIRE_API_KEY'] = False
    
    with flask_app.test_client() as client:
        # Requisição sem API key deve passar
        response = client.get('/api-key-protected')
        assert response.status_code == 200 