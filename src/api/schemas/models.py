"""
Models para validação de entrada e saída da API.
Utiliza dataclasses para tipagem estática e validação.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from marshmallow import Schema, fields

class SendMode(str, Enum):
    TEST = "test"
    PRODUCTION = "production"

@dataclass
class ApiResponse:
    """Resposta padrão da API"""
    status: str
    message: str
    
@dataclass
class SendEmailRequest:
    """Requisição para envio de emails"""
    template: str
    mode: SendMode
    csv_file: Optional[str] = None
    skip_unsubscribed_sync: bool = False
    
@dataclass
class ReportData:
    """Dados do relatório de envio"""
    report_file: str
    duration: float
    avg_time: float
    total_sent: int
    successful: int
    failed: int

@dataclass
class SendEmailResponse(ApiResponse):
    """Resposta do envio de emails"""
    report: ReportData
    
@dataclass
class TestSmtpRequest:
    """Requisição para teste SMTP"""
    recipient: Optional[str] = None
    
@dataclass
class ClearFlagsRequest:
    """Requisição para limpar flags de envio"""
    csv_file: Optional[str] = None
    
@dataclass
class ClearFlagsResponse(ApiResponse):
    """Resposta da limpeza de flags"""
    cleared_count: int
    
@dataclass
class SyncUnsubscribedRequest:
    """Requisição para sincronizar emails descadastrados"""
    csv_file: Optional[str] = None
    unsubscribe_file: Optional[str] = None
    
@dataclass
class SyncUnsubscribedResponse(ApiResponse):
    """Resposta da sincronização de emails descadastrados"""
    csv_file: str
    unsubscribe_file: str
    updated_count: int
    
def validate_request(data: Dict, model_class) -> Any:
    """
    Valida os dados de entrada de acordo com o modelo especificado.
    
    Args:
        data: Dados de entrada (geralmente do request.json)
        model_class: Classe do modelo para validação
        
    Returns:
        Instância do modelo com os dados validados
    
    Raises:
        ValueError: Se os dados não forem válidos para o modelo
    """
    try:
        # Remover campos None ou vazios que não sejam obrigatórios
        clean_data = {k: v for k, v in data.items() if v is not None}
        
        # Converter SendMode se necessário
        if model_class == SendEmailRequest and 'mode' in clean_data:
            clean_data['mode'] = SendMode(clean_data['mode'])
            
        # Criar instância do modelo
        return model_class(**clean_data)
    except TypeError as e:
        raise ValueError(f"Dados inválidos: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Valores inválidos: {str(e)}")
        
def to_dict(obj: Any) -> Dict:
    """
    Converte um objeto para dicionário.
    
    Args:
        obj: Objeto a ser convertido
        
    Returns:
        Dicionário representando o objeto
    """
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for field_name in obj.__dataclass_fields__:
            value = getattr(obj, field_name)
            if isinstance(value, Enum):
                result[field_name] = value.value
            elif hasattr(value, "__dataclass_fields__"):
                result[field_name] = to_dict(value)
            else:
                result[field_name] = value
        return result
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj 

class LoginSchema(Schema):
    """Schema para validação de dados de login"""
    username = fields.String(required=True)
    password = fields.String(required=True)

class TokenResponseSchema(Schema):
    """Schema para resposta contendo tokens"""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=False)
    token_type = fields.String(required=True)
    expires_in = fields.Integer(required=False) 