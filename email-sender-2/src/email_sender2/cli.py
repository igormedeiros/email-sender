from __future__ import annotations

import typer

from .ui import print_banner, build_ascii_art

app = typer.Typer(help="Treineinsite Email Sender (Postgres-first)")


@app.callback()
def _banner() -> None:
    print_banner(build_ascii_art(), subtitle="Treineinsite • Email Sender 2")


@app.command()
def health() -> None:
    """Simple healthcheck."""
    typer.echo("ok")


if __name__ == "__main__":
    app()
