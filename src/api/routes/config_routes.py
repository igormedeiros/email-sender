"""
Rotas para operações de configuração.
"""
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import os

from ..utils import error_response, success_response
from ..auth import token_required, role_required
from datetime import datetime

# Criar blueprint para rotas de configuração
config_bp = Blueprint('config', __name__, url_prefix='/api/config')

# Definição do arquivo de configuração de email
DEFAULT_CONFIG_FILE = "config/email.yaml"

@config_bp.route('/', methods=['GET'])
@role_required('admin')
def get_config():
    """
    Obtém as configurações atuais.
    
    Returns:
        Configurações atuais em formato JSON
    """
    try:
        config_path = Path(DEFAULT_CONFIG_FILE)
        
        if not config_path.exists():
            return error_response("Arquivo de configuração não encontrado", 404)
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        return jsonify(config)
        
    except Exception as e:
        return error_response(f"Erro ao obter configurações: {str(e)}", 500)

@config_bp.route('/', methods=['PUT'])
@role_required('admin')
def update_config():
    """
    Atualiza completamente as configurações.
    
    Returns:
        Resposta JSON com o resultado da operação
    """
    try:
        # Verificar se o corpo da requisição contém dados válidos
        if not request.json:
            return error_response("Configurações não encontradas no corpo da requisição", 400)
            
        config_path = Path(DEFAULT_CONFIG_FILE)
        
        # Criar diretório de config se não existir
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Fazer backup do arquivo existente se houver
        if config_path.exists():
            # Criar backup com timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_path.with_name(f"{config_path.stem}.backup_{timestamp}{config_path.suffix}")
            
            with open(config_path, 'r', encoding='utf-8') as src:
                with open(backup_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        
        # Salvar novas configurações
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(request.json, f, default_flow_style=False, allow_unicode=True)
            
        return success_response("Configurações atualizadas com sucesso", {
            "backup_file": str(backup_path) if config_path.exists() else None
        })
        
    except Exception as e:
        return error_response(f"Erro ao atualizar configurações: {str(e)}", 500)

@config_bp.route('/partial', methods=['PATCH'])
@role_required('admin')
def update_config_partial():
    """
    Atualiza parcialmente as configurações.
    
    Returns:
        Resposta JSON com o resultado da operação
    """
    try:
        # Verificar se o corpo da requisição contém dados válidos
        if not request.json:
            return error_response("Configurações não encontradas no corpo da requisição", 400)
            
        config_path = Path(DEFAULT_CONFIG_FILE)
        
        if not config_path.exists():
            return error_response("Arquivo de configuração não encontrado", 404)
            
        # Ler configurações atuais
        with open(config_path, 'r', encoding='utf-8') as f:
            current_config = yaml.safe_load(f) or {}
            
        # Fazer backup do arquivo existente
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_name(f"{config_path.stem}.backup_{timestamp}{config_path.suffix}")
        
        with open(config_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        # Atualizar configurações com os novos valores (merge recursivo)
        update_dict(current_config, request.json)
        
        # Salvar configurações atualizadas
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f, default_flow_style=False, allow_unicode=True)
            
        return success_response("Configurações atualizadas parcialmente com sucesso", {
            "backup_file": str(backup_path)
        })
        
    except Exception as e:
        return error_response(f"Erro ao atualizar configurações: {str(e)}", 500)
        
def update_dict(target, source):
    """Atualiza um dicionário de forma recursiva"""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            update_dict(target[key], value)
        else:
            target[key] = value 