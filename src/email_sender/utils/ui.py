from __future__ import annotations

from typing import Optional, Iterable

try:
    from pyfiglet import Figlet  # type: ignore
except Exception:  # pragma: no cover - fallback if not installed
    Figlet = None  # type: ignore

from rich.console import Console
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
    console.print(ascii_text)

    if subtitle:
        console.print(Text(subtitle, style="bright_white"), justify="center")

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
    console.rule(Text(title, style="bold magenta"))


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
