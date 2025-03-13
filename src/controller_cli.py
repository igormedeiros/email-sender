import os
import logging
import typer
from typer import Exit
import json
import sys
import pandas as pd
from pathlib import Path
import signal
import time
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime, timedelta

from src.config import Config
from src.email_service import EmailService

# Configuração do logger
log = logging.getLogger("email_sender")

# Definição do modo de envio
class SendMode(str, Enum):
    test = "test"
    production = "production"

# Criação da aplicação Typer
app = typer.Typer()

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

# Novo comando para remover duplicados
@app.command()
def remove_duplicates(
    csv_file: str = typer.Argument(..., help="Caminho para o arquivo CSV a ser processado"),
    column: str = typer.Option("email", "--column", "-c", help="Coluna a ser usada para identificar duplicados"),
    keep: str = typer.Option("first", "--keep", "-k", help="Qual ocorrência manter ('first', 'last')"),
    output_file: str = typer.Option(None, "--output", "-o", help="Arquivo de saída. Se não especificado, substitui o original"),
    config_file: str = typer.Option("config/config.yaml", "--config", help="Caminho para o arquivo de configuração")
):
    """
    Remove linhas duplicadas de um arquivo CSV baseado em uma coluna específica.
    
    Por padrão, remove duplicados baseados na coluna 'email' e mantém a primeira ocorrência.
    """
    try:
        print(f"Removendo duplicados do arquivo {csv_file} baseado na coluna '{column}'...")
        
        # Inicializar o serviço de email com a configuração
        config = Config(config_file)
        email_service = EmailService(config)
        
        # Usar o método da classe EmailService
        try:
            result = email_service.remove_duplicates(
                csv_file=csv_file,
                column=column,
                keep=keep,
                output_file=output_file
            )
            
            # Exibir resultado
            duplicados_removidos = result["duplicados_removidos"]
            total_antes = result["total_antes"]
            total_depois = result["total_depois"]
            output_path = result["output_file"]
            backup_file = result["backup_file"]
            
            if duplicados_removidos > 0:
                print(f"✅ {duplicados_removidos} duplicados removidos com sucesso!")
                print(f"📊 Registros antes: {total_antes}")
                print(f"📊 Registros depois: {total_depois}")
                print(f"📄 Arquivo salvo em: {output_path}")
                if backup_file:
                    print(f"🔄 Backup criado em: {backup_file}")
            else:
                print(f"✅ Nenhum duplicado encontrado para a coluna '{column}'.")
                
        except FileNotFoundError as e:
            print(f"❌ Erro: {str(e)}")
            raise Exit(1)
        except ValueError as e:
            print(f"❌ Erro: {str(e)}")
            raise Exit(1)
            
    except Exception as e:
        print(f"❌ Erro ao remover duplicados: {str(e)}")
        raise Exit(1)

@app.command()
def send_emails(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    template: str = typer.Argument(..., help="Name of the HTML template file to use"),
    subject: str = typer.Option(None, "--subject", "-s", help="[OBSOLETO] O assunto será sempre lido do arquivo email.yaml"),
    titulo: str = typer.Option(None, "--titulo", "-t", help="Título personalizado para os emails"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
    skip_unsubscribed_sync: bool = typer.Option(False, "--skip-sync", help="Skip unsubscribed emails synchronization before sending"),
    mode: SendMode = typer.Option(..., help="Modo de envio obrigatório: especifique --mode=test ou --mode=production"),
):
    """
    Send batch HTML emails using a CSV file and HTML email template.
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
            
        email_service = EmailService(config)
        
        # Delegar a execução para o service
        result = email_service.process_email_sending(
            csv_file=csv_file,
            template=template,
            skip_unsubscribed_sync=skip_unsubscribed_sync,
            is_test_mode=(mode == SendMode.test)
        )
        
        print("\n✅ Email sending completed!")
        print(f"📊 Report saved to: reports/{result['report_file']}")
        print("\nReport Summary:")
        print(result['report'])
        print(f"⏱️ Tempo total de processamento: {result.get('duracao_formatada', '')}")
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

@app.command()
def test_smtp(
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Mostrar informações detalhadas de debug"),
):
    """
    Test SMTP connection by sending a test email to the configured test recipient.
    """
    try:
        config = Config(config_file, content_file)
        email_service = EmailService(config)
        
        test_recipient = config.email_config.get("test_recipient")
        if not test_recipient:
            raise ValueError("test_recipient not configured in properties file")
            
        print(f"\n📧 {test_recipient}")
        
        # Mostrar informações de debug
        if debug:
            print("\n=== INFORMAÇÕES DE CONEXÃO SMTP ===")
            print(f"Host: {config.smtp_config['host']}")
            print(f"Port: {config.smtp_config['port']}")
            print(f"Usuário: {config.smtp_config['username']}")
            print(f"Senha: {'*' * len(config.smtp_config['password']) if config.smtp_config['password'] else 'Não configurada'}")
            print(f"TLS: {'Sim' if config.smtp_config['use_tls'] else 'Não'}")
            print("=" * 35 + "\n")
        
        # Delegar para o serviço
        email_service.send_test_email(test_recipient)
        
        print(f"✅ {test_recipient}")
    
    except Exception as e:
        print(f"❌ {test_recipient}: {str(e)}")
        sys.exit(1)

@app.command()
def clear_sent_flags(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
):
    """
    Clear 'enviado' flags in CSV file, allowing emails to be sent again.
    """
    try:
        config = Config(config_file, content_file)
        email_service = EmailService(config)
        
        file_path = csv_file or config.email_config["csv_file"]
        
        print(f"Criando backup do arquivo {file_path} antes de prosseguir...")
        print(f"Limpando flags 'enviado' e 'falhou' de {file_path}...")
        
        # Delegar para o serviço
        cleared_count = email_service.clear_sent_flags(file_path)
        
        print(f"✅ {cleared_count} flags cleared successfully!")
        print(f"🔄 Um backup do arquivo original foi salvo em: backup/{Path(file_path).name}.bak")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

@app.command()
def sync_unsubscribed_command(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    unsubscribe_file: str = typer.Option(None, help="Path to CSV file with unsubscribed emails"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
):
    """
    Synchronize unsubscribed emails with the main CSV file.
    """
    try:
        config = Config(config_file, content_file)
        
        # Determinar arquivos a serem usados
        csv_path = csv_file or config.email_config["csv_file"]
        unsubscribe_path = unsubscribe_file or config.email_config.get("unsubscribe_file", "data/descadastros.csv")
        
        print(f"Sincronizando lista de descadastros {unsubscribe_path} com {csv_path}...")
        
        # Delegar para o serviço
        email_service = EmailService(config)
        updated_count = email_service.sync_unsubscribed_emails(csv_path, unsubscribe_path)
        
        print(f"✅ Sincronização concluída! {updated_count} emails atualizados.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app() 