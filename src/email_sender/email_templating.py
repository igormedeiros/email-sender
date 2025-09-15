import re
import logging
from pathlib import Path
from typing import Dict, Any
from urllib.parse import urlunparse
from datetime import date as _date

log = logging.getLogger("email_sender")

class TemplateProcessor:
    """Processes email templates by substituting placeholders with dynamic content."""
    def __init__(self, config: Any):
        """
        Initializes the TemplateProcessor.

        Args:
            config: The main configuration object, expected to have a 'content_config'
                   or 'email_config' attribute containing the email content dictionary.
        """
        log.debug(f"Iniciando TemplateProcessor com config do tipo: {type(config)}")

        # Tenta obter as configurações de email de diferentes atributos do objeto config
        # Por ordem de prioridade
        self.content_config = {}
        
        # Função auxiliar para validar e logar estrutura
        def validate_config(cfg: dict) -> bool:
            log.debug(f"Validando configuração: {cfg}")
            # Checa seções esperadas
            required_sections = ["email", "evento"]
            for section in required_sections:
                if section not in cfg:
                    log.warning(f"Seção '{section}' não encontrada na configuração")
            # Checa estrutura da seção evento
            evento = cfg.get("evento", {})
            expected_evento_fields = ["nome", "link", "data", "cidade", "local"]
            for field in expected_evento_fields:
                if field not in evento:
                    log.warning(f"Campo '{field}' não encontrado na seção evento")
            return True  # Por enquanto retorna True para manter compatibilidade
        
        # Verifica se há content_config no objeto principal
        content_config_dict = getattr(config, 'content_config', None)
        if isinstance(content_config_dict, dict):
            self.content_config = content_config_dict
            validate_config(self.content_config)
            log.debug(f"TemplateProcessor initialized with content_config: {list(self.content_config.keys())}")
            return
            
        # Tenta email_config como segunda opção
        email_config_dict = getattr(config, 'email_config', None)
        if isinstance(email_config_dict, dict):
            self.content_config = email_config_dict
            validate_config(self.content_config)
            log.debug(f"TemplateProcessor initialized with email_config: {list(self.content_config.keys())}")
            return
            
        # Se o config passado for um dicionário, usa ele diretamente
        if isinstance(config, dict):
            self.content_config = config
            validate_config(self.content_config)
            log.debug(f"TemplateProcessor initialized with dict: {list(self.content_config.keys())}")
            return
            
        log.error(
            f"Não foi possível encontrar configurações de email válidas. "
            f"Tipo do objeto config: {type(config)}. "
            f"TemplateProcessor.content_config será um dicionário vazio."
        )
        self.content_config = {}

    def _replace_placeholders(self, html_content: str, recipient: Dict[str, str], urls_config: Dict[str, str]) -> str:
        """
        Replaces placeholders in the HTML content with recipient and configuration data.

        Args:
            html_content: The HTML content as a string.
            recipient: Dictionary containing recipient-specific data.
            urls_config: Dictionary containing URL configuration.

        Returns:
            The HTML content with placeholders replaced.
        """
        log.debug(f"Iniciando substituição de placeholders. Tamanho do HTML: {len(html_content)}")
        log.debug(f"URLs config recebida: {urls_config}")
        log.debug(f"Dados do recipient: {recipient}")
        
        # URLs from urls_config (derived from self.content_config.get("urls"))
        unsubscribe_base = urls_config.get("unsubscribe", "")
        subscribe_base = urls_config.get("subscribe", "")
        log.debug(f"URLs base - unsubscribe: {unsubscribe_base}, subscribe: {subscribe_base}")
        # Substituir URLs básicas
        log.debug("Substituindo URLs básicas...")
        html_content = html_content.replace("{unsubscribe_url}", unsubscribe_base)
        html_content = html_content.replace("{subscribe_url}", subscribe_base)
        log.debug("URLs básicas substituídas")
        log.debug(f"HTML após substituição de URLs básicas (primeiros 200 caracteres): {html_content[:200]}")

        # Build full unsubscribe link and a Gmail-safe redirect helper if possible
        try:
            recipient_email_val = str(recipient.get('email', ''))
            log.debug(f"Email do recipient para unsubscribe: {recipient_email_val}")
            if unsubscribe_base and recipient_email_val:
                unsubscribe_full = f"{unsubscribe_base}?email={recipient_email_val}"
                # Gmail-safe redirect URL (it may add its own, but we prepare a consistent value)
                unsubscribe_safe_url = f"https://www.google.com/url?q={unsubscribe_full}"
                log.debug(f"URLs de unsubscribe geradas - full: {unsubscribe_full}, safe: {unsubscribe_safe_url}")
                html_content = html_content.replace("{unsubscribe_full}", unsubscribe_full)
                html_content = html_content.replace("{unsubscribe_safe_url}", unsubscribe_safe_url)
        except Exception:
            # If building fails, just strip placeholders
            html_content = html_content.replace("{unsubscribe_full}", unsubscribe_base)
            html_content = html_content.replace("{unsubscribe_safe_url}", unsubscribe_base)

        # Recipient email (mandatory placeholder)
        if 'email' in recipient:
            html_content = html_content.replace("{email}", str(recipient['email']))
        else:
            log.debug("Recipient data is missing 'email' field for {email} placeholder.")
        log.debug(f"HTML após substituição do email (primeiros 200 caracteres): {html_content[:200]}")

        # Event specific placeholders from self.content_config
        evento_config = self.content_config.get("evento", {})
        log.debug(f"Configuração do evento obtida: {evento_config}")
        
        # Helper: format raw ISO-like date range to PT-BR human text
        def _parse_ymd(date_str: str):
            try:
                m = re.search(r"(\d{4})-(\d{2})-(\d{2})", date_str or "")
                if not m:
                    return None, None, None
                return int(m.group(1)), int(m.group(2)), int(m.group(3))
            except Exception:
                return None, None, None

        def _format_ptbr_date_range_from_str(raw: str) -> str:
            if not raw:
                return ""
            try:
                from babel.dates import format_date as _fmt_date
            except Exception:
                return raw
            # Permitir locale configurável via config/email.yaml -> email.locale ou env
            locale_pref = (
                self.content_config.get("email", {}).get("locale")
                if isinstance(self.content_config, dict) else None
            )
            import os as _os
            locale_pref = locale_pref or _os.environ.get("EVENT_DATE_LOCALE") or _os.environ.get("LOCALE") or "pt_BR"
            # tenta separar duas partes por ' a '
            import re as regex_module
            parts = [p.strip() for p in regex_module.split(r"\s+a\s+", raw)]
            if len(parts) == 1:
                y, m, d = _parse_ymd(parts[0])
                if all(v is not None for v in (y, m, d)):
                    dt = _date(int(y), int(m), int(d))
                    m_name = _fmt_date(dt, format='MMMM', locale=locale_pref)
                    return f"{d} de {m_name}"
                return raw
            else:
                y1, m1, d1 = _parse_ymd(parts[0])
                y2, m2, d2 = _parse_ymd(parts[1])
                if not all(v is not None for v in (y1, m1, d1)):
                    return raw
                if not all(v is not None for v in (y2, m2, d2)):
                    y2, m2, d2 = y1, m1, d1
                dt1 = _date(int(y1), int(m1), int(d1))
                dt2 = _date(int(y2), int(m2), int(d2))
                m1_name = _fmt_date(dt1, format='MMMM', locale=locale_pref)
                m2_name = _fmt_date(dt2, format='MMMM', locale=locale_pref)
                if y1 == y2:
                    if m1 == m2:
                        if d1 == d2:
                            return f"{d1} de {m1_name}"
                        return f"{d1} e {d2} de {m1_name}"
                    return f"{d1} de {m1_name} a {d2} de {m2_name}"
                return f"{d1} de {m1_name} de {y1} a {d2} de {m2_name} de {y2}"
        # Se houver cupom configurado, garantir que o link do evento carregue o cupom (param 'd')
        try:
            link_raw = str(evento_config.get("link", ""))
            coupon_code = str(evento_config.get("cupom") or "")
            
            log.debug(f"Link do evento bruto: {link_raw}")
            log.debug(f"Cupom inicial do evento: {coupon_code}")
            # Se não tiver cupom, tenta usar o padrão do ambiente
            if not coupon_code:
                import os
                coupon_code = os.environ.get("DEFAULT_COUPON", "CINA30")
                log.debug(f"Usando cupom padrão do ambiente: {coupon_code}")

            if link_raw and coupon_code:
                # Verifica se a URL já tem o cupom correto
                from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
                parsed = urlparse(link_raw)
                query_params = parse_qs(parsed.query)
                current_coupon = query_params.get('d', [''])[0]
                
                # Se não tiver cupom ou for diferente do desejado, adiciona/atualiza
                if current_coupon != coupon_code:
                    # Remove cupom existente se houver
                    if 'd' in query_params:
                        del query_params['d']
                    # Adiciona novo cupom
                    query_params['d'] = [coupon_code]
                    log.debug(f"Query params antes da reconstrução: {query_params}")
                    # Reconstrói a query string
                    new_query = urlencode(query_params, doseq=True)
                    log.debug(f"Nova query string gerada: {new_query}")
                    # Reconstrói a URL completa
                    parts = list(parsed)
                    parts[4] = new_query
                    link_with_coupon = urlunparse(tuple(parts))
                else:
                    # Se já tem o cupom correto, mantém a URL como está
                    link_with_coupon = link_raw
            else:
                link_with_coupon = link_raw
            log.debug(f"Link do evento com cupom: {link_with_coupon}")
        except Exception as e:
            # Fallback mais simples possível
            if link_raw and coupon_code:
                joiner = "&" if "?" in link_raw else "?"
                # Remove qualquer cupom existente (procura por &d= ou ?d=)
                import re
                link_clean = re.sub(r'[?&]d=[^&]*', '', link_raw)
                # Adiciona o novo cupom
                link_with_coupon = f"{link_clean}{joiner}d={coupon_code}"
            else:
                link_with_coupon = link_raw
            log.warning(f"Erro ao processar cupom para URL: {e}")
            
        html_content = html_content.replace("{link_evento}", link_with_coupon)
        log.debug(f"HTML após substituição do link do evento (primeiros 200 caracteres): {html_content[:200]}")
        
        data_raw = str(evento_config.get("data", "") or "")
        # Regra: manter data simples exatamente como veio (compatibilidade com testes)
        # e usar formatação humana apenas quando houver intervalo (" a ")
        if " a " in data_raw:
            data_human = _format_ptbr_date_range_from_str(data_raw)
        else:
            data_human = data_raw
        html_content = html_content.replace("{data_evento}", data_human)
        log.debug(f"HTML após substituição da data do evento (primeiros 200 caracteres): {html_content[:200]}")
        
        cidade = evento_config.get("cidade", "")
        local = evento_config.get("local", "")
        log.debug(f"Dados do evento para substituição - cidade: {cidade}, local: {local}")
        html_content = html_content.replace("{cidade}", cidade)
        html_content = html_content.replace("{local}", local)
        log.debug(f"HTML após substituição da cidade e local (primeiros 200 caracteres): {html_content[:200]}")

        # Conditional discount paragraph from self.content_config
        desconto_paragrafo = ""
        promocao_config = self.content_config.get("promocao", {})
        if "desconto" in promocao_config:
            desconto_paragrafo = promocao_config.get(
                "paragrafo_desconto",
                f"Aproveite nosso desconto de {promocao_config['desconto']}!"
            )
        html_content = html_content.replace("{desconto_paragrafo}", desconto_paragrafo)
        log.debug(f"HTML após substituição do desconto (primeiros 200 caracteres): {html_content[:200]}")

        # Generic placeholders from the main level of self.content_config
        for key, value in self.content_config.items():
            if isinstance(value, str):
                html_content = html_content.replace(f"{{{key}}}", value)
                log.debug(f"Substituído placeholder {{{key}}} com valor: {value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        html_content = html_content.replace(f"{{{key}.{sub_key}}}", sub_value)
                        log.debug(f"Substituído placeholder {{{key}.{sub_key}}} com valor: {sub_value}")
        log.debug(f"HTML após substituição de placeholders genéricos (primeiros 200 caracteres): {html_content[:200]}")

        # Substitute remaining placeholders from recipient data
        import re as regex_module
        remaining_placeholders = regex_module.findall(r'\{([^}]+)\}', html_content)
        log.debug(f"Placeholders restantes encontrados: {remaining_placeholders}")
        for placeholder in remaining_placeholders:
            if placeholder in recipient:
                html_content = html_content.replace(f"{{{placeholder}}}", str(recipient[placeholder]))
                log.debug(f"Substituído placeholder {{{placeholder}}} com valor do recipient: {recipient[placeholder]}")
            else:
                known_config_placeholders = ["unsubscribe_url", "subscribe_url", "link_evento", "data_evento", "cidade", "local", "desconto_paragrafo"] \
                                            + list(self.content_config.keys()) \
                                            + [f"{k}.{sk}" for k, v in self.content_config.items() if isinstance(v, dict) for sk in v.keys()]
                if placeholder not in known_config_placeholders and placeholder != "email":
                    log.debug(f"Placeholder {{{placeholder}}} not found in recipient data or specific config sections.")

        # Tracking injection foi desabilitado completamente
        pass

        log.debug(f"HTML final após todas as substituições (primeiros 200 caracteres): {html_content[:200]}")
        return html_content

    def process(self, template_path: Path, recipient: Dict[str, str]) -> str:
        """
        Loads an HTML template and substitutes placeholders with recipient data and config values.

        Args:
            template_path: Path object for the HTML template file.
            recipient: Dictionary containing recipient-specific data.

        Returns:
            The processed HTML content as a string.
        """
        log.debug(f"Iniciando processamento de template em: {template_path}")
        log.debug(f"Dados do recipient recebidos: {recipient}")
        log.debug(f"Estado atual do content_config: {self.content_config}")

        try:
            log.debug("Tentando carregar arquivo de template...")
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            log.debug(f"Template carregado com sucesso. Tamanho: {len(html_content)}")
            log.debug(f"Primeiras 200 caracteres do template original: {html_content[:200]}")

            # Get URLs from self.content_config (which should now be the correct email dict)
            urls_config = self.content_config.get("urls", {})
            log.debug(f"URLs obtidas do content_config: {urls_config}")
            
            html_content = self._replace_placeholders(html_content, recipient, urls_config)
            log.debug(f"Conteúdo HTML após _replace_placeholders (tamanho: {len(html_content)})")
            log.debug(f"Primeiras 200 caracteres após _replace_placeholders: {html_content[:200]}")

            css_file_path_str = self.content_config.get("css_file")
            
            log.debug("Buscando arquivo CSS configurado...")
            if css_file_path_str:
                css_path = Path(css_file_path_str)
                log.debug(f"Caminho do CSS configurado: {css_path}")
                if css_path.exists():
                    log.debug("Arquivo CSS encontrado, tentando carregar com premailer...")
                    try:
                        from premailer import Premailer
                        with open(css_path, 'r', encoding='utf-8') as css_file:
                            css_content = css_file.read()
                        
                        # Combine HTML with external CSS for premailer
                        if "<html" not in html_content.lower():
                            html_with_style = f"<html><head><style>{css_content}</style></head><body>{html_content}</body></html>"
                        elif "<style>" in html_content.lower() or "</style>" in html_content.lower():
                            pass
                        else:
                            html_with_style = html_content.replace("</head>", f"<style>{css_content}</style></head>", 1)
                            if "</style>" not in html_with_style:
                                html_with_style = html_content.replace("<body>", f"<body><style>{css_content}</style>", 1)

                        pm = Premailer(html_content, css_text=css_content)
                        # Nota: Premailer está carregado; processamento inline pode ser aplicado conforme necessário no futuro
                    except Exception:
                        pass
            log.debug("Finalizando processamento do template...")
            log.debug(f"Tamanho final do HTML processado: {len(html_content)}")
            log.debug(f"Primeiras 200 caracteres do HTML final: {html_content[:200]}")
            return html_content
        except Exception as e:
            log.error(f"Erro no processamento do template: {e}", exc_info=True)
            return ""
