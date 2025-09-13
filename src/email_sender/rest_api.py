from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Query, Body, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from .config import Config
from .db import Database
from .tracking import TrackingUrlValidator

app = FastAPI(title="Treineinsite Email Sender API", version="0.1.0")


def _normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def _do_unsubscribe(email: str) -> int:
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="email inválido")
    cfg = Config()
    with Database(cfg) as db:
        affected = db.execute("sql/contacts/mark_unsubscribed_by_email.sql", (email,))
    return affected


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/api/unsubscribe")
async def unsubscribe_get(email: str = Query(..., description="Email do contato a descadastrar")) -> JSONResponse:
    email_norm = _normalize_email(email)
    affected = _do_unsubscribe(email_norm)
    return JSONResponse({"status": "ok", "email": email_norm, "affected": affected})


@app.post("/api/unsubscribe")
async def unsubscribe_post(payload: dict = Body(..., description="{ 'email': 'contato@exemplo.com' }")) -> JSONResponse:
    email_norm = _normalize_email(str(payload.get("email", "")))
    affected = _do_unsubscribe(email_norm)
    return JSONResponse({"status": "ok", "email": email_norm, "affected": affected})


@app.get("/api/tracking/open")
async def track_open(request: Request, contact_id: int = Query(...), message_id: int = Query(...)) -> Response:
    """Registra abertura de email e retorna um pixel 1x1 transparente."""
    cfg = Config()
    client_ip = request.headers.get("x-forwarded-for") or request.client.host

    with Database(cfg) as db:
        try:
            db.execute("sql/messages/insert_open_log.sql", (contact_id, message_id, client_ip))
            # Opcional: atualizar lead score e tag
            try:
                db.execute("sql/leads/upsert_open_score.sql", (contact_id,))
            except Exception:
                pass
            try:
                db.execute("sql/tags/assign_tag_opened.sql", (contact_id,))
            except Exception:
                pass
        except Exception as e:
            # Não propaga erro para não quebrar pixel
            pass

    # Retorna um pixel PNG transparente
    # 1x1 GIF também aceitável, mas vamos usar PNG em bytes
    pixel_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\x0bIDATx\x9cc````\x00\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(content=pixel_png, media_type="image/png")


"""Endpoint de tracking de cliques foi removido."""


if __name__ == "__main__":
    # Execução direta: lê host/port de config/rest.yaml se existir
    cfg = Config()
    server = cfg.rest_server_config
    uvicorn.run(
        "email_sender.rest_api:app",
        host=server.get("host", "0.0.0.0"),
        port=int(server.get("port", 5000)),
        reload=bool(server.get("debug", True)),
    )
