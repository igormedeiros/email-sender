from configparser import ConfigParser
from pathlib import Path

class Config:
    def __init__(self, properties_file: str = "dev.properties"):
        self.config = ConfigParser()
        self.config.read(properties_file)

    @property
    def smtp_config(self) -> dict:
        return {
            "host": self.config.get("smtp", "host"),
            "port": self.config.getint("smtp", "port"),
            "username": self.config.get("smtp", "username"),
            "password": self.config.get("smtp", "password"),
            "use_tls": self.config.getboolean("smtp", "use_tls"),
            "retry_attempts": self.config.getint("smtp", "retry_attempts", fallback=3),
            "retry_delay": self.config.getint("smtp", "retry_delay", fallback=5),
            "send_timeout": self.config.getint("smtp", "send_timeout", fallback=10)
        }

    @property
    def email_config(self) -> dict:
        return {
            "sender": self.config.get("email", "sender"),
            "batch_size": self.config.getint("email", "batch_size"),
            "xlsx_file": self.config.get("email", "xlsx_file"),
            "test_recipient": self.config.get("email", "test_recipient", fallback=None),
            "default_subject": self.config.get("email", "default_subject", fallback=None),
            "batch_delay": self.config.getint("email", "batch_delay", fallback=60)
        }