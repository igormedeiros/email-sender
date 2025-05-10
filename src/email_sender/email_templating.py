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
        html_content = html_content.replace("{link_evento}", evento_config.get("link", ""))
        html_content = html_content.replace("{data_evento}", evento_config.get("data", ""))
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
