import os
import sys
from unittest.mock import patch, MagicMock
import typer
import pytest
from email_sender.email_service import EmailService

def test_subject_regeneration_on_rejection():
    """Testa se a função gera um novo assunto quando o usuário rejeita o primeiro."""
    # Configurar o ambiente para teste
    os.environ['SUBJECT_INTERACTIVE'] = '1'
    
    # Criar um mock para a configuração
    class DummyConfig:
        def __init__(self):
            self._content = {'email': {'template_path': ''}}
            self._email = {}
            # Add email_content attribute for compatibility
            self.email_content = self._content

        @property
        def content_config(self):
            return self._content

        @property
        def email_config(self):
            return self._email

    # Criar uma instância do serviço de email
    svc = EmailService(DummyConfig())
    
    # Substituir a função _generate_subject_for_body por um mock simples
    call_log = []
    
    def mock_generate_subject(body_html, existing_subject=None, temperature=0.6, variation_hint=None):
        call_log.append({
            'existing_subject': existing_subject,
            'temperature': temperature,
            'variation_hint': variation_hint
        })
        # Retornar um assunto diferente a cada chamada
        return f"Assunto gerado {len(call_log)}"
    
    svc._generate_subject_for_body = mock_generate_subject
    
    # Testar a função real com mocks controlados
    with patch('email_sender.email_service.get_console') as mock_console:
        # Criar um mock para o console que não faz nada
        mock_console_instance = MagicMock()
        mock_console_instance.print = MagicMock()
        mock_console.return_value = mock_console_instance
        
        # Mock typer.confirm para retornar False nas duas primeiras chamadas e True na terceira
        confirm_calls = []
        
        def mock_confirm(message, default=True):
            confirm_calls.append(message)
            # Aprovar apenas na terceira chamada
            result = len(confirm_calls) >= 3
            return result
        
        with patch('typer.confirm', side_effect=mock_confirm):
            with patch('sys.stdin.isatty', return_value=True):
                # Chamar a função real
                result = svc._maybe_interactive_subject(
                    "Assunto inicial", 
                    "<html>Conteúdo de teste</html>", 
                    force=True, 
                    show_current_first=False
                )
                
                # Verificar resultados
                assert len(confirm_calls) == 3, f"Esperava 3 chamadas ao typer.confirm, obteve {len(confirm_calls)}"
                assert len(call_log) == 2, f"Esperava 2 chamadas à _generate_subject_for_body, obteve {len(call_log)}"
                assert result == "Assunto gerado 2", f"Esperava resultado 'Assunto gerado 2', obteve '{result}'"
                
                # Verificar que as chamadas à _generate_subject_for_body receberam os parâmetros corretos
                assert call_log[0]['existing_subject'] == "Assunto inicial"
                assert call_log[0]['temperature'] == 0.9
                assert call_log[0]['variation_hint'] == "gere uma variação diferente do anterior, mais curiosa e com benefício específico"
                
                assert call_log[1]['existing_subject'] == "Assunto gerado 1"
                assert call_log[1]['temperature'] == 0.9
                assert call_log[1]['variation_hint'] == "gere uma variação diferente do anterior, mais curiosa e com benefício específico"