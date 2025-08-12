import os
from email_sender.utils.secrets_manager import SecretsManager, SecretSource


def test_secrets_manager_env_override(monkeypatch):
    monkeypatch.setenv("SMTP_USERNAME", "u1")
    sm = SecretsManager(source=SecretSource.ENV, config_defaults={"SMTP_USERNAME": "fallback"})
    creds = sm.get_smtp_credentials()
    assert creds["username"] == "u1"


def test_secrets_manager_dotenv_fallback(monkeypatch, tmp_path):
    envf = tmp_path / ".env"
    envf.write_text("SMTP_PASSWORD=secret\n", encoding="utf-8")
    # Ensure no env var pre-exists to override
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    sm = SecretsManager(source=SecretSource.DOTENV, dotenv_path=str(envf))
    assert sm.get_secret("SMTP_PASSWORD") == "secret"
