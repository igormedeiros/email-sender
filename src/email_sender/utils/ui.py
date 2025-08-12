from __future__ import annotations

from typing import Optional, Iterable

try:
    from pyfiglet import Figlet  # type: ignore
except Exception:  # pragma: no cover - fallback if not installed
    Figlet = None  # type: ignore

from rich.console import Console
import requests  # module-level for monkeypatching in tests
from rich.text import Text
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)

# Singleton console for consistent output across the app
_CONSOLE: Optional[Console] = None


def get_console() -> Console:
    global _CONSOLE
    if _CONSOLE is None:
        _CONSOLE = Console(highlight=False, soft_wrap=False)
    return _CONSOLE


def print_banner(ascii_art: str, subtitle: Optional[str] = None) -> None:
    """Cursor/Claude/Opencode-style banner with Treineinsite in light blue.

    - Gradient-like feel using shades of cyan/blue
    - Clean single-line rule beneath
    """
    console = get_console()

    # Use light blue (cyan) for the wordmark, without any box/border
    ascii_text = Text(ascii_art.rstrip("\n"), style="bold bright_cyan")
    # Envolver o banner em uma moldura simples
    top = Text("┌" + ("─" * 60) + "┐", style="bright_cyan")
    bottom = Text("└" + ("─" * 60) + "┘", style="bright_cyan")
    console.print(top, justify="center")
    console.print(ascii_text)
    if subtitle:
        console.print(Text(subtitle, style="bright_white"), justify="center")
    console.print(bottom, justify="center")
    console.rule(style="bright_cyan")


def build_treineinsite_ascii_art() -> str:
    """Returns an ASCII art banner for 'TREINEINSITE' using pyfiglet (slant)."""
    text = "TREINEINSITE"
    if Figlet is not None:
        try:
            fig = Figlet(font="slant", width=120)
            art = fig.renderText(text)
            return "\n" + art.rstrip("\n") + "\n"
        except Exception:
            pass
    # Fallback literal
    return f"\n{text}\n"


def section(title: str) -> None:
    """Renders a section divider with a title."""
    console = get_console()
    # Seção com canto arredondado visual (unicode)
    line = "─" * max(10, min(70, len(title) + 8))
    console.print(Text(f"╭{line}╮", style="bright_cyan"))
    console.print(Text(f"  {title}", style="bold bright_white"))
    console.print(Text(f"╰{line}╯", style="bright_cyan"))


def info(message: str) -> None:
    get_console().print(f"[bold cyan]ℹ[/bold cyan] {message}")


def success(message: str) -> None:
    get_console().print(f"[bold green]✓[/bold green] {message}")


def warn(message: str) -> None:
    get_console().print(f"[bold yellow]![/bold yellow] {message}")


def error(message: str) -> None:
    get_console().print(f"[bold red]✗[/bold red] {message}")


def progress(description: str = "Processando...", total: Optional[int] = None) -> Progress:
    """Creates a pre-configured Progress instance (Cursor Agent CLI style)."""
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        transient=False,
        console=get_console(),
    )


def notify_telegram(message: str) -> bool:
    """Envia uma notificação simples via Telegram Bot, se as variáveis estiverem configuradas.

    Requer: TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no ambiente.
    Não lança exceções; falhas são ignoradas silenciosamente para não quebrar o fluxo.
    """
    import os
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN")
    # Support both numeric chat id and @username via envs
    chat_id = (
        os.environ.get("TELEGRAM_CHAT_ID")
        or os.environ.get("TELEGRAM_CHAT")
        or os.environ.get("TELEGRAM_CHAT_USERNAME")
    )
    if not token or not chat_id or not message:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    debug = (os.environ.get("TELEGRAM_DEBUG") or "").lower() in {"1","true","yes","on"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        ok = 200 <= getattr(resp, "status_code", 0) < 300
        if debug and not ok:
            get_console().print(f"[yellow]Telegram notify failed:[/yellow] {getattr(resp, 'status_code', 'NA')} for {url}")
        return ok
    except Exception as e:
        if debug:
            get_console().print(f"[yellow]Telegram notify exception:[/yellow] {e}")
        return False
