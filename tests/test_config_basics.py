import os
from pathlib import Path

from email_sender.config import Config


def test_config_loads_environment_mode(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    content_path = tmp_path / "email.yaml"
    cfg_path.write_text("smtp:\n  host: \"\"\nemail:\n  sender: \"\"\n", encoding="utf-8")
    content_path.write_text("email:\n  template_path: \"/tmp/t.html\"\n", encoding="utf-8")

    monkeypatch.setenv("ENVIRONMENT", "production")
    c = Config(str(cfg_path), str(content_path))
    assert c.environment_mode == "prod"


def test_smtp_config_defaults(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    content_path = tmp_path / "email.yaml"
    cfg_path.write_text("smtp:\n  host: \"smtp\"\n  port: 2525\nemail: {}\n", encoding="utf-8")
    content_path.write_text("email:\n  template_path: \"/tmp/t.html\"\n", encoding="utf-8")
    c = Config(str(cfg_path), str(content_path))
    s = c.smtp_config
    assert s["host"] == "smtp"
    assert s["port"] == 2525
    assert s["use_tls"] is True
