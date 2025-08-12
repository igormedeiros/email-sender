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

from .config import Config # Changed to relative import
from .email_service import EmailService # Changed to relative import
from .utils.ui import print_banner, build_treineinsite_ascii_art

# Configuração do logger
log = logging.getLogger("email_sender")

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
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    subject: str = typer.Option(None, "--subject", "-s", help="[OBSOLETO] O assunto será sempre lido do arquivo email.yaml"),
    titulo: str = typer.Option(None, "--titulo", "-t", help="Título personalizado para os emails"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
    skip_unsubscribed_sync: bool = typer.Option(False, "--skip-sync", help="Skip unsubscribed emails synchronization before sending"),
    mode: SendMode = typer.Option(None, help="Modo de envio: --mode=test ou --mode=production. Se omitido, usa ENVIRONMENT do .env"),
    bounces_file: str = typer.Option("data/bounces.csv", "--bounces-file", help="Caminho para o arquivo CSV com emails de bounce (coluna 'email')")
):
    """
    Send batch HTML emails using a CSV file and HTML email template.
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
        if resolved_mode == "test" and not csv_file:
            print("Ambiente de teste detectado — enviando para segmento de teste no Postgres (sql/)...")
            result = email_service.send_email_to_test_recipient(template_path)
        else:
            # Caminho legado/compatível: permite CSV explícito quando informado
            result = email_service.process_email_sending(
                csv_file=csv_file,
                template=template_path,
                skip_unsubscribed_sync=skip_unsubscribed_sync,
                is_test_mode=(resolved_mode == "test"),
                bounces_file_path=bounces_file
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


if __name__ == "__main__":
    app()