from pathlib import Path
import typer

from email_sender import cli as cli_mod


def test_event_summary_panel_renders(monkeypatch, tmp_path):
    # Arrange minimal config/email
    cfgp, contentp = cli_mod._ensure_or_create_default_config()

    # Fake Sympla API response
    class DummyResponse:
        def __init__(self, status_code=200, json_data=None, text="OK"):
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text
        def raise_for_status(self):
            if not (200 <= self.status_code < 300):
                raise RuntimeError("HTTP error")
        def json(self):
            return self._json

    payload = {"data": [{
        "name": "PowerTreine Goiânia",
        "url": "https://sympla.com/e/ABCDE123",
        "start_date": "2025-08-23 09:00:00",
        "end_date": "2025-08-24 18:00:00",
        "address": {"city": "Goiânia", "state": "GO", "venue": "Centro"}
    }]}

    monkeypatch.setenv("SYMPLA_TOKEN", "tkn")
    monkeypatch.setattr(cli_mod.requests, "get", lambda *a, **k: DummyResponse(200, payload))
    # Auto-select first and auto-confirm
    monkeypatch.setattr(typer, "prompt", lambda *a, **k: "1")
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)

    # Patch DB context used inside function
    import email_sender.db as db_ref
    class FakeDB:
        def __init__(self, cfg): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): return 1
        def fetch_one(self, *a, **k): return {"id": 1}
    monkeypatch.setattr(db_ref, "Database", FakeDB)

    # Act: run function should not raise
    cli_mod._update_event_from_sympla()

    # Assert YAML updated with place/city/state and human date (render path uses Babel if present)
    content = Path(contentp).read_text(encoding="utf-8")
    assert "cidade:" in content and "uf:" in content and "local:" in content
