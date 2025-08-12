from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

_CONSOLE: Optional[Console] = None

def console() -> Console:
    global _CONSOLE
    if _CONSOLE is None:
        _CONSOLE = Console(highlight=False, soft_wrap=False)
    return _CONSOLE


def build_ascii_art() -> str:
    return (
        "\n"
        "  _______              _           _         _     _       _       _        \n"
        " |__   __|            | |         (_)       | |   (_)     | |     | |       \n"
        "    | | _ __ ___  __ _| |_ ___ ___ _  ___   | |_   _  __ _| | __ _| |_ ___  \n"
        "    | || '__/ _ \\/ _` | __/ __/ __| |/ __|  | __| | |/ _` | |/ _` | __/ _ \\ \n"
        "    | || | |  __/ (_| | |_\\__ \\__ \\ | (__   | |_  | | (_| | | (_| | ||  __/ \n"
        "    |_|_|  \\___|\\__,_|\\__|___/___/_|\\___|   \\__| |_|\\__, |_|\\__,_|\\__\\___| \n"
        "                                                     __/ |                      \n"
        "                                                    |___/                       \n"
    )


def print_banner(ascii_art: str, subtitle: Optional[str] = None) -> None:
    c = console()
    c.print(Panel.fit(Text(ascii_art.rstrip("\n"), style="bold cyan"), border_style="cyan", padding=(1, 2)))
    if subtitle:
        c.print(Text(subtitle, style="bold white"), justify="center")
    c.rule(style="cyan")
