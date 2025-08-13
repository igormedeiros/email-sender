import time
from pathlib import Path

from email_sender import email_service as es
from email_sender.email_service import EmailService


class FakeDb:
    def __init__(self):
        self.executed = []
        self.fetches = []
    def __enter__(self):
        return self
    def __exit__(self, *a):
        pass
    def fetch_one(self, sql, params=()):
        if "create_message.sql" in str(sql):
            return {"id": 42}
        if "count_unsubscribed_since_id.sql" in str(sql):
            return {"cnt": 1}
        if "count_bounces_since_id.sql" in str(sql):
            return {"cnt": 1}
        return None
    def fetch_all(self, sql, params=()):
        # Track which SQL was used
        self.fetches.append((str(sql), params))
        # Two recipients
        return [
            {"id": 1, "email": "a@test"},
            {"id": 2, "email": "b@test"},
        ]
    def execute(self, sql, params=()):
        self.executed.append((str(sql), params))
        return 1


class FakeSmtp:
    def __init__(self):
        self.calls = []
    def send_email(self, to_email, subject, content, is_html=True):
        self.calls.append(to_email)


class FakeConfig:
    def __init__(self, tpl: Path):
        self._content = {"email": {"template_path": str(tpl), "subject": "S"}}
        self._email = {
            "batch_delay": 0,
            "retry_attempts": 1,
            "retry_delay": 0,
            "send_timeout": 1,
            "batch_size": 10,
        }
    @property
    def content_config(self):
        return self._content
    @property
    def email_config(self):
        return self._email


def test_process_email_sending_success(monkeypatch, tmp_path):
    tpl = tmp_path / "t.html"
    tpl.write_text("<html><head><title>Convite PT</title></head><body><h1>PowerTreine Goiânia</h1>Hi {email}</body></html>", encoding="utf-8")

    monkeypatch.setattr(es, "Database", lambda cfg: FakeDb())
    fake_smtp = FakeSmtp()
    monkeypatch.setattr(es, "SmtpManager", lambda cfg: fake_smtp)
    monkeypatch.setattr(es.time, "sleep", lambda *a, **k: None)
    # no-op alarm
    monkeypatch.setattr(es.signal, "alarm", lambda *a, **k: None)

    svc = EmailService(FakeConfig(tpl))
    result = svc.process_email_sending(template=str(tpl))
    assert result["total_sent"] == 2
    assert result["successful"] == 2
    assert len(fake_smtp.calls) == 2
    # Ensure we used the SQL that excludes unsubscribed/bounces
    assert any("select_contacts_simple.sql" in call[0] for call in db.executed + db.fetches)
