from pathlib import Path
import os

from email_sender.email_service import EmailService


class DummyConfig:
    def __init__(self):
        self._content = {"email": {"template_path": ""}}
        self._email = {}

    @property
    def content_config(self):
        return self._content

    @property
    def email_config(self):
        return self._email


def _make_service():
    return EmailService(DummyConfig())


def test_generate_subject_from_body_fallback_no_api(monkeypatch):
    # Ensure no API keys are present
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GENAI_API_KEY", raising=False)

    svc = _make_service()
    body = (
        "<html><head><title>Proteção e Seletividade</title></head>"
        "<body>"
        "<h1>PowerTreine Goiânia</h1>"
        "<p><strong>Estudos de caso reais</strong></p>"
        "<ul><li>Coordenação de proteções</li><li>Dimensionamento</li></ul>"
        "</body></html>"
    )
    subject = svc._generate_subject_for_body(body, existing_subject="")
    assert subject
    assert ":" not in subject  # não deve conter dois-pontos


def test_subject_interactive_skips_on_non_tty(monkeypatch):
    # Force interactive mode via env, but simulate non-tty to avoid blocking
    monkeypatch.setenv("SUBJECT_INTERACTIVE", "1")

    class FakeStdin:
        def isatty(self):
            return False

    import sys
    old_stdin = sys.stdin
    sys.stdin = FakeStdin()  # type: ignore
    try:
        svc = _make_service()
        result = svc._maybe_interactive_subject("Assunto", "<html></html>")
        assert result == "Assunto"
    finally:
        sys.stdin = old_stdin
