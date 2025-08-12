import types
import smtplib
from email_sender.smtp_manager import SmtpManager


class FakeConfig:
    def __init__(self):
        self._smtp = {
            "host": "smtp.local",
            "port": 2525,
            "username": "user",
            "password": "pass",
            "use_tls": True,
            "retry_attempts": 1,
            "retry_delay": 0,
            "send_timeout": 2,
        }
        self._email = {"sender": "Sender Name <sender@example.com>"}

    @property
    def smtp_config(self):
        return self._smtp

    @property
    def email_config(self):
        return self._email


class DummySMTP:
    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = False
        self.sent = []

    def starttls(self):
        self.started_tls = True

    def login(self, user, pwd):
        self.logged_in = True

    def send_message(self, msg):
        self.sent.append(msg)

    def quit(self):
        pass


def test_extract_email_address_and_create_message(monkeypatch):
    mgr = SmtpManager(FakeConfig())
    assert mgr._extract_email_address("Name <a@b.com>") == "a@b.com"
    msg = mgr._create_message(
        to_email="rcpt@test",
        subject="Sub",
        content="Hello",
        is_html=False,
    )
    assert msg["To"] == "rcpt@test"
    assert msg["From"].endswith("<sender@example.com>")

    # HTML variant adds text and html parts
    html_msg = mgr._create_message("rcpt@test", "Sub", "<b>Hello</b>", is_html=True)
    assert len(html_msg.get_payload()) == 2


def test_send_email_success(monkeypatch):
    dummy = DummySMTP("smtp.local", 2525, timeout=2)

    def fake_smtp(host, port, timeout):
        assert host == "smtp.local" and port == 2525
        return dummy

    monkeypatch.setattr(smtplib, "SMTP", fake_smtp)

    mgr = SmtpManager(FakeConfig())
    mgr.send_email("rcpt@test", "Subj", "Body", is_html=False)
    assert len(dummy.sent) == 1
