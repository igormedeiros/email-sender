import pytest
import json
from unittest.mock import patch
from werkzeug.exceptions import BadRequest

from src.api.schemas.models import (
    SendEmailRequest, SendEmailResponse, TestSmtpRequest,
    ClearFlagsRequest, ClearFlagsResponse, SyncUnsubscribedRequest,
    SyncUnsubscribedResponse, ReportData, ApiResponse,
    validate_request, to_dict
)

def test_send_email_request_validation():
    """Testa a validação do esquema SendEmailRequest"""
    # Dados válidos mínimos
    data = {
        "csv_file": "test.csv",
        "template": "template.html"
    }
    
    # Validar
    validated = validate_request(data, SendEmailRequest)
    
    # Verificar valores padrão
    assert validated["csv_file"] == "test.csv"
    assert validated["template"] == "template.html"
    assert validated["mode"] == "test"  # Valor padrão
    assert validated["skip_unsubscribed_sync"] is False  # Valor padrão
    assert validated.get("titulo") is None  # Campo opcional

def test_send_email_request_validation_with_all_fields():
    """Testa a validação do esquema SendEmailRequest com todos os campos"""
    # Dados completos
    data = {
        "csv_file": "test.csv",
        "template": "template.html",
        "mode": "production",
        "skip_unsubscribed_sync": True,
        "titulo": "Título do Email"
    }
    
    # Validar
    validated = validate_request(data, SendEmailRequest)
    
    # Verificar todos os campos
    assert validated["csv_file"] == "test.csv"
    assert validated["template"] == "template.html"
    assert validated["mode"] == "production"
    assert validated["skip_unsubscribed_sync"] is True
    assert validated["titulo"] == "Título do Email"

def test_send_email_request_validation_invalid_mode():
    """Testa a validação do esquema SendEmailRequest com modo inválido"""
    # Dados com modo inválido
    data = {
        "csv_file": "test.csv",
        "template": "template.html",
        "mode": "invalid_mode"  # Modo inválido (deve ser 'test' ou 'production')
    }
    
    # Validar deve falhar
    with pytest.raises(BadRequest):
        validate_request(data, SendEmailRequest)

def test_test_smtp_request_validation():
    """Testa a validação do esquema TestSmtpRequest"""
    # Dados válidos
    data = {
        "recipient": "test@example.com"
    }
    
    # Validar
    validated = validate_request(data, TestSmtpRequest)
    
    # Verificar campos
    assert validated["recipient"] == "test@example.com"

def test_test_smtp_request_validation_invalid_email():
    """Testa a validação do esquema TestSmtpRequest com email inválido"""
    # Dados com email inválido
    data = {
        "recipient": "not-an-email"
    }
    
    # Validar deve falhar
    with pytest.raises(BadRequest):
        validate_request(data, TestSmtpRequest)

def test_clear_flags_request_validation():
    """Testa a validação do esquema ClearFlagsRequest"""
    # Dados válidos
    data = {
        "csv_file": "test.csv"
    }
    
    # Validar
    validated = validate_request(data, ClearFlagsRequest)
    
    # Verificar campos
    assert validated["csv_file"] == "test.csv"

def test_sync_unsubscribed_request_validation():
    """Testa a validação do esquema SyncUnsubscribedRequest"""
    # Dados válidos
    data = {
        "csv_file": "test.csv",
        "unsubscribe_file": "unsubscribe.csv"
    }
    
    # Validar
    validated = validate_request(data, SyncUnsubscribedRequest)
    
    # Verificar campos
    assert validated["csv_file"] == "test.csv"
    assert validated["unsubscribe_file"] == "unsubscribe.csv"

def test_sync_unsubscribed_request_validation_with_defaults():
    """Testa a validação do esquema SyncUnsubscribedRequest com valores padrão"""
    # Dados com apenas csv_file
    data = {
        "csv_file": "test.csv"
    }
    
    # Validar
    validated = validate_request(data, SyncUnsubscribedRequest)
    
    # Verificar campos e valores padrão
    assert validated["csv_file"] == "test.csv"
    assert validated["unsubscribe_file"] == "data/descadastros.csv"  # Valor padrão

def test_report_data_creation():
    """Testa a criação de objeto ReportData"""
    # Criar objeto
    report = ReportData(
        total_sent=10,
        successful=8,
        failed=2,
        duracao_formatada="00:00:05",
        report="Test report",
        report_file="report.html"
    )
    
    # Verificar campos
    assert report.total_sent == 10
    assert report.successful == 8
    assert report.failed == 2
    assert report.duracao_formatada == "00:00:05"
    assert report.report == "Test report"
    assert report.report_file == "report.html"

def test_send_email_response_creation():
    """Testa a criação de objeto SendEmailResponse"""
    # Criar objeto de relatório
    report = ReportData(
        total_sent=10,
        successful=8,
        failed=2,
        duracao_formatada="00:00:05",
        report="Test report",
        report_file="report.html"
    )
    
    # Criar resposta
    response = SendEmailResponse(report=report)
    
    # Verificar campos
    assert response.report.total_sent == 10
    assert response.report.successful == 8
    assert response.report.failed == 2
    assert response.report.duracao_formatada == "00:00:05"

def test_clear_flags_response_creation():
    """Testa a criação de objeto ClearFlagsResponse"""
    # Criar resposta
    response = ClearFlagsResponse(rows_affected=15)
    
    # Verificar campos
    assert response.rows_affected == 15

def test_sync_unsubscribed_response_creation():
    """Testa a criação de objeto SyncUnsubscribedResponse"""
    # Criar resposta
    response = SyncUnsubscribedResponse(rows_synced=5)
    
    # Verificar campos
    assert response.rows_synced == 5

def test_api_response_creation():
    """Testa a criação de objeto ApiResponse"""
    # Criar resposta genérica
    response = ApiResponse(status="success", message="Operação concluída")
    
    # Verificar campos
    assert response.status == "success"
    assert response.message == "Operação concluída"

def test_to_dict_handles_nested_objects():
    """Testa que a função to_dict lida com objetos aninhados"""
    # Criar objeto aninhado
    report = ReportData(
        total_sent=10,
        successful=8,
        failed=2,
        duracao_formatada="00:00:05"
    )
    response = SendEmailResponse(report=report)
    
    # Converter para dict
    result = to_dict(response)
    
    # Verificar resultado
    assert isinstance(result, dict)
    assert "report" in result
    assert isinstance(result["report"], dict)
    assert result["report"]["total_sent"] == 10
    assert result["report"]["successful"] == 8

def test_to_dict_handles_none_values():
    """Testa que a função to_dict lida com valores None"""
    # Criar objeto com campos opcionais não definidos
    report = ReportData(
        total_sent=10,
        successful=8,
        failed=2,
        duracao_formatada="00:00:05",
        report=None,
        report_file=None
    )
    
    # Converter para dict
    result = to_dict(report)
    
    # Verificar resultado
    assert isinstance(result, dict)
    assert result["report"] is None
    assert result["report_file"] is None

def test_validate_request_handles_extra_fields():
    """Testa que validate_request ignora campos extras"""
    # Dados com campos adicionais
    data = {
        "csv_file": "test.csv",
        "template": "template.html",
        "campo_extra": "valor_extra"
    }
    
    # Validar
    validated = validate_request(data, SendEmailRequest)
    
    # Verificar que apenas os campos definidos no modelo são incluídos
    assert validated["csv_file"] == "test.csv"
    assert validated["template"] == "template.html"
    assert "campo_extra" not in validated 