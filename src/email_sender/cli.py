#!/usr/bin/env python3
"""
CLI interativa para o Email Sender - Menu principal.
Segue princípios KISS com interface amigável.
"""
import sys
import typer
import logging
from typing import Optional
from rich.console import Console
from rich.table import Table

from .config import Config
from .db import Database
from .smtp_manager import SmtpManager
from .email_service import EmailService

# CONFIGURAR LOGGING PARA VER [DEBUG], [INFO], [ERROR]
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s'
)

console = Console()
app = typer.Typer()


def show_menu():
    """Exibir menu interativo principal."""
    console.print("\n[bold cyan]Treineinsite • Email Sender CLI[/bold cyan]\n")
    
    table = Table(show_header=False, box=None)
    table.add_row("[bold]1[/bold]", "Enviar emails")
    table.add_row("[bold]2[/bold]", "Testar SMTP")
    table.add_row("[bold]3[/bold]", "Ver contatos")
    table.add_row("[bold]4[/bold]", "Importar contatos (CSV)")
    table.add_row("[bold]5[/bold]", "Sair")
    
    console.print(table)
    return console.input("\n[bold]Escolha uma opção:[/bold] ").strip()


def send_emails_interactive():
    """Menu interativo para envio de emails."""
    try:
        config = Config("config/config.yaml")
        
        # Escolher modo (padrão: TESTE)
        console.print("\n[bold]Modo de envio:[/bold]")
        console.print("[bold green]1[/bold green] - Teste (contatos com tag 'Test') [padrão]")
        console.print("[bold red]2[/bold red] - ⚠️  Produção (TODOS os contatos)")
        
        mode = console.input("\nEscolha [1-2] (padrão=1): ").strip() or "1"
        
        if mode not in ["1", "2"]:
            console.print("[red]Opção inválida![/red]")
            return
        
        is_test = mode == "1"
        
        # Aviso se for produção
        if is_test:
            console.print("[green]✓ Modo TESTE - contatos com tag 'Test'[/green]")
        else:
            console.print("[bold red]⚠️  MODO PRODUÇÃO - CUIDADO![/bold red]")
            confirm = console.input("[red]Tem certeza? Digite 'SIM' para confirmar: [/red]").strip()
            if confirm.upper() != "SIM":
                console.print("[yellow]Operação cancelada.[/yellow]")
                return
        
        # Inicializar componentes
        db = Database(config)
        smtp = SmtpManager(config)
        service = EmailService(config, db, smtp)
        
        # 📋 MOSTRAR TEMPLATE ANTES DE ENVIAR
        console.print("\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        console.print("[bold cyan]📋 Dados do Email a Enviar[/bold cyan]")
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]")
        
        email_config = config.content_config  # Carregar dados dinâmicos
        
        # Tabela com dados
        table_preview = Table(show_header=False, box=None)
        
        # Assunto
        subject = email_config.get('email', {}).get('subject', '(sem assunto)')
        table_preview.add_row("[bold]Assunto:[/bold]", f"[yellow]{subject}[/yellow]")
        
        # Evento
        evento = email_config.get('evento', {})
        table_preview.add_row("[bold]Evento:[/bold]", f"[cyan]{evento.get('nome', '(sem evento)')}[/cyan]")
        table_preview.add_row("[bold]Data:[/bold]", f"{evento.get('data', '(sem data)')}")
        table_preview.add_row("[bold]Local:[/bold]", f"{evento.get('local', '(sem local)')}")
        
        # Link
        link = evento.get('link', '(sem link)')
        cupom = evento.get('cupom', '')
        if cupom:
            table_preview.add_row("[bold]Cupom:[/bold]", f"[green]{cupom}[/green]")
        
        # Modo
        mode_text = "[green]TESTE (tag 'Test')[/green]" if is_test else "[red]PRODUÇÃO (TODOS)[/red]"
        table_preview.add_row("[bold]Modo:[/bold]", mode_text)
        
        console.print(table_preview)
        console.print("[bold cyan]═══════════════════════════════════════[/bold cyan]\n")
        
        # Confirmação final
        confirm_final = console.input("[bold]Continuar com o envio? (s/n):[/bold] ").strip().lower()
        if confirm_final not in ["s", "sim", "y", "yes"]:
            console.print("[yellow]Operação cancelada.[/yellow]")
            return
        
        # Executar envio
        console.print("\n[bold cyan]Iniciando envio de emails...[/bold cyan]")
        result = service.send_batch(message_id=1, dry_run=False, is_test_mode=is_test)
        
        # Se for TESTE e enviou com sucesso, reseta flag para próximo envio
        if is_test and result.get('sent', 0) > 0:
            try:
                db.connect()
                db.execute("sql/messages/mark_message_unprocessed.sql", [1])
                db.disconnect()
                console.print("[green]✓ Message reset para próximo envio (TESTE)[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Não foi possível resetar message: {e}[/yellow]")
        
        # Mostrar resultado
        console.print("\n[bold cyan]Resumo do Envio:[/bold cyan]")
        table = Table(title="Email Report")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="magenta")
        
        table.add_row("Total processado", str(result.get('total_processed', 0)))
        table.add_row("Enviados", str(result.get('sent', 0)))
        table.add_row("Falhas", str(result.get('failed', 0)))
        
        if result.get('errors'):
            table.add_row("Erros", str(len(result['errors'])))
        
        console.print(table)
        
    except Exception as e:
        import traceback
        console.print(f"\n[red]Erro: {str(e)}[/red]")
        console.print(f"[red]Traceback:[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")
        console.print(f"[red]{traceback.format_exc()}[/red]")


def test_smtp_interactive():
    """Menu interativo para teste de SMTP."""
    try:
        config = Config("config/config.yaml")
        smtp = SmtpManager(config.smtp_config)
        
        console.print("\n[bold cyan]Testando conexão SMTP...[/bold cyan]")
        smtp.connect()
        console.print("[green]✅ Conexão SMTP estabelecida com sucesso[/green]\n")
        
    except Exception as e:
        console.print(f"\n[red]❌ Erro na conexão SMTP: {str(e)}[/red]\n")


def list_contacts():
    """Menu para listar contatos."""
    try:
        config = Config("config/config.yaml")
        db = Database(config)
        
        # Buscar contatos elegíveis
        query_path = "sql/contacts/select_recipients_for_message.sql"
        contacts = db.fetch_all(query_path, [False])
        
        console.print(f"\n[bold cyan]Encontrados {len(contacts)} contatos elegíveis[/bold cyan]\n")
        
        if contacts:
            table = Table(title="Contatos")
            table.add_column("ID", style="cyan")
            table.add_column("Email", style="magenta")
            
            for contact_id, email in contacts[:10]:  # Mostrar os primeiros 10
                table.add_row(str(contact_id), email)
            
            if len(contacts) > 10:
                table.add_row("[...]", f"+{len(contacts) - 10} mais")
            
            console.print(table)
        
    except Exception as e:
        console.print(f"\n[red]Erro: {str(e)}[/red]\n")


def import_contacts_csv():
    """Menu para importar contatos de arquivo CSV."""
    try:
        import csv
        from pathlib import Path
        
        csv_file = Path("contacts.csv")
        
        if not csv_file.exists():
            console.print(f"\n[red]❌ Arquivo 'contacts.csv' não encontrado[/red]")
            console.print("[yellow]Crie um arquivo 'contacts.csv' na raiz do projeto com coluna 'email'[/yellow]\n")
            return
        
        config = Config("config/config.yaml")
        db = Database(config)
        
        # Ler CSV
        emails = []
        duplicates = 0
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('email', '').strip().lower()
                if email:
                    if email in emails:
                        duplicates += 1
                    else:
                        emails.append(email)
        
        if not emails:
            console.print("\n[red]❌ Nenhum email encontrado no arquivo[/red]\n")
            return
        
        console.print(f"\n[bold cyan]Importando {len(emails)} contatos...[/bold cyan]")
        
        # Inserir no BD
        inserted = 0
        for email in emails:
            try:
                # Verificar se já existe
                check_query = "SELECT id FROM tbl_contacts WHERE email = %s LIMIT 1"
                existing = db.fetch_one(check_query, [email])
                
                if not existing:
                    insert_query = "INSERT INTO tbl_contacts (email, unsubscribed) VALUES (%s, false)"
                    db.execute(insert_query, [email])
                    inserted += 1
            except Exception as e:
                console.print(f"[red]Erro ao inserir {email}: {str(e)}[/red]")
        
        console.print(f"[green]✅ Importados {inserted} novos contatos[/green]")
        if duplicates > 0:
            console.print(f"[yellow]⚠️  {duplicates} duplicados ignorados[/yellow]")
        console.print()
        
    except Exception as e:
        console.print(f"\n[red]Erro na importação: {str(e)}[/red]\n")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, option: Optional[str] = typer.Argument(None)):
    """
    Menu interativo da CLI.
    
    Uso:
        uv run -m email_sender.cli        # Menu interativo
        uv run -m email_sender.cli 1      # Enviar emails
        uv run -m email_sender.cli 2      # Testar SMTP
        uv run -m email_sender.cli 3      # Ver contatos
        uv run -m email_sender.cli 4      # Importar contatos
        uv run -m email_sender.cli 5      # Sair
    """
    
    # Se passou um argumento, usar como opção
    if option:
        choice = option
    else:
        # Mostrar menu interativo
        choice = show_menu()
    
    # Processar escolha
    if choice == "1":
        send_emails_interactive()
    elif choice == "2":
        test_smtp_interactive()
    elif choice == "3":
        list_contacts()
    elif choice == "4":
        import_contacts_csv()
    elif choice == "5" or choice.lower() == "sair":
        console.print("\n[yellow]Até logo![/yellow]\n")
        raise typer.Exit(0)
    else:
        console.print("\n[red]Opção inválida![/red]\n")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
