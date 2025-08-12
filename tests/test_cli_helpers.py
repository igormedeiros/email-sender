import os
from pathlib import Path
import types

import typer

from email_sender import cli as cli_mod


class DummyPsycopgConn:
    def __init__(self, *a, **k):
        self.closed = False
    def close(self):
        self.closed = True


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text="OK"):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise RuntimeError(f"HTTP {self.status_code}")
    def json(self):
        return self._json


def _patch_cwd(monkeypatch, tmp_path: Path):
    class FakePath(Path):
        _flavour = Path('.')._flavour
    monkeypatch.setattr(cli_mod.Path, "cwd", staticmethod(lambda: tmp_path))
    # Ensure working dir is tmp for any relative IO
    monkeypatch.chdir(tmp_path)


def test_ensure_or_create_default_config_creates_files(monkeypatch, tmp_path):
    _patch_cwd(monkeypatch, tmp_path)
    config_path, email_path = cli_mod._ensure_or_create_default_config()
    assert config_path.exists()
    assert email_path.exists()
    # Check .env was created
    assert (tmp_path / ".env").exists()


def test_ensure_valid_sender_prompts_and_updates(monkeypatch, tmp_path):
    _patch_cwd(monkeypatch, tmp_path)
    cfg_file = tmp_path / "config" / "config.yaml"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text("email:\n  sender: ''\n", encoding="utf-8")

    prompts = {"Remetente (From)": "Sender <sender@test.com>"}
    monkeypatch.setattr(typer, "prompt", lambda text, **_: prompts[text])

    cli_mod._ensure_valid_sender(cfg_file)
    content = cfg_file.read_text(encoding="utf-8")
    assert "sender@test.com" in content


def test_self_test_runs_successfully(monkeypatch, tmp_path):
    _patch_cwd(monkeypatch, tmp_path)
    # minimal config and template
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config" / "templates").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "config.yaml").write_text("smtp:\n  host: 'localhost'\nemail:\n  sender: 's@d'\n", encoding="utf-8")
    tpl = tmp_path / "config" / "templates" / "email.html"
    tpl.write_text("<html><body>Hi {email}</body></html>", encoding="utf-8")
    (tmp_path / "config" / "email.yaml").write_text(f"email:\n  template_path: '{tpl.as_posix()}'\n  subject: 's'\n  variables: {{}}\n", encoding="utf-8")

    # patch network/db
    monkeypatch.setattr(cli_mod.socket, "getaddrinfo", lambda *a, **k: [(None,)])
    class DummySock:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(cli_mod.socket, "create_connection", lambda *a, **k: DummySock())

    class DummyPsy:
        def __init__(self, *a, **k): pass
        def close(self): pass
    monkeypatch.setattr(cli_mod.psycopg, "connect", lambda **k: DummyPsy())

    # Sympla
    events_payload = {"data": [{"name": "EVT", "url": "https://x/y/evtcode", "start_date": "2025-01-01"}]}
    monkeypatch.setenv("SYMPLA_TOKEN", "tkn")
    monkeypatch.setattr(cli_mod.requests, "get", lambda *a, **k: DummyResponse(200, events_payload))

    # Run
    cli_mod._self_test()


def test_update_event_from_sympla(monkeypatch, tmp_path):
    _patch_cwd(monkeypatch, tmp_path)
    # ensure default config files exist
    cfg_path, content_path = cli_mod._ensure_or_create_default_config()
    # patch token and http
    monkeypatch.setenv("SYMPLA_TOKEN", "tkn")
    payload = {"data": [{
        "name": "My Event - Test",
        "url": "https://sympla.com/e/ABCDE123",
        "start_date": "2025-01-01",
        "end_date": "2025-01-02",
        "address": {"city": "Sao Paulo", "state": "SP", "venue": "Arena"}
    }]}
    monkeypatch.setattr(cli_mod.requests, "get", lambda *a, **k: DummyResponse(200, payload))
    # patch prompts
    monkeypatch.setattr(typer, "prompt", lambda *a, **k: "")
    monkeypatch.setattr(typer, "confirm", lambda *a, **k: True)

    # patch db
    # Monkeypatch Database import used inside function (it imports from email_sender.db)
    import email_sender.db as db_ref
    class FakeDB:
        def __init__(self, cfg): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a, **k): return 1
        def fetch_one(self, *a, **k): return {"id": 1}
    monkeypatch.setattr(db_ref, "Database", FakeDB)

    cli_mod._update_event_from_sympla()
    # YAML should be updated
    content = content_path.read_text(encoding="utf-8")
    assert "sympla_id" in content
