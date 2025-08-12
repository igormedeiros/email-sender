from __future__ import annotations

from typing import Optional, Iterable

from rich.console import Console
from rich.panel import Panel
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
    """Prints a consistent banner panel with optional subtitle.

    - Uses cyan border and bold cyan ASCII text
    - Subtitle centered below the banner
    """
    console = get_console()

    ascii_text = Text(ascii_art.rstrip("\n"), style="bold cyan")
    console.print(Panel.fit(ascii_text, border_style="cyan", padding=(1, 2)))

    if subtitle:
        console.print(Text(subtitle, style="bold white"), justify="center")

    console.rule(style="cyan")


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
