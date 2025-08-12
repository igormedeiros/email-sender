import os
from email_sender.utils.ui import notify_telegram


class DummyResponse:
    def __init__(self, status_code=200):
        self.status_code = status_code


def test_notify_telegram_posts_when_env_set(monkeypatch):
    calls = {}

    def fake_post(url, json=None, timeout=5):
        calls["url"] = url
        calls["json"] = json
        return DummyResponse(200)

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tkn")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("email_sender.utils.ui.requests.post", fake_post)

    notify_telegram("hello")
    assert calls.get("url", "").startswith("https://api.telegram.org/bot")
    assert calls.get("json", {}).get("text") == "hello"


def test_notify_telegram_noop_without_env(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    # Should not raise
    notify_telegram("hello")
