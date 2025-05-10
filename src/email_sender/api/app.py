"""
Aplicação principal da API REST.
"""
from flask import Flask
from flask_cors import CORS
import logging
import os
from pathlib import Path

from ..config import Config
from .utils import load_api_config
from .routes.email_routes import email_bp
from .routes.config_routes import config_bp
from .routes.docs_routes import docs_bp
from .auth import token_required

def create_app(config_file: str = "config/rest.yaml") -> Flask:
    """
    Cria e configura a aplicação Flask.
    
    Args:
        config_file: Caminho para o arquivo de configuração
        
    Returns:
        Aplicação Flask configurada
    """
    # Carregar configurações
    config = Config()
    api_config = load_api_config(config_file)
    
    # Criar aplicação Flask
    app = Flask(__name__)
    
    # Configurar a aplicação
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    # Configurações do servidor
    server_config = api_config.get('server', {})
    app.config['SERVER_HOST'] = server_config.get('host', '0.0.0.0')
    app.config['SERVER_PORT'] = int(server_config.get('port', 5000))
    app.config['DEBUG'] = server_config.get('debug', True)
    
    # Configurações de timeout
    timeout_config = api_config.get('timeout', {})
    app.config['REQUEST_TIMEOUT'] = int(timeout_config.get('request', 60))
    
    # Configurações de segurança
    security_config = api_config.get('security', {})
    app.config['REQUIRE_API_KEY'] = security_config.get('require_api_key', False)
    app.config['API_KEY_HEADER'] = security_config.get('api_key_header', 'X-API-Key')
    app.config['API_KEYS'] = security_config.get('api_keys', [])
    
    # Configurações de rate limiting
    rate_limit_config = security_config.get('rate_limiting', {})
    app.config['RATE_LIMITING_ENABLED'] = rate_limit_config.get('enabled', True)
    app.config['REQUESTS_PER_MINUTE'] = int(rate_limit_config.get('requests_per_minute', 60))
    
    # Configurações de documentação
    docs_config = api_config.get('documentation', {})
    app.config['API_DOCS_ENABLED'] = docs_config.get('enabled', True)
    app.config['API_DOCS_PATH'] = docs_config.get('path', '/api/docs')
    app.config['API_SPEC_FILE'] = docs_config.get('openapi_file', 'config/api-docs.yaml')
    app.config['API_TITLE'] = docs_config.get('title', 'Email Sender API')
    app.config['API_VERSION'] = docs_config.get('version', '1.0.0')
    
    # Configurar CORS
    if security_config.get('enable_cors', True):
        CORS(app, resources={r"/api/*": {"origins": security_config.get('allowed_origins', '*')}})
    
    # Configurar logging
    logging_config = api_config.get('logging', {})
    log_level = getattr(logging, logging_config.get('level', 'INFO'))
    log_file = logging_config.get('file', '')
    
    if log_file:
        # Criar diretório de logs se necessário
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        logging.basicConfig(
            filename=log_file,
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Registrar blueprints com base na configuração
    endpoints_config = api_config.get('endpoints', {})
    
    # Registrar rotas de email se habilitadas
    email_config = endpoints_config.get('email', {})
    if email_config.get('enabled', True):
        app.register_blueprint(email_bp, url_prefix=email_config.get('base_path', '/api/emails'))
    
    # Registrar rotas de config se habilitadas
    config_endpoint_config = endpoints_config.get('config', {})
    if config_endpoint_config.get('enabled', True):
        app.register_blueprint(config_bp, url_prefix=config_endpoint_config.get('base_path', '/api/config'))
    
    # Registrar rotas de docs se habilitadas
    if docs_config.get('enabled', True):
        app.register_blueprint(docs_bp, url_prefix=docs_config.get('path', '/api/docs'))
    
    # Registrar rotas de autenticação
    if 'auth' in endpoints_config and endpoints_config['auth'].get('enabled', False):
        auth_config = endpoints_config['auth']
        from .routes.auth_routes import create_auth_blueprint
        app.register_blueprint(
            create_auth_blueprint(
                base_url=auth_config.get('base_url', '/api/auth'),
                **auth_config
            )
        )
    
    # Adicionar rota healthcheck
    health_config = endpoints_config.get('health', {})
    if health_config.get('enabled', True):
        @app.route(health_config.get('path', '/api/health'), methods=health_config.get('methods', ['GET']))
        @token_required
        def health_check():
            from datetime import datetime
            return {
                'status': 'ok',
                'timestamp': datetime.now().isoformat()
            }
    
    # Adicionar configurações JWT
    if 'security' in api_config and 'jwt' in api_config['security']:
        jwt_config = api_config['security']['jwt']
        if jwt_config.get('enabled', False):
            app.config['JWT_SECRET_KEY'] = jwt_config.get('secret_key')
            app.config['JWT_TOKEN_EXPIRY_HOURS'] = jwt_config.get('token_expiry_hours', 24)
            app.config['JWT_REFRESH_TOKEN_EXPIRY_HOURS'] = jwt_config.get('refresh_token_expiry_hours', 168)
            app.config['JWT_ALGORITHM'] = jwt_config.get('algorithm', 'HS256')
    
    return app 