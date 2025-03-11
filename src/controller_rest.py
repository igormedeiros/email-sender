from flask import Flask, request, jsonify
import os
import yaml
from datetime import datetime
from pathlib import Path

from .config import Config
from .email_service import EmailService

# Obter a configuração padrão
config = Config()

# Configurar a aplicação Flask com timeout adequado
app = Flask(__name__)
app.config['PERMANENT_SESSION_LIFETIME'] = config.rest_timeout_config['request']
app.config['REQUEST_TIMEOUT'] = config.rest_timeout_config['request']

# Configurações padrão
DEFAULT_CONFIG_FILE = "config/config.yaml"
DEFAULT_CONTENT_FILE = "config/email.yaml"

def get_email_service():
    """Obter instância do serviço com as configurações padrão"""
    service_config = Config(DEFAULT_CONFIG_FILE, DEFAULT_CONTENT_FILE)
    return EmailService(service_config)

# Endpoints principais

@app.route("/api/health", methods=["GET"])
def health_check():
    """Endpoint para verificar se o serviço está rodando"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route("/api/emails/send", methods=["POST"])
def send_emails():
    """Endpoint para enviar emails em lote"""
    data = request.json
    
    csv_file = data.get("csv_file")
    template = data.get("template")
    skip_unsubscribed_sync = data.get("skip_unsubscribed_sync", False)
    mode = data.get("mode", "test")  # test ou production
    
    if not template:
        return jsonify({"error": "Template não fornecido"}), 400
    
    try:
        email_service = get_email_service()
        
        result = email_service.process_email_sending(
            csv_file=csv_file,
            template=template,
            skip_unsubscribed_sync=skip_unsubscribed_sync,
            is_test_mode=(mode == "test")
        )
        
        return jsonify({
            "status": "success",
            "message": "Emails enviados com sucesso",
            "report": result
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/emails/test-smtp", methods=["POST"])
def test_smtp():
    """Endpoint para testar a conexão SMTP"""
    data = request.json
    recipient = data.get("recipient")
    
    try:
        email_service = get_email_service()
        
        # Se não foi fornecido recipient, usa o padrão da configuração
        if not recipient:
            config = Config(DEFAULT_CONFIG_FILE, DEFAULT_CONTENT_FILE)
            recipient = config.email_config.get("test_recipient")
            
            if not recipient:
                return jsonify({"error": "Recipient não configurado"}), 400
                
        # Envia o email de teste
        email_service.send_test_email(recipient)
        
        return jsonify({
            "status": "success",
            "message": f"Email de teste enviado para {recipient}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/emails/clear-flags", methods=["POST"])
def clear_sent_flags():
    """Endpoint para limpar as flags de envio"""
    data = request.json
    csv_file = data.get("csv_file")
    
    try:
        email_service = get_email_service()
        
        # Se não foi fornecido arquivo, usa o padrão da configuração
        if not csv_file:
            config = Config(DEFAULT_CONFIG_FILE, DEFAULT_CONTENT_FILE)
            csv_file = config.email_config.get("csv_file")
            
            if not csv_file:
                return jsonify({"error": "CSV file não configurado"}), 400
                
        # Limpa as flags
        cleared_count = email_service.clear_sent_flags(csv_file)
        
        return jsonify({
            "status": "success",
            "message": f"{cleared_count} flags limpas com sucesso"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/emails/sync-unsubscribed", methods=["POST"])
def sync_unsubscribed():
    """Endpoint para sincronizar emails descadastrados"""
    data = request.json
    csv_file = data.get("csv_file")
    unsubscribe_file = data.get("unsubscribe_file")
    
    try:
        email_service = get_email_service()
        config = Config(DEFAULT_CONFIG_FILE, DEFAULT_CONTENT_FILE)
        
        # Usa os valores padrão se não forem fornecidos
        if not csv_file:
            csv_file = config.email_config.get("csv_file")
            if not csv_file:
                return jsonify({"error": "CSV file não configurado"}), 400
                
        if not unsubscribe_file:
            unsubscribe_file = config.email_config.get("unsubscribe_file", "data/descadastros.csv")
            
        # Sincroniza os emails descadastrados
        updated_count = email_service.sync_unsubscribed_emails(csv_file, unsubscribe_file)
        
        return jsonify({
            "status": "success",
            "message": f"{updated_count} emails sincronizados",
            "csv_file": csv_file,
            "unsubscribe_file": unsubscribe_file
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Endpoints para gerenciar configurações

@app.route("/api/config", methods=["GET"])
def get_config():
    """Endpoint para obter as configurações atuais"""
    try:
        # Lê as configurações do email.yaml
        content_path = Path(DEFAULT_CONTENT_FILE)
        
        if not content_path.exists():
            return jsonify({"error": "Arquivo de configuração não encontrado"}), 404
            
        with open(content_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        return jsonify(config)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/config", methods=["PUT"])
def update_config():
    """Endpoint para atualizar as configurações"""
    try:
        new_config = request.json
        
        if not new_config:
            return jsonify({"error": "Configuração não fornecida"}), 400
            
        content_path = Path(DEFAULT_CONTENT_FILE)
        
        # Cria um backup antes de atualizar
        backup_path = content_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        
        # Se o arquivo já existir, cria um backup
        if content_path.exists():
            with open(content_path, 'r', encoding='utf-8') as f:
                current_config = yaml.safe_load(f)
                
            with open(backup_path, 'w', encoding='utf-8') as f:
                yaml.dump(current_config, f)
        
        # Atualiza o arquivo com as novas configurações
        with open(content_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_config, f)
            
        return jsonify({
            "status": "success",
            "message": "Configurações atualizadas com sucesso",
            "backup_file": str(backup_path) if content_path.exists() else None
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/config/partial", methods=["PATCH"])
def update_config_partial():
    """Endpoint para atualizar parcialmente as configurações"""
    try:
        partial_config = request.json
        
        if not partial_config:
            return jsonify({"error": "Configuração não fornecida"}), 400
            
        content_path = Path(DEFAULT_CONTENT_FILE)
        
        # Verifica se o arquivo existe
        if not content_path.exists():
            return jsonify({"error": "Arquivo de configuração não encontrado"}), 404
            
        # Lê a configuração atual
        with open(content_path, 'r', encoding='utf-8') as f:
            current_config = yaml.safe_load(f)
            
        # Cria um backup antes de atualizar
        backup_path = content_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f)
            
        # Atualiza apenas os campos fornecidos
        def update_dict(target, source):
            for key, value in source.items():
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    update_dict(target[key], value)
                else:
                    target[key] = value
        
        update_dict(current_config, partial_config)
        
        # Salva a configuração atualizada
        with open(content_path, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f)
            
        return jsonify({
            "status": "success",
            "message": "Configurações atualizadas parcialmente com sucesso",
            "backup_file": str(backup_path)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 