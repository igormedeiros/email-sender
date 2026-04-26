from configparser import ConfigParser
from pathlib import Path
import yaml
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_file: str = "config/config.yaml", email_content_file: str = "config/email.yaml", rest_config_file: str = "config/rest.yaml"):
        # Carregar variáveis de ambiente do arquivo .env
        load_dotenv()

        self.config_file = config_file
        self.email_content_file = email_content_file
        self.rest_config_file = rest_config_file

        # Carregar configurações a partir do arquivo YAML
        if config_file.endswith('.yaml') or config_file.endswith('.yml'):
            with open(config_file, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
        # Manter compatibilidade com o formato properties anterior
        else:
            config_parser = ConfigParser()
            config_parser.read(config_file)
            self.config = self._convert_parser_to_dict(config_parser)

        # Carregar conteúdo de email do arquivo email.yaml
        try:
            with open(email_content_file, 'r', encoding='utf-8') as file:
                self.email_content = yaml.safe_load(file) or {}
        except FileNotFoundError:
            logger.warning(f"Arquivo de conteúdo de email {email_content_file} não encontrado. Usando valores vazios.")
            self.email_content = {}

        # Carregar configurações REST se existirem
        try:
            if os.path.exists(rest_config_file):
                with open(rest_config_file, 'r', encoding='utf-8') as file:
                    self.rest_config = yaml.safe_load(file) or {}
            else:
                self.rest_config = {}
        except Exception as e:
            logger.error(f"Erro ao carregar configurações REST: {str(e)}")
            self.rest_config = {}

        # Carregar modo de ambiente da variável ENVIRONMENT
        self._environment = os.getenv("ENVIRONMENT", "test").strip().lower()
        if self._environment not in {"test", "prod", "production"}:
            logger.warning("ENVIRONMENT inválido: %s. Usando 'test' por padrão.", self._environment)
            self._environment = "test"

    def _convert_parser_to_dict(self, parser: ConfigParser) -> dict:
        """Converte um ConfigParser para um dicionário"""
        result = {}
        for section in parser.sections():
            result[section] = {}
            for key, value in parser.items(section):
                result[section][key] = value
        return result

    @property
    def smtp_config(self) -> dict:
        # Obter credenciais diretamente das variáveis de ambiente
        smtp_username = os.getenv("SMTP_USERNAME", self.config["smtp"].get("username", ""))
        smtp_password = os.getenv("SMTP_PASSWORD", self.config["smtp"].get("password", ""))

        # Permite a sobreposição do host SMTP via variável de ambiente
        smtp_host = os.getenv("SMTP_HOST_OVERRIDE", self.config["smtp"].get("host", ""))

        return {
            "host": smtp_host,
            "port": int(self.config["smtp"].get("port", 587)),
            "username": smtp_username,
            "password": smtp_password,
            "use_tls": self.config["smtp"].get("use_tls", True),
            "retry_attempts": int(self.config["smtp"].get("retry_attempts", 3)),
            "retry_delay": int(self.config["smtp"].get("retry_delay", 5)),
            "send_timeout": int(self.config["smtp"].get("send_timeout", 3))
        }

    @property
    def email_config(self) -> dict:
        return {
            "sender": self.config["email"].get("sender", ""),
            "batch_size": int(self.config["email"].get("batch_size", 10)),
            "test_recipient": self.config["email"].get("test_recipient"),
            "batch_delay": int(self.config["email"].get("batch_delay", 60)),
            "public_domain": self.config["email"].get("public_domain", "mkt.treineinsite.com.br"),
            "max_workers": int(self.config["email"].get("max_workers", 10)),
            "send_timeout": int(self.config["email"].get("send_timeout", 3)),
        }

    @property
    def content_config(self) -> dict:
        """Retorna a configuração de conteúdo dinâmico para os templates de email"""
        # Criar uma cópia para não modificar o original self.email_content em memória
        content = self.email_content.copy()
        
        # Se houver dados do evento e um cupom definido, anexar ao link
        if "evento" in content and isinstance(content["evento"], dict):
            evento = content["evento"].copy()
            link = evento.get("link")
            cupom = evento.get("cupom")
            
            if link and cupom:
                # Se o link é uma string e o cupom não está presente, anexar
                link = str(link).strip()
                cupom = str(cupom).strip()
                
                if cupom and f"d={cupom}" not in link:
                    # Decidir o separador (? ou &)
                    separator = "&" if "?" in link else "?"
                    evento["link"] = f"{link}{separator}d={cupom}"
                    content["evento"] = evento
        
        return content

    def save_content_config(self):
        """Salva a configuração de conteúdo dinâmico no arquivo email.yaml"""
        try:
            with open(self.email_content_file, 'w', encoding='utf-8') as file:
                yaml.dump(self.email_content, file, allow_unicode=True, sort_keys=False)
            logger.info(f"Configuração de conteúdo salva em {self.email_content_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar configuração de conteúdo: {str(e)}")
            raise
        
    @property
    def rest_api_config(self) -> dict:
        """Retorna a configuração da API REST"""
        return self.rest_config

    @property
    def rest_server_config(self) -> dict:
        """Retorna as configurações do servidor REST"""
        server_config = self.rest_config.get("server", {})
        return {
            "host": server_config.get("host", "0.0.0.0"),
            "port": int(server_config.get("port", 5000)),
            "debug": bool(server_config.get("debug", True))
        }
    
    @property
    def rest_security_config(self) -> dict:
        """Retorna as configurações de segurança da API REST"""
        security_config = self.rest_config.get("security", {})
        return {
            "enable_cors": bool(security_config.get("enable_cors", True)),
            "allowed_origins": security_config.get("allowed_origins", "*")
        }
    
    @property
    def rest_logging_config(self) -> dict:
        """Retorna as configurações de log da API REST"""
        logging_config = self.rest_config.get("logging", {})
        return {
            "level": logging_config.get("level", "INFO"),
            "file": logging_config.get("file", "")
        }
    
    @property
    def logging_config(self) -> dict:
        """Retorna as configurações de log gerais"""
        logging_config = self.config.get("logging", {})
        return {
            "level": logging_config.get("level", "INFO")
        }

    @property
    def rest_timeout_config(self) -> dict:
        """Retorna as configurações de timeout da API REST"""
        timeout_config = self.rest_config.get("timeout", {})
        return {
            "request": int(timeout_config.get("request", 60))
        }

    # ————————————————————————————————————
    # Ambiente e Postgres
    # ————————————————————————————————————
    @property
    def environment_mode(self) -> str:
        """Retorna o modo de ambiente: 'test' ou 'prod'."""
        return "prod" if self._environment in {"prod", "production"} else "test"

    @property
    def postgres_config(self) -> dict:
        """Credenciais/parametros do Postgres vindos do .env.

        Variáveis esperadas:
        - PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
        """
        return {
            "host": os.getenv("PGHOST", "localhost"),
            "port": int(os.getenv("PGPORT", "5432")),
            "user": os.getenv("PGUSER", ""),
            "password": os.getenv("PGPASSWORD", ""),
            "database": os.getenv("PGDATABASE", ""),
        }