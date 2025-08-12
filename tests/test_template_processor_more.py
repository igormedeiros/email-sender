from pathlib import Path

from email_sender.email_templating import TemplateProcessor


def test_template_processor_formats_date_ptbr_range(tmp_path, monkeypatch):
    # Force pt_BR
    monkeypatch.setenv("EVENT_DATE_LOCALE", "pt_BR")
    tpl = tmp_path / "tpl.html"
    tpl.write_text("<html><body>{data_evento}</body></html>", encoding="utf-8")
    config = {
        "evento": {
            "data": "2025-08-23 09:00:00 a 2025-08-24 18:00:00",
            "link": "",
        }
    }
    tp = TemplateProcessor(config)
    out = tp.process(tpl, {"email": "x@test"})
    assert "23" in out and "24" in out
    assert "agost" in out.lower()  # agosto em pt_BR


def test_template_processor_adds_coupon_param(tmp_path):
    tpl = tmp_path / "tpl.html"
    tpl.write_text("<a href=\"{link_evento}\">Evento</a>", encoding="utf-8")
    config = {"evento": {"link": "https://ex.com/e?x=1", "cupom": "CUPOM30"}}
    tp = TemplateProcessor(config)
    out = tp.process(tpl, {"email": "x@test"})
    assert "d=CUPOM30" in out
    assert out.count("?") == 1
