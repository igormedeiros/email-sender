import builtins
from pathlib import Path
import tempfile

from email_sender.email_templating import TemplateProcessor


def test_template_processor_replaces_placeholders_without_coupon():
    html = """
    <html><body>
    <a href="{link_evento}">Evento</a>
    <p>{data_evento}</p>
    <p>{cidade}</p>
    <p>{local}</p>
    <p>{email}</p>
    </body></html>
    """.strip()

    with tempfile.TemporaryDirectory() as tmp:
        tpl_path = Path(tmp) / "tpl.html"
        tpl_path.write_text(html, encoding="utf-8")
        config = {
            "evento": {
                "link": "https://exemplo.com/evento",
                "data": "2025-01-01",
                "cidade": "SP",
                "local": "Allianz"
            },
            "urls": {"unsubscribe": "https://u", "subscribe": "https://s"}
        }
        tp = TemplateProcessor(config)
        out = tp.process(tpl_path, {"email": "user@test"})
        assert "https://exemplo.com/evento" in out
        assert "2025-01-01" in out
        assert ">SP<" in out
        assert ">Allianz<" in out
        assert ">user@test<" in out


def test_template_processor_adds_coupon_when_present():
    html = "<a href=\"{link_evento}\">Evento</a>"
    with tempfile.TemporaryDirectory() as tmp:
        tpl_path = Path(tmp) / "tpl.html"
        tpl_path.write_text(html, encoding="utf-8")
        config = {"evento": {"link": "https://exemplo.com/evento?x=1", "cupom": "CUPOM10"}}
        tp = TemplateProcessor(config)
        out = tp.process(tpl_path, {"email": "user@test"})
        assert "d=CUPOM10" in out
        assert out.count("?") == 1

