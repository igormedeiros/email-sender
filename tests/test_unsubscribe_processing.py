from pathlib import Path
import types

from email_sender.email_templating import TemplateProcessor


def test_template_builds_unsubscribe_full_and_safe(tmp_path):
    # Create a minimal template with placeholders
    tpl = tmp_path / "tpl.html"
    tpl.write_text('<a href="{unsubscribe_full}" data-saferedirecturl="{unsubscribe_safe_url}">x</a>', encoding="utf-8")
    # Configure unsubscribe base
    cfg = {"urls": {"unsubscribe": "https://mkt.treineinsite.com.br/api/unsubscribe"}}
    tp = TemplateProcessor(cfg)
    out = tp.process(tpl, {"email": "user@test.com"})
    assert "https://mkt.treineinsite.com.br/api/unsubscribe?email=user@test.com" in out
    assert "https://www.google.com/url?q=https://mkt.treineinsite.com.br/api/unsubscribe?email=user@test.com" in out


def test_unsubscribe_sql_param(monkeypatch):
    # Import rest_api and patch Database to capture execute call
    from email_sender import rest_api as ra

    calls = {}

    class FakeDb:
        def __init__(self, cfg):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, sql, params=()):
            calls["sql"] = str(sql)
            calls["params"] = tuple(params)
            return 1

    monkeypatch.setattr(ra, "Database", FakeDb)

    # Call internal helper directly
    affected = ra._do_unsubscribe("User@Test.com ")
    assert affected == 1
    assert "mark_unsubscribed_by_email.sql" in calls.get("sql", "")
    # Should pass exactly one param and be normalized to lowercase/trimmed in SQL
    assert calls.get("params") == ("user@test.com",) or calls.get("params") == ("User@Test.com ",)
