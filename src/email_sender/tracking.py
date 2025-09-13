"""
Sistema de tracking de emails para Treineinsite.

Este módulo implementa o tracking de abertura e clicks de emails através de:
- Pixel de tracking invisível para detectar abertura de emails
- Reescrita de links para tracking de clicks com redirecionamento
- Integração com banco de dados para logging de eventos
"""

import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import quote, unquote, urlparse, parse_qs, urlencode, urlunparse

log = logging.getLogger("email_sender")


class EmailTracker:
    """Gerencia tracking de emails através de pixels e reescrita de links."""
    
    def __init__(self, base_url: str):
        """
        Inicializa o tracker de emails.
        
        Args:
            base_url: URL base da API de tracking (ex: "https://api.exemplo.com")
        """
        self.base_url = base_url.rstrip('/')
        
    def inject_tracking_pixel(self, html_content: str, contact_id: int, message_id: int) -> str:
        """
        Injeta pixel de tracking invisível no HTML para detectar abertura.
        
        Args:
            html_content: Conteúdo HTML do email
            contact_id: ID do contato
            message_id: ID da mensagem
            
        Returns:
            HTML com pixel de tracking injetado
        """
        tracking_url = f"{self.base_url}/api/tracking/open?contact_id={contact_id}&message_id={message_id}"
        pixel_html = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" alt="">'
        
        # Tenta injetar antes do fechamento do body
        if '</body>' in html_content.lower():
            html_content = re.sub(
                r'</body>',
                f'{pixel_html}</body>',
                html_content,
                flags=re.IGNORECASE
            )
        else:
            # Se não há tag body, adiciona no final
            html_content += pixel_html
            
        return html_content
    
    def rewrite_links_for_tracking(self, html_content: str, contact_id: int, message_id: int) -> str:
        """
        Este método foi desativado e agora apenas retorna o conteúdo original.
        Mantido para compatibilidade com código existente.
        """
        return html_content
    
    def process_email_for_tracking(self, html_content: str, contact_id: int, message_id: int) -> str:
        """
        Processa email para tracking: injeta apenas o pixel de abertura.
        
        Args:
            html_content: Conteúdo HTML do email
            contact_id: ID do contato  
            message_id: ID da mensagem
            
        Returns:
            HTML processado com tracking de abertura
        """
        # Agora apenas injeta o pixel, sem reescrita de links
        html_content = self.inject_tracking_pixel(html_content, contact_id, message_id)
        
        return html_content


class TrackingUrlValidator:
    """Valida URLs de redirect para evitar ataques de redirecionamento."""
    
    def __init__(self, allowed_domains: Optional[list] = None):
        """
        Inicializa validador.
        
        Args:
            allowed_domains: Lista de domínios permitidos. Se None, permite todos os HTTPS.
        """
        self.allowed_domains = allowed_domains or []
        
    def is_safe_url(self, url: str) -> bool:
        """
        Verifica se URL é segura para redirecionamento.
        
        Args:
            url: URL para validar
            
        Returns:
            True se URL é segura
        """
        try:
            parsed = urlparse(url)
            
            # Deve ter esquema válido
            if parsed.scheme not in ['http', 'https']:
                return False
                
            # Se há lista de domínios permitidos, verificar
            if self.allowed_domains:
                domain = parsed.netloc.lower()
                return any(
                    domain == allowed.lower() or 
                    domain.endswith('.' + allowed.lower())
                    for allowed in self.allowed_domains
                )
                
            # Caso contrário, permite HTTPS e HTTP para localhost/IPs privados
            if parsed.scheme == 'https':
                return True
                
            # HTTP apenas para desenvolvimento local
            if parsed.scheme == 'http':
                hostname = parsed.hostname
                if hostname in ['localhost', '127.0.0.1'] or hostname.startswith('192.168.'):
                    return True
                    
            return False
            
        except Exception:
            return False


def extract_tracking_params(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrai e valida parâmetros de tracking de query string.
    
    Args:
        query_params: Parâmetros da query string
        
    Returns:
        Dicionário com parâmetros validados
    """
    result = {}
    
    # contact_id (obrigatório)
    contact_id = query_params.get('contact_id')
    if contact_id:
        try:
            result['contact_id'] = int(contact_id)
        except (ValueError, TypeError):
            pass
            
    # message_id (obrigatório)  
    message_id = query_params.get('message_id')
    if message_id:
        try:
            result['message_id'] = int(message_id)
        except (ValueError, TypeError):
            pass
            
    # url (para clicks)
    url = query_params.get('url')
    if url:
        try:
            result['url'] = unquote(str(url))
        except Exception:
            pass
            
    return result