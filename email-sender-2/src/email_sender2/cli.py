from __future__ import annotations

import typer

from .ui import print_banner, build_ascii_art
from .config import AppConfig
from .use_cases import CreateMessageAndSelectRecipients

app = typer.Typer(help="Treineinsite Email Sender (Postgres-first)")


@app.callback()
def _banner() -> None:
    print_banner(build_ascii_art(), subtitle="Treineinsite • Email Sender 2")


@app.command()
def health() -> None:
    """Simple healthcheck."""
    typer.echo("ok")


@app.command("message:init")
def message_init(subject: str = typer.Option(..., "--subject", "-s", help="Assunto da campanha")) -> None:
    """Cria a mensagem para o evento ativo e lista destinatários selecionados (Postgres)."""
    cfg = AppConfig()
    uc = CreateMessageAndSelectRecipients(cfg)
    message_id, recipients = uc.run(subject)

    typer.echo(f"message_id={message_id}")
    count = 0
    for _, email in recipients:
        if count < 20:
            typer.echo(f"  - {email}")
        count += 1
    typer.echo(f"total_recipients_previewed={min(count,20)} (de um total possivelmente maior)")


if __name__ == "__main__":
    app()
