"""
Módulo para autenticação JWT e proteção de endpoints.
Implementa funções para geração, validação e verificação de tokens.
"""
import jwt
import logging
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Any, Callable, Optional, Union

logger = logging.getLogger(__name__)

def generate_token(user_id: str, additional_data: Dict = None, expiry_hours: int = 24) -> str:
    """
    Gera um token JWT para o usuário.
    
    Args:
        user_id: Identificador único do usuário
        additional_data: Dados adicionais a serem incluídos no token
        expiry_hours: Validade do token em horas
        
    Returns:
        Token JWT gerado
    """
    additional_data = additional_data or {}
    
    # Carregar configuração secreta do JWT
    secret_key = current_app.config.get('JWT_SECRET_KEY')
    if not secret_key:
        raise ValueError("JWT_SECRET_KEY não configurada na aplicação")
    
    # Definir prazo de expiração
    expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours)
    
    # Criar payload do token
    payload = {
        'sub': user_id,
        'iat': datetime.datetime.utcnow(),
        'exp': expiry
    }
    
    # Adicionar dados extras
    payload.update(additional_data)
    
    # Gerar o token com algoritmo HS256
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    return token

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifica e decodifica um token JWT.
    
    Args:
        token: Token JWT a ser verificado
        
    Returns:
        Payload do token se válido, None caso contrário
    """
    secret_key = current_app.config.get('JWT_SECRET_KEY')
    if not secret_key:
        logger.error("JWT_SECRET_KEY não configurada na aplicação")
        return None
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {str(e)}")
        return None

def get_token_from_request() -> Optional[str]:
    """
    Extrai o token JWT do cabeçalho de autorização.
    
    Returns:
        Token extraído ou None se não encontrado/inválido
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    # Verificar formato "Bearer <token>"
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]

def token_required(f: Callable) -> Callable:
    """
    Decorador que exige token JWT válido para acessar um endpoint.
    
    Args:
        f: Função a ser decorada
        
    Returns:
        Função decorada que verifica autenticação
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        
        if not token:
            return jsonify({'message': 'Token de autenticação ausente'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'message': 'Token inválido ou expirado'}), 401
        
        # Adiciona o payload do token ao contexto da requisição
        request.jwt_payload = payload
        
        return f(*args, **kwargs)
    
    return decorated

def role_required(roles: Union[str, list]) -> Callable:
    """
    Decorador que verifica se o usuário tem a(s) função(ões) necessária(s).
    
    Args:
        roles: Função ou lista de funções requeridas
        
    Returns:
        Decorador que verifica funções do usuário
    """
    if isinstance(roles, str):
        roles = [roles]
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            # Verificar se o usuário tem alguma das funções necessárias
            user_roles = request.jwt_payload.get('roles', [])
            
            if not any(role in user_roles for role in roles):
                return jsonify({'message': 'Acesso negado: permissões insuficientes'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator 