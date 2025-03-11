"""
Rotas para operações de email.
"""
from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional

from ...config import Config
from ...email_service import EmailService
from ..schemas.models import (
    SendEmailRequest, SendEmailResponse, TestSmtpRequest,
    ClearFlagsRequest, ClearFlagsResponse, SyncUnsubscribedRequest,
    SyncUnsubscribedResponse, ReportData, ApiResponse,
    validate_request, to_dict
)
from ..utils import error_response, success_response
from ..auth import token_required, role_required

# Criar blueprint para rotas de email
email_bp = Blueprint('email', __name__, url_prefix='/api/emails')

def get_email_service() -> EmailService:
    """
    Obtém uma instância do serviço de email.
    
    Returns:
        Instância do EmailService
    """
    config = Config()
    return EmailService(config)

@email_bp.route('/send', methods=['POST'])
@token_required
def send_emails():
    """
    Envia emails em lote.
    
    Returns:
        Resposta JSON com o resultado do envio
    """
    try:
        # Validar a requisição
        if not request.json:
            return error_response("O corpo da requisição deve ser JSON", 400)
            
        # Validar os dados de entrada
        data = validate_request(request.json, SendEmailRequest)
        
        # Obter serviço de email
        email_service = get_email_service()
        
        # Processar o envio
        result = email_service.process_email_sending(
            csv_file=data.csv_file,
            template=data.template,
            skip_unsubscribed_sync=data.skip_unsubscribed_sync,
            is_test_mode=(data.mode.value == "test")
        )
        
        # Preparar a resposta
        report_data = ReportData(
            report_file=result.get('report_file', ''),
            duration=result.get('duration', 0.0),
            avg_time=result.get('avg_time', 0.0),
            total_sent=result.get('total_sent', 0),
            successful=result.get('successful', 0),
            failed=result.get('failed', 0)
        )
        
        response = SendEmailResponse(
            status="success",
            message="Emails enviados com sucesso",
            report=report_data
        )
        
        return jsonify(to_dict(response))
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"Erro ao enviar emails: {str(e)}", 500)

@email_bp.route('/test-smtp', methods=['POST'])
@token_required
def test_smtp():
    """
    Testa a conexão SMTP.
    
    Returns:
        Resposta JSON com o resultado do teste
    """
    try:
        # Validar a requisição
        if request.json:
            data = validate_request(request.json, TestSmtpRequest)
            recipient = data.recipient
        else:
            recipient = None
            
        # Obter serviço de email
        email_service = get_email_service()
        
        # Testar a conexão SMTP
        email_service.send_test_email(recipient)
        
        return success_response("Teste SMTP realizado com sucesso")
        
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        return error_response(f"Erro ao testar conexão SMTP: {str(e)}", 500)

@email_bp.route('/clear-flags', methods=['POST'])
@role_required('admin')
def clear_flags():
    """
    Limpa as flags de envio no arquivo CSV.
    
    Returns:
        Resposta JSON com o resultado da operação
    """
    try:
        # Validar a requisição
        if request.json:
            data = validate_request(request.json, ClearFlagsRequest)
            csv_file = data.csv_file
        else:
            csv_file = None
            
        # Obter serviço de email
        email_service = get_email_service()
        
        # Limpar as flags
        cleared_count = email_service.clear_sent_flags(csv_file)
        
        # Preparar a resposta
        response = ClearFlagsResponse(
            status="success",
            message=f"{cleared_count} flags limpas com sucesso",
            cleared_count=cleared_count
        )
        
        return jsonify(to_dict(response))
        
    except ValueError as e:
        return error_response(str(e), 400)
    except FileNotFoundError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f"Erro ao limpar flags: {str(e)}", 500)

@email_bp.route('/sync-unsubscribed', methods=['POST'])
@role_required('admin')
def sync_unsubscribed():
    """
    Sincroniza os emails descadastrados.
    
    Returns:
        Resposta JSON com o resultado da sincronização
    """
    try:
        # Validar a requisição
        if request.json:
            data = validate_request(request.json, SyncUnsubscribedRequest)
            csv_file = data.csv_file
            unsubscribe_file = data.unsubscribe_file
        else:
            csv_file = None
            unsubscribe_file = None
            
        # Obter serviço de email
        email_service = get_email_service()
        
        # Obter configuração para valores padrão
        config = Config()
        
        # Determinar arquivos a serem usados
        if not csv_file:
            csv_file = config.email_config.get("csv_file")
            
        if not unsubscribe_file:
            unsubscribe_file = config.email_config.get("unsubscribe_file", "data/descadastros.csv")
            
        # Sincronizar os emails
        updated_count = email_service.sync_unsubscribed_emails(csv_file, unsubscribe_file)
        
        # Preparar a resposta
        response = SyncUnsubscribedResponse(
            status="success",
            message=f"{updated_count} emails sincronizados",
            csv_file=csv_file,
            unsubscribe_file=unsubscribe_file,
            updated_count=updated_count
        )
        
        return jsonify(to_dict(response))
        
    except ValueError as e:
        return error_response(str(e), 400)
    except FileNotFoundError as e:
        return error_response(str(e), 404)
    except Exception as e:
        return error_response(f"Erro ao sincronizar emails descadastrados: {str(e)}", 500)

@email_bp.route('/config', methods=['GET'])
@role_required('admin')
def get_email_config():
    # ... existing code ... 