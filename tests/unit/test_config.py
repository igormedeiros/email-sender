"""
Testes unitários para o módulo de configuração.
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.email_sender.config import Config


class TestConfig:
    """Testes para a classe Config."""

    def test_config_initialization(self, temp_dir, sample_config_data):
        """Testa inicialização básica da configuração."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config_data, f)

        email_data = {"email": {"subject": "Test"}}
        email_path = temp_dir / "email.yaml"
        with open(email_path, 'w') as f:
            yaml.dump(email_data, f)

        config = Config(str(config_path), str(email_path))

        assert config.config["database"]["host"] == "localhost"
        assert config.config["database"]["port"] == 5432
        assert config.config["smtp"]["host"] == "smtp.test.com"
        assert config.email_content["email"]["subject"] == "Test"

    def test_config_missing_file(self):
        """Testa comportamento quando arquivo de configuração não existe."""
        with pytest.raises(FileNotFoundError):
            Config("/nonexistent/path/config.yaml")

    def test_config_invalid_yaml(self, temp_dir):
        """Testa comportamento com YAML inválido."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [\n")

        with pytest.raises(yaml.YAMLError):
            Config(str(config_path))

    def test_config_smtp_config(self, mock_config):
        """Testa configuração SMTP."""
        smtp_config = mock_config.smtp_config

        assert smtp_config["host"] == "smtp.test.com"
        assert smtp_config["port"] == 587
        assert smtp_config["username"] == "test@test.com"
        assert "password" in smtp_config

    def test_config_email_config(self, mock_config):
        """Testa configuração de email."""
        email_config = mock_config.email_config

        assert email_config["sender"] == "Test Sender <test@test.com>"
        assert email_config["batch_size"] == 200
        assert email_config["batch_delay"] == 5

    def test_config_missing_file(self):
        """Testa comportamento quando arquivo de configuração não existe."""
        config = Config()
        config._config_file = "/nonexistent/path/config.yaml"

        with pytest.raises(FileNotFoundError):
            config._load_config()

    def test_config_invalid_yaml(self, temp_dir):
        """Testa comportamento com YAML inválido."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            f.write("invalid: yaml: content: [\n")

        config = Config()
        config._config_file = str(config_path)

        with pytest.raises(yaml.YAMLError):
            config._load_config()

    def test_config_env_override(self, temp_dir, sample_config_data):
        """Testa que variáveis de ambiente sobrescrevem configuração."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config_data, f)

        env_vars = {
            "DB_HOST": "env_host",
            "DB_PORT": "9999",
            "DB_USER": "env_user",
            "DB_PASSWORD": "env_password",
            "DB_NAME": "env_db"
        }

        config = Config()
        config.config_file = str(config_path)

            assert config.postgres_config["host"] == "env_host"
            assert config.postgres_config["port"] == 9999
            assert config.postgres_config["user"] == "env_user"
            assert config.postgres_config["password"] == "env_password"
            assert config.postgres_config["database"] == "env_db"

    def test_config_smtp_config(self, temp_dir, sample_config_data):
        """Testa configuração SMTP."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config_data, f)

        with patch.dict(os.environ, {"SMTP_PASSWORD": "smtp_pass"}):
                    config = Config()
                    config.config_file = str(config_path)
            smtp_config = config.get_smtp_config()
            assert smtp_config["host"] == "smtp.test.com"
            assert smtp_config["port"] == 587
            assert smtp_config["user"] == "test@test.com"
            assert smtp_config["password"] == "smtp_pass"

        config = Config()
        config.config_file = str(config_path)

        email_config = config.get_email_config()
        assert email_config["sender"] == "Test Sender <test@test.com>"
        assert email_config["batch_size"] == 200
        assert email_config["batch_delay"] == 5

    def test_config_logging_config(self, temp_dir, sample_config_data):
        """Testa configuração de logging."""
        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(sample_config_data, f)

        config = Config()
        config.config_file = str(config_path)

        logging_config = config.get_logging_config()
        assert logging_config["level"] == "INFO"
        assert logging_config["file"] is None

    def test_config_missing_required_fields(self, temp_dir):
        """Testa comportamento com campos obrigatórios faltando."""
        incomplete_config = {
            "database": {
                "host": "localhost"
                # faltam outros campos obrigatórios
            }
        }

        config_path = temp_dir / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(incomplete_config, f)

        config = Config()
        config.config_file = str(config_path)
        assert config.postgres_config["host"] == "localhost"

    def test_config_file_path_resolution(self, temp_dir, sample_config_data):
        """Testa resolução de caminho do arquivo de configuração."""
        config_path = temp_dir / "subdir" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(sample_config_data, f)

        config = Config()
        config.config_file = str(config_path)
        assert config.postgres_config["host"] == "localhost"