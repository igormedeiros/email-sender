from configparser import ConfigParser
from pathlib import Path
import yaml
import os
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from .utils.secrets_manager import SecretsManager, SecretSource

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
            
        # Inicializar o gerenciador de segredos
        self._init_secrets_manager()
        
        # Carregar modo de ambiente da variável ENVIRONMENT
        self._environment = os.getenv("ENVIRONMENT", "test").strip().lower()
        if self._environment not in {"test", "prod", "production"}:
            logger.warning("ENVIRONMENT inválido: %s. Usando 'test' por padrão.", self._environment)
            self._environment = "test"
            
    def _init_secrets_manager(self):
        """Inicializa o gerenciador de segredos com base nas configurações"""
        # Determinar a fonte de segredos a ser usada
        secret_source_str = os.getenv("SECRET_SOURCE", "env").lower()
        
        # Mapear string para enum
        source_map = {
            "env": SecretSource.ENV,
            "dotenv": SecretSource.DOTENV,
            "aws": SecretSource.AWS_SECRETS,
            "azure": SecretSource.AZURE_KEYVAULT,
            "vault": SecretSource.VAULT
        }
        
        source = source_map.get(secret_source_str, SecretSource.ENV)
        
        # Obter configurações específicas para cada fonte
        dotenv_path = os.getenv("DOTENV_PATH", ".env")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        azure_vault_url = os.getenv("AZURE_VAULT_URL")
        vault_url = os.getenv("VAULT_URL")
        
        # Valores padrão das configurações YAML para fallback
        config_defaults = {}
        if "smtp" in self.config:
            config_defaults["SMTP_USERNAME"] = self.config["smtp"].get("username", "")
            config_defaults["SMTP_PASSWORD"] = self.config["smtp"].get("password", "")
        
        # Criar o gerenciador de segredos
        self.secrets_manager = SecretsManager(
            source=source,
            dotenv_path=dotenv_path,
            aws_region=aws_region,
            azure_vault_url=azure_vault_url,
            vault_url=vault_url,
            config_defaults=config_defaults
        )
        
        # Log da fonte de segredos sendo usada
        logger.info(f"Usando fonte de segredos: {source.value}")

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
        # Obter credenciais do gerenciador de segredos
        smtp_credentials = self.secrets_manager.get_smtp_credentials()
        
        return {
            "host": self.config["smtp"].get("host", ""),
            "port": int(self.config["smtp"].get("port", 587)),
            "username": smtp_credentials["username"],
            "password": smtp_credentials["password"],
            "use_tls": self.config["smtp"].get("use_tls", True),
            "retry_attempts": int(self.config["smtp"].get("retry_attempts", 3)),
            "retry_delay": int(self.config["smtp"].get("retry_delay", 5)),
            "send_timeout": int(self.config["smtp"].get("send_timeout", 10))
        }

    @property
    def email_config(self) -> dict:
        return {
            "sender": self.config["email"].get("sender", ""),
            "batch_size": int(self.config["email"].get("batch_size", 10)),
            "test_recipient": self.config["email"].get("test_recipient"),
            "batch_delay": int(self.config["email"].get("batch_delay", 60)),
            "public_domain": self.config["email"].get("public_domain", "mkt.treineinsite.com.br"),
        }

    @property
    def content_config(self) -> dict:
        """Retorna a configuração de conteúdo dinâmico para os templates de email"""
        return self.email_content
        
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