"""
Rotas para documentação da API.
"""
from flask import Blueprint, jsonify, render_template, current_app, send_from_directory, request
import yaml
import logging
import os
from ..utils import error_response
from ..auth import token_required

logger = logging.getLogger(__name__)

# Criar blueprint para rotas de documentação
docs_bp = Blueprint('docs', __name__)

@docs_bp.route('/')
@token_required
def docs_ui():
    """
    Renderiza a interface Swagger UI.
    
    Returns:
        Interface HTML do Swagger UI
    """
    # Obter a URL base da API
    api_url = f"{request.scheme}://{request.host}"
    
    return render_template(
        'swagger-ui.html',
        title=current_app.config.get('API_TITLE', 'Email Sender API'),
        swagger_url=f"{request.path}/swagger.json"
    )

@docs_bp.route('/swagger.json')
@token_required
def swagger_json():
    """
    Retorna a especificação OpenAPI em formato JSON.
    
    Returns:
        Especificação OpenAPI em JSON
    """
    try:
        # Obter a localização do arquivo de especificação
        openapi_file = current_app.config.get('OPENAPI_FILE', 'config/api-docs.yaml')
        
        if not os.path.exists(openapi_file):
            return error_response("Arquivo de especificação OpenAPI não encontrado", 404)
        
        # Carregar o arquivo YAML
        with open(openapi_file, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
            
        # Retornar como JSON
        return jsonify(spec)
        
    except Exception as e:
        logger.error(f"Erro ao carregar especificação OpenAPI: {str(e)}")
        return error_response(f"Erro ao carregar especificação OpenAPI: {str(e)}", 500)

@docs_bp.route('/swagger-ui/<path:path>')
def swagger_ui_static(path):
    """
    Serve arquivos estáticos do Swagger UI.
    
    Args:
        path: Caminho relativo para o arquivo estático
        
    Returns:
        Arquivo estático solicitado
    """
    static_dir = current_app.config.get('SWAGGER_UI_DIR', 'swagger-ui-dist')
    return send_from_directory(static_dir, path) 