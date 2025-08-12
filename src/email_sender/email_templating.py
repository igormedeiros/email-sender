import re
import logging
from pathlib import Path
from typing import Dict, Any

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
        # Tenta obter as configurações de email de diferentes atributos do objeto config
        # Por ordem de prioridade
        self.content_config = {}
        
        # Verifica se há content_config no objeto principal
        content_config_dict = getattr(config, 'content_config', None)
        if isinstance(content_config_dict, dict):
            self.content_config = content_config_dict
            log.debug(f"TemplateProcessor initialized with content_config: {list(self.content_config.keys())}")
            return
            
        # Tenta email_config como segunda opção
        email_config_dict = getattr(config, 'email_config', None)
        if isinstance(email_config_dict, dict):
            self.content_config = email_config_dict
            log.debug(f"TemplateProcessor initialized with email_config: {list(self.content_config.keys())}")
            return
            
        # Se o config passado for um dicionário, usa ele diretamente
        if isinstance(config, dict):
            self.content_config = config
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
        # URLs from urls_config (derived from self.content_config.get("urls"))
        html_content = html_content.replace("{unsubscribe_url}", urls_config.get("unsubscribe", ""))
        html_content = html_content.replace("{subscribe_url}", urls_config.get("subscribe", ""))

        # Recipient email (mandatory placeholder)
        if 'email' in recipient:
            html_content = html_content.replace("{email}", str(recipient['email']))
        else:
            log.debug("Recipient data is missing 'email' field for {email} placeholder.")

        # Event specific placeholders from self.content_config
        evento_config = self.content_config.get("evento", {})
        
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
            parts = [p.strip() for p in re.split(r"\s+a\s+", raw)]
            if len(parts) == 1:
                y, m, d = _parse_ymd(parts[0])
                if all(v is not None for v in (y, m, d)):
                    from datetime import date as _date
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
                from datetime import date as _date
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
            from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
            link_raw = str(evento_config.get("link", ""))
            coupon_code = str(evento_config.get("cupom") or "")
            if link_raw:
                parts = urlparse(link_raw)
                query_map = dict(parse_qsl(parts.query, keep_blank_values=True))
                # Somente forçar o cupom se fornecido
                if coupon_code:
                    query_map["d"] = coupon_code
                new_query = urlencode(query_map, doseq=True)
                link_with_coupon = urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
            else:
                link_with_coupon = link_raw
        except Exception:
            # Fallback simples caso parsing falhe
            if link_raw:
                joiner = "&" if ("?" in link_raw) else "?"
                link_with_coupon = f"{link_raw}{joiner}d={coupon_code}" if coupon_code else link_raw
            else:
                link_with_coupon = ""
        html_content = html_content.replace("{link_evento}", link_with_coupon)
        data_raw = str(evento_config.get("data", "") or "")
        data_human = _format_ptbr_date_range_from_str(data_raw)
        html_content = html_content.replace("{data_evento}", data_human)
        html_content = html_content.replace("{cidade}", evento_config.get("cidade", ""))
        html_content = html_content.replace("{local}", evento_config.get("local", ""))

        # Conditional discount paragraph from self.content_config
        desconto_paragrafo = ""
        promocao_config = self.content_config.get("promocao", {})
        if "desconto" in promocao_config:
            desconto_paragrafo = promocao_config.get(
                "paragrafo_desconto",
                f"Aproveite nosso desconto de {promocao_config['desconto']}!"
            )
        html_content = html_content.replace("{desconto_paragrafo}", desconto_paragrafo)

        # Generic placeholders from the main level of self.content_config
        for key, value in self.content_config.items():
            if isinstance(value, str):
                html_content = html_content.replace(f"{{{key}}}", value)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        html_content = html_content.replace(f"{{{key}.{sub_key}}}", sub_value)

        # Substitute remaining placeholders from recipient data
        remaining_placeholders = re.findall(r'\{([^}]+)\}', html_content)
        for placeholder in remaining_placeholders:
            if placeholder in recipient:
                html_content = html_content.replace(f"{{{placeholder}}}", str(recipient[placeholder]))
            else:
                known_config_placeholders = ["unsubscribe_url", "subscribe_url", "link_evento", "data_evento", "cidade", "local", "desconto_paragrafo"] \
                                            + list(self.content_config.keys()) \
                                            + [f"{k}.{sk}" for k, v in self.content_config.items() if isinstance(v, dict) for sk in v.keys()]
                if placeholder not in known_config_placeholders and placeholder != "email":
                    log.debug(f"Placeholder {{{placeholder}}} not found in recipient data or specific config sections.")

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
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # Get URLs from self.content_config (which should now be the correct email dict)
            urls_config = self.content_config.get("urls", {})
            
            html_content = self._replace_placeholders(html_content, recipient, urls_config)

            css_file_path_str = self.content_config.get("css_file")
            
            if css_file_path_str:
                css_path = Path(css_file_path_str)
                if css_path.exists():
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
                        html_content = pm.transform()
                        log.debug(f"CSS inlined successfully from {css_path}")
                    except ImportError:
                        log.warning("Premailer library not installed. CSS will not be inlined. pip install premailer")
                    except Exception as e_css:
                        log.error(f"Error inlining CSS from {css_path}: {e_css}")
                else:
                    log.warning(f"CSS file not found: {css_path}")
            
            return html_content
        except FileNotFoundError:
            log.error(f"Template file not found: {template_path}")
            raise
        except Exception as e:
            log.error(f"Error processing template {template_path} for recipient {recipient.get('email', 'N/A')}: {e}")
            import traceback
            log.debug(traceback.format_exc())
            raise
