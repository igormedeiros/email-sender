"""
Utilitários para a API REST.
"""
import yaml
import logging
import os
from pathlib import Path
from functools import wraps
from typing import Dict, Any, List, Callable, Optional
from flask import request, jsonify, current_app, Response

logger = logging.getLogger("api")

def load_api_config(config_file: str) -> Dict[str, Any]:
    """
    Carrega a configuração da API do arquivo YAML.
    
    Args:
        config_file: Caminho para o arquivo de configuração
        
    Returns:
        Dicionário com as configurações da API
    """
    try:
        if not os.path.exists(config_file):
            logger.warning(f"Arquivo de configuração {config_file} não encontrado. Usando valores padrão.")
            return {}
            
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        if not config:
            logger.warning(f"Arquivo de configuração {config_file} está vazio. Usando valores padrão.")
            return {}
            
        return config
    except Exception as e:
        logger.error(f"Erro ao carregar configuração da API: {str(e)}")
        return {}

def load_api_spec(spec_file: str) -> Dict[str, Any]:
    """
    Carrega a especificação OpenAPI do arquivo YAML.
    
    Args:
        spec_file: Caminho para o arquivo de especificação
        
    Returns:
        Dicionário com a especificação OpenAPI
    """
    try:
        if not os.path.exists(spec_file):
            logger.warning(f"Arquivo de especificação {spec_file} não encontrado.")
            return {}
            
        with open(spec_file, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
            
        return spec
    except Exception as e:
        logger.error(f"Erro ao carregar especificação da API: {str(e)}")
        return {}

def is_endpoint_enabled(endpoint_config: Dict[str, Any], endpoint_key: str) -> bool:
    """
    Verifica se um endpoint está habilitado na configuração.
    
    Args:
        endpoint_config: Configuração de endpoints
        endpoint_key: Chave do endpoint a verificar
        
    Returns:
        True se o endpoint estiver habilitado, False caso contrário
    """
    if not endpoint_config:
        return True  # Por padrão, todos os endpoints estão habilitados
        
    if endpoint_key not in endpoint_config:
        return True
        
    return endpoint_config.get(endpoint_key, {}).get("enabled", True)

def error_response(message: str, status_code: int = 400) -> Response:
    """
    Cria uma resposta de erro padronizada.
    
    Args:
        message: Mensagem de erro
        status_code: Código de status HTTP
        
    Returns:
        Resposta JSON com a mensagem de erro
    """
    return jsonify({"status": "error", "message": message}), status_code
    
def success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Response:
    """
    Cria uma resposta de sucesso padronizada.
    
    Args:
        message: Mensagem de sucesso
        data: Dados adicionais para incluir na resposta
        
    Returns:
        Resposta JSON com a mensagem de sucesso e dados
    """
    response = {"status": "success", "message": message}
    if data:
        response.update(data)
    return jsonify(response)

def api_key_required(f: Callable) -> Callable:
    """
    Decorator para verificar a chave de API nas requisições.
    
    Args:
        f: Função a decorar
        
    Returns:
        Função decorada
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verificar se autenticação está habilitada
        if not current_app.config.get('REQUIRE_API_KEY', False):
            return f(*args, **kwargs)
            
        api_key_header = current_app.config.get('API_KEY_HEADER', 'X-API-Key')
        api_keys = current_app.config.get('API_KEYS', [])
        
        # Verificar se o cabeçalho existe
        api_key = request.headers.get(api_key_header)
        if not api_key:
            return error_response("API key is required", 401)
            
        # Verificar se a chave é válida
        if api_key not in api_keys:
            return error_response("Invalid API key", 403)
            
        return f(*args, **kwargs)
    return decorated 