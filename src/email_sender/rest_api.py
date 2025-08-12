from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Query, Body, HTTPException
from fastapi.responses import JSONResponse

from .config import Config
from .db import Database

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
