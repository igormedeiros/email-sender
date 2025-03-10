from configparser import ConfigParser
from pathlib import Path
import yaml
import os
from dotenv import load_dotenv

class Config:
    def __init__(self, config_file: str = "config/config.yaml", email_content_file: str = "config/email.yaml"):
        # Carregar variáveis de ambiente do arquivo .env
        load_dotenv()
        
        self.config_file = config_file
        self.email_content_file = email_content_file
        
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
            print(f"⚠️ Arquivo de conteúdo de email {email_content_file} não encontrado. Usando valores vazios.")
            self.email_content = {}
    
    def _convert_parser_to_dict(self, parser: ConfigParser) -> dict:
        """Converte um ConfigParser para um dicionário aninhado"""
        result = {}
        for section in parser.sections():
            result[section] = {}
            for key, value in parser.items(section):
                result[section][key] = value
        return result

    @property
    def smtp_config(self) -> dict:
        # Pegar credenciais do arquivo .env, com fallback para os valores do YAML se não estiverem definidos
        smtp_username = os.getenv("SMTP_USERNAME") or self.config["smtp"].get("username", "")
        smtp_password = os.getenv("SMTP_PASSWORD") or self.config["smtp"].get("password", "")
        
        return {
            "host": self.config["smtp"]["host"],
            "port": int(self.config["smtp"]["port"]),
            "username": smtp_username,
            "password": smtp_password,
            "use_tls": bool(self.config["smtp"]["use_tls"]),
            "retry_attempts": int(self.config["smtp"].get("retry_attempts", 3)),
            "retry_delay": int(self.config["smtp"].get("retry_delay", 5)),
            "send_timeout": int(self.config["smtp"].get("send_timeout", 10))
        }

    @property
    def email_config(self) -> dict:
        return {
            "sender": self.config["email"]["sender"],
            "batch_size": int(self.config["email"]["batch_size"]),
            "csv_file": self.config["email"].get("csv_file", "data/emails_geral.csv"),
            "test_recipient": self.config["email"].get("test_recipient"),
            "batch_delay": int(self.config["email"].get("batch_delay", 60)),
            "unsubscribe_file": self.config["email"].get("unsubscribe_file", "data/descadastros.csv"),
            "test_emails_file": self.config["email"].get("test_emails_file", "data/test_emails.csv")
        }

    @property
    def content_config(self) -> dict:
        """Retorna a configuração de conteúdo dinâmico para os templates de email"""
        return self.email_content