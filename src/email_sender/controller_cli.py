import os
import logging
import typer
from typer import Exit
import json
import sys
from pathlib import Path
import signal
import time
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta

from .config import Config
from .db import Database
from .email_service import EmailService
from .utils.ui import (
    build_treineinsite_ascii_art,
    error,
    info,
    print_banner,
    success,
)
from .logging_config import setup_logging

# Configuração do logger
log = logging.getLogger("email_sender")

# Configurar logging
setup_logging()

# Definição do modo de envio
class SendMode(str, Enum):
    test = "test"
    production = "production"

# Criação da aplicação Typer
app = typer.Typer()

# ————————————————————————————————————
# Banner ASCII (Treineinsite)
# ————————————————————————————————————
def _print_treineinsite_banner() -> None:
    ascii_art = build_treineinsite_ascii_art()
    print_banner(ascii_art, subtitle="Treineinsite • Email Sender CLI")


@app.callback()
def _banner_callback() -> None:
    """Imprime o banner ASCII no início da execução do CLI."""
    _print_treineinsite_banner()

# Handler de timeout e interrupção
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

def interrupt_handler(signum, frame):
    print("\nProcess interrupted by user. Saving progress...")
    sys.exit(1)

# Configuração dos signal handlers
signal.signal(signal.SIGALRM, timeout_handler)
signal.signal(signal.SIGINT, interrupt_handler)


@app.command()
def send_emails(
    subject: str = typer.Option(None, "--subject", "-s", help="[OBSOLETO] O assunto será sempre lido do arquivo email.yaml"),
    titulo: str = typer.Option(None, "--titulo", "-t", help="Título personalizado para os emails"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
    skip_unsubscribed_sync: bool = typer.Option(False, "--skip-sync", help="Skip unsubscribed emails synchronization before sending"),
    mode: SendMode = typer.Option(None, help="Modo de envio: --mode=test ou --mode=production. Se omitido, usa ENVIRONMENT do .env")
):
    """
    Send batch HTML emails using database and HTML email template.
    The HTML template path is now read from the email.yaml configuration file.
    """
    try:
        print("\n===== INICIANDO PROCESSO DE ENVIO DE EMAILS =====")
        print(f"Arquivo de configuração: {config_file}")
        print(f"Arquivo de conteúdo: {content_file}")
        
        config = Config(config_file, content_file)
        
        # Aplicar título personalizado se fornecido
        if titulo:
            if "email" not in config.content_config:
                config.content_config["email"] = {}
            config.content_config["email"]["subject"] = titulo
            print(f"Título personalizado: {titulo}")

        # Obter o caminho do template do arquivo de configuração de conteúdo (email.yaml)
        template_path = config.content_config.get("email", {}).get("template_path")
        if not template_path:
            raise ValueError("O caminho do template (template_path) não está configurado no arquivo email.yaml.")
        print(f"Template de email a ser usado (de email.yaml): {template_path}")
            
        email_service = EmailService(config)

        # Resolver modo a partir do ENVIRONMENT se não for passado
        resolved_mode = mode.value if isinstance(mode, SendMode) else None
        if not resolved_mode:
            resolved_mode = "test" if config.environment_mode == "test" else "production"
        print(f"Modo resolvido: {resolved_mode} (ENVIRONMENT={config.environment_mode})")

        # Em ambiente de teste, usar base Postgres (sql/) e segmentação de teste
        result = email_service.process_email_sending(
                template=template_path,
                limit=3 if resolved_mode == "test" else 0,
                is_test_mode=(resolved_mode == "test")
            )
        
        print("\n✅ Email sending completed!")
        
        if 'report_file' in result and 'report' in result:
            print(f"📊 Report saved to: reports/{result['report_file']}")
            print("\nReport Summary:")
            print(result['report'])
            print(f"⏱️ Tempo total de processamento: {result.get('duracao_formatada', 'N/A')}")
        elif result.get("status") == "no_emails":
            # A mensagem "Nenhum email para enviar!" já é logada pelo email_service.
            # Adicionamos uma mensagem específica para a saída do CLI.
            print("Nenhum email foi processado, portanto, nenhum relatório foi gerado.")
        else:
            # Caso para estruturas inesperadas de 'result'
            print("Não foi possível exibir o resumo do relatório ou o resultado do processamento é inesperado. Verifique os logs.")
            # Opcionalmente, logar a estrutura inesperada de result para depuração:
            # from .logs import log
            # log.warning(f"Resultado inesperado do processamento de email: {result}")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

# test_smtp command removed as part of code cleanup


@app.command()
def reset_send_state(
    config_file: str = typer.Option(
        "config/config.yaml", "--config", "-c", help="Path to config file"
    ),
    content_file: str = typer.Option(
        "config/email.yaml", "--content", help="Path to email content file"
    ),
):
    """
    Limpa a tabela de estado de envio (tbl_send_state) para permitir um novo envio para toda a base.
    """
    try:
        info("Limpando estado de envio para permitir novo disparo...")
        cfg = Config(config_file, content_file)
        with Database(cfg) as db:
            db.execute("sql/runtime/reset_send_state.sql")
        success("Estado de envio reiniciado. Você pode disparar os emails novamente.")
    except Exception as e:
        error(f"Falha ao limpar o estado de envio: {e}")
        raise Exit(1)



@app.command()
def import_contacts_from_csv(
    config_file: str = typer.Option(
        "config/config.yaml", "--config", "-c", help="Path to config file"
    ),
    content_file: str = typer.Option(
        "config/email.yaml", "--content", help="Path to email content file"
    ),
):
    """
    Import contacts from a contacts.csv file in the project root.
    The CSV file should have a single column with the header 'email'.
    """
    try:
        info("Iniciando importação de contatos do arquivo contacts.csv...")
        
        # Define o caminho do arquivo CSV
        csv_path = Path.cwd() / "contacts.csv"
        
        if not csv_path.exists():
            error("Arquivo contacts.csv não encontrado na raiz do projeto.")
            info("Crie o arquivo com uma única coluna chamada 'email' e os contatos a serem importados.")
            return

        # Lê os e-mails do arquivo CSV
        import csv
        emails_to_import = set()
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Pula o cabeçalho
            if header != ['email']:
                error("O cabeçalho do arquivo contacts.csv deve ser 'email'.")
                return
            
            for row in reader:
                if row:
                    email = row[0].lower().strip()
                    if email:
                        emails_to_import.add(email)

        if not emails_to_import:
            info("Nenhum email para importar encontrado no arquivo.")
            return

        # Constrói a query SQL
        values_string = ",".join(f"('{email}', FALSE, FALSE)" for email in emails_to_import)
        sql_query = f"INSERT INTO tbl_contacts (email, unsubscribed, is_buyer) VALUES {values_string} ON CONFLICT (email) DO NOTHING;"

        # Escreve a query em um arquivo temporário
        sql_file_path = Path.cwd() / "temp_import_contacts.sql"
        with open(sql_file_path, "w") as f:
            f.write(sql_query)

        # Executa a importação
        cfg = Config(config_file, content_file)
        with Database(cfg) as db:
            rows_affected = db.execute(sql_file_path)
        
        success(f"Importação concluída! {rows_affected} novos contatos foram inseridos.")

    except Exception as e:
        error(f"Falha na importação: {e}")
    finally:
        # Limpa o arquivo SQL temporário
        if 'sql_file_path' in locals() and sql_file_path.exists():
            os.remove(sql_file_path)


if __name__ == "__main__":
    app()
