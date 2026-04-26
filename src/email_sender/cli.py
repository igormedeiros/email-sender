#!/usr/bin/env python3
"""
Treineinsite Email Sender CLI.

Complete command-line interface for email batch sending, SMTP testing,
contact management, event editing, and database maintenance.

Usage:
    uv run treineinsite-sendemails             # Interactive menu
    uv run treineinsite-sendemails send        # Send emails (test mode)
    uv run treineinsite-sendemails send --prod # Send emails (production)
    uv run treineinsite-sendemails test-smtp   # Test SMTP connection
    uv run treineinsite-sendemails contacts    # List eligible contacts
    uv run treineinsite-sendemails import-csv  # Import contacts from CSV
    uv run treineinsite-sendemails edit-event  # Edit event data
    uv run treineinsite-sendemails clean-db    # Database maintenance
    uv run treineinsite-sendemails bounces     # Manage hardbounces
"""
import csv
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Config
from .db import Database
from .smtp_manager import SmtpManager
from .email_service import EmailService

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

console = Console()
app = typer.Typer(
    name="treineinsite-sendemails",
    help="Treineinsite Email Sender CLI - batch email sending with deduplication.",
    no_args_is_help=False,
)


def _load_components(config_path: str = "config/config.yaml"):
    config = Config(config_path)
    db = Database(config)
    smtp = SmtpManager(config)
    return config, db, smtp


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------
@app.command()
def send(
    message_id: int = typer.Option(1, "--message-id", "-m", help="Message ID to send."),
    prod: bool = typer.Option(False, "--prod", "-p", help="Production mode (all contacts). Default is test mode."),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Simulate sending without actually delivering emails."),
    clear_flags: bool = typer.Option(False, "--clear-flags", "-c", help="Clear send flags before sending (allows re-send)."),
    target_email: Optional[str] = typer.Option(None, "--target", "-t", help="Send only to this specific email address."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts."),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Send emails in batch with 4-level deduplication protection."""
    try:
        config, db, smtp = _load_components(config_path)
        is_test = not prod

        if prod and clear_flags:
            if not yes:
                confirm = console.input("[red]Clear flags + production send. Type 'SIM' to confirm: [/red]").strip()
                if confirm.upper() != "SIM":
                    console.print("[yellow]Cancelled.[/yellow]")
                    raise typer.Exit(0)
            console.print("[cyan]Clearing send flags...[/cyan]")
            try:
                db.connect()
                db.execute("sql/messages/clear_sent_flags.sql", [message_id])
                db.execute("sql/messages/mark_message_unprocessed.sql", [message_id])
                db.close()
                console.print("[green]Flags cleared.[/green]")
            except Exception as e:
                console.print(f"[red]Error clearing flags: {e}[/red]")
                raise typer.Exit(1)

        if prod and not yes:
            confirm = console.input("[red]PRODUCTION mode. Type 'SIM' to confirm: [/red]").strip()
            if confirm.upper() != "SIM":
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        _show_send_preview(config, is_test, dry_run, target_email)

        if not yes and not dry_run:
            go = console.input("[bold]Proceed? (s/n): [/bold]").strip().lower()
            if go not in ("s", "sim", "y", "yes"):
                console.print("[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0)

        service = EmailService(config, db, smtp)
        console.print("[cyan]Starting email delivery...[/cyan]")
        result = service.send_batch(
            message_id=message_id,
            dry_run=dry_run,
            is_test_mode=is_test,
            target_email=target_email,
        )

        if is_test and result.get("sent", 0) > 0:
            try:
                db.connect()
                db.execute("sql/messages/mark_message_unprocessed.sql", [message_id])
                db.close()
            except Exception:
                pass

        _show_send_result(result)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def _show_send_preview(config: Config, is_test: bool, dry_run: bool, target_email: Optional[str]) -> None:
    email_config = config.content_config
    table = Table(show_header=False, box=None, title="Email Preview")
    table.add_row("[bold]Subject:[/bold]", email_config.get("email", {}).get("subject", "(none)"))
    evento = email_config.get("evento", {})
    table.add_row("[bold]Event:[/bold]", evento.get("nome", "(none)"))
    table.add_row("[bold]Date:[/bold]", evento.get("data", "(none)"))
    table.add_row("[bold]Location:[/bold]", evento.get("local", "(none)"))
    cupom = evento.get("cupom", "")
    if cupom:
        table.add_row("[bold]Coupon:[/bold]", cupom)
    mode = "[green]TEST[/green]" if is_test else "[red]PRODUCTION[/red]"
    if dry_run:
        mode += " [yellow](DRY-RUN)[/yellow]"
    if target_email:
        mode += f" [cyan](target: {target_email})[/cyan]"
    table.add_row("[bold]Mode:[/bold]", mode)
    console.print(table)


def _show_send_result(result: dict) -> None:
    table = Table(title="Send Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    table.add_row("Total processed", str(result.get("total_processed", 0)))
    table.add_row("Sent", str(result.get("sent", 0)))
    table.add_row("Failed", str(result.get("failed", 0)))
    if result.get("errors"):
        table.add_row("Errors", str(len(result["errors"])))
    console.print(table)


# ---------------------------------------------------------------------------
# test-smtp
# ---------------------------------------------------------------------------
@app.command("test-smtp")
def test_smtp(
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Test SMTP connection and authentication."""
    try:
        config = Config(config_path)
        smtp = SmtpManager(config)
        console.print("[cyan]Testing SMTP connection...[/cyan]")
        smtp.connect()
        smtp.disconnect()
        console.print("[green]SMTP connection successful.[/green]")
    except Exception as e:
        console.print(f"[red]SMTP connection failed: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# contacts
# ---------------------------------------------------------------------------
@app.command()
def contacts(
    limit: int = typer.Option(20, "--limit", "-l", help="Max contacts to display."),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """List eligible contacts from the database."""
    try:
        config = Config(config_path)
        db = Database(config)
        db.connect()
        all_contacts = db.fetch_all("sql/contacts/select_recipients_for_message.sql", [False, 1])
        db.close()

        console.print(f"[cyan]{len(all_contacts)} eligible contacts found.[/cyan]")
        if all_contacts:
            table = Table(title="Contacts")
            table.add_column("ID", style="cyan")
            table.add_column("Email", style="magenta")
            for c in all_contacts[:limit]:
                cid = c.get("id", c[0]) if isinstance(c, dict) else c[0]
                email = c.get("email", c[1]) if isinstance(c, dict) else c[1]
                table.add_row(str(cid), str(email))
            if len(all_contacts) > limit:
                table.add_row("...", f"+{len(all_contacts) - limit} more")
            console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# import-csv
# ---------------------------------------------------------------------------
@app.command("import-csv")
def import_csv(
    csv_file: str = typer.Argument("contacts.csv", help="Path to the CSV file with an 'email' column."),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Import contacts from a CSV file into the database."""
    csv_path = Path(csv_file)
    if not csv_path.exists():
        console.print(f"[red]File not found: {csv_file}[/red]")
        raise typer.Exit(1)

    try:
        config = Config(config_path)
        db = Database(config)
        db.connect()

        emails: list[str] = []
        duplicates = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email", "").strip().lower()
                if email:
                    if email in emails:
                        duplicates += 1
                    else:
                        emails.append(email)

        if not emails:
            console.print("[red]No emails found in file.[/red]")
            raise typer.Exit(1)

        inserted = 0
        for email in emails:
            try:
                existing = db.fetch_one("sql/contacts/select_contact_by_email.sql", [email])
                if not existing:
                    db.execute("sql/contacts/insert_contact.sql", [email])
                    inserted += 1
            except Exception as e:
                console.print(f"[red]Error inserting {email}: {e}[/red]")

        db.close()
        console.print(f"[green]Imported {inserted} new contacts.[/green]")
        if duplicates:
            console.print(f"[yellow]{duplicates} duplicates skipped.[/yellow]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Import error: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# edit-event
# ---------------------------------------------------------------------------
@app.command("edit-event")
def edit_event(
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Interactively edit event data stored in email.yaml."""
    try:
        config = Config(config_path)
        email_config = config.content_config
        evento = email_config.get("evento", {})
        email_data = email_config.get("email", {})

        console.print("[cyan]Editing event data (leave blank to keep current).[/cyan]")

        fields = [
            ("nome", "Name"),
            ("data", "Date"),
            ("local", "Location"),
            ("link", "Link"),
            ("cupom", "Coupon"),
        ]
        for key, label in fields:
            current = evento.get(key, "")
            new_val = console.input(f"  [bold]{label}[/bold] ([cyan]{current}[/cyan]): ").strip()
            if new_val:
                evento[key] = new_val

        current_subject = email_data.get("subject", "")
        new_subject = console.input(f"  [bold]Subject[/bold] ([yellow]{current_subject}[/yellow]): ").strip()
        if new_subject:
            email_data["subject"] = new_subject

        config.email_content["evento"] = evento
        config.email_content["email"] = email_data
        config.save_content_config()
        console.print("[green]Event data updated.[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# clean-db
# ---------------------------------------------------------------------------
@app.command("clean-db")
def clean_db(
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Run database maintenance operations."""
    console.print("[cyan]Database Maintenance[/cyan]")
    console.print("[yellow]Warning: these actions are irreversible.[/yellow]")

    table = Table(show_header=False, box=None)
    table.add_row("[bold]1[/bold]", "Remove duplicate contacts")
    table.add_row("[bold]2[/bold]", "Run full maintenance (SQL)")
    table.add_row("[bold]3[/bold]", "Cancel")
    console.print(table)

    choice = console.input("[bold]Choose: [/bold]").strip()

    if choice == "1":
        confirm = console.input("[red]Type 'SIM' to confirm: [/red]").strip()
        if confirm.upper() == "SIM":
            try:
                import subprocess
                proc = subprocess.run(["python", "scripts/remove_duplicate_contacts.py"], capture_output=True, text=True)
                if proc.returncode == 0:
                    console.print(f"[green]Done.[/green]\n{proc.stdout}")
                else:
                    console.print(f"[red]Error:[/red]\n{proc.stderr}")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")

    elif choice == "2":
        confirm = console.input("[red]Type 'SIM' to confirm: [/red]").strip()
        if confirm.upper() == "SIM":
            try:
                config = Config(config_path)
                db = Database(config)
                db.connect()
                db.execute("sql/maintenance/database_maintenance.sql")
                db.close()
                console.print("[green]Maintenance complete.[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")


# ---------------------------------------------------------------------------
# bounces
# ---------------------------------------------------------------------------
@app.command()
def bounces(
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config.yaml."),
) -> None:
    """Fetch and process hardbounces from Locaweb SMTP, removing them from the mailing list."""
    try:
        from .hardbounce_manager import HardbounceManager

        config = Config(config_path)
        db = Database(config)
        manager = HardbounceManager(config, db)
        result = manager.process_bounces()

        console.print(f"[cyan]Hardbounces processed.[/cyan]")
        console.print(f"  Fetched: {result['fetched']}")
        console.print(f"  Tagged: {result['tagged']}")
        console.print(f"  Already tagged: {result['already_tagged']}")
        if result.get("errors"):
            for err in result["errors"]:
                console.print(f"  [red]Error: {err}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Interactive menu (default)
# ---------------------------------------------------------------------------
def _show_menu() -> str:
    console.print("\n[bold cyan]Treineinsite - Email Sender CLI[/bold cyan]\n")
    table = Table(show_header=False, box=None)
    table.add_row("[bold]1[/bold]", "Send emails")
    table.add_row("[bold]2[/bold]", "Test SMTP")
    table.add_row("[bold]3[/bold]", "List contacts")
    table.add_row("[bold]4[/bold]", "Import contacts (CSV)")
    table.add_row("[bold]5[/bold]", "Edit event")
    table.add_row("[bold]6[/bold]", "Clean database")
    table.add_row("[bold]7[/bold]", "Manage hardbounces")
    table.add_row("[bold]8[/bold]", "Exit")
    console.print(table)
    return console.input("\n[bold]Choose an option:[/bold] ").strip()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Treineinsite Email Sender - interactive menu or use subcommands above."""
    if ctx.invoked_subcommand is not None:
        return

    choice = _show_menu()
    dispatch = {
        "1": lambda: _send_menu(),
        "2": lambda: test_smtp(config_path="config/config.yaml"),
        "3": lambda: contacts(limit=20, config_path="config/config.yaml"),
        "4": lambda: import_csv(csv_file="contacts.csv", config_path="config/config.yaml"),
        "5": lambda: edit_event(config_path="config/config.yaml"),
        "6": lambda: clean_db(config_path="config/config.yaml"),
        "7": lambda: bounces(config_path="config/config.yaml"),
        "8": lambda: _exit_app(),
    }

    action = dispatch.get(choice)
    if action:
        action()
    else:
        console.print("[red]Invalid option.[/red]")
        raise typer.Exit(1)


def _send_menu() -> None:
    console.print("\n[bold]Modo de envio:[/bold]")
    table = Table(show_header=False, box=None)
    table.add_row("[bold]1[/bold]", "[green]Teste[/green] (somente contatos de teste)")
    table.add_row("[bold]2[/bold]", "[red]Produção[/red] (todos os contatos)")
    table.add_row("[bold]3[/bold]", "Voltar")
    console.print(table)
    mode_choice = console.input("[bold]Modo: [/bold]").strip()

    if mode_choice == "3":
        return
    if mode_choice not in ("1", "2"):
        console.print("[red]Opção inválida.[/red]")
        return

    is_prod = mode_choice == "2"

    clear = False
    if console.input("[bold]Limpar flags de envio antes de enviar? (s/n): [/bold]").strip().lower() in ("s", "sim", "y", "yes"):
        clear = True

    send(
        message_id=1,
        prod=is_prod,
        dry_run=False,
        clear_flags=clear,
        target_email=None,
        yes=False,
        config_path="config/config.yaml",
    )


def _exit_app() -> None:
    console.print("[yellow]Goodbye![/yellow]")
    raise typer.Exit(0)


if __name__ == "__main__":
    app()
