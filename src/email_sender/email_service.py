import smtplib
import csv
import os
import logging
import pandas as pd
import time
import ssl
import socket
import re
import shutil
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from contextlib import contextmanager
from datetime import datetime
import signal
import math

from .config import Config
from .utils.csv_reader import CSVReader
from .email_templating import TemplateProcessor
from .db_utils import get_db_connection, get_unsubscribed_emails as db_get_unsubscribed_emails
from .reporting import ReportGenerator
from .smtp_manager import SmtpManager

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config
        # Passa apenas content_config para o TemplateProcessor para garantir compatibilidade
        self.template_processor = TemplateProcessor(config.content_config if hasattr(config, 'content_config') else config)
        self.report_generator = ReportGenerator(reports_dir=self.config.email_config.get("reports_dir", "reports"))
        self.smtp_manager = SmtpManager(config)

    def clear_sent_flags(self, csv_file: str, columns_to_clear: List[str] = ["enviado", "falhou"]) -> Dict[str, Any]:
        """
        Clears specified flag columns in a CSV file.
        Sets the values in these columns to False.
        Creates a backup of the original file.
        """
        try:
            log.info(f"Limpando flags {columns_to_clear} do arquivo {csv_file}...")
            
            if not Path(csv_file).exists():
                raise FileNotFoundError(f"Arquivo {csv_file} não encontrado")

            # Create backup
            backup_file_path = self.create_backup(csv_file)
            log.info(f"Backup do arquivo {csv_file} criado em: {backup_file_path}")

            try:
                df = pd.read_csv(csv_file, sep=None, engine='python', dtype=str) # Read all as string to preserve data
            except Exception as e:
                raise ValueError(f"Erro ao ler o arquivo CSV {csv_file}: {str(e)}")

            original_row_count = len(df)
            cleared_flags_count = {}

            for col in columns_to_clear:
                if col in df.columns:
                    # Count how many flags will be cleared (e.g., were True or non-empty)
                    # Assuming flags are stored as strings 'True', 'true', '1' or just non-empty
                    # For simplicity, we'll just clear them to empty string or a specific "False" marker
                    # If they are boolean, pandas will handle it. If strings, this sets to empty.
                    cleared_flags_count[col] = df[col].astype(bool).sum() # Example: count previously true flags
                    df[col] = "" # Set to empty string, or False if column is boolean
                else:
                    log.warning(f"Coluna '{col}' não encontrada no arquivo {csv_file}. Nenhuma flag será limpa para esta coluna.")
                    cleared_flags_count[col] = 0
            
            df.to_csv(csv_file, index=False)
            log.info(f"Flags {columns_to_clear} limpas com sucesso em {csv_file}.")

            return {
                "status": "success",
                "csv_file": csv_file,
                "backup_file": backup_file_path,
                "original_row_count": original_row_count,
                "cleared_flags_count": cleared_flags_count
            }

        except Exception as e:
            log.error(f"Erro ao limpar flags no arquivo {csv_file}: {str(e)}")
            # Re-raise the exception so the CLI can catch it and report
            raise

    def load_unsubscribed_emails(self) -> set:
        """
        Carrega emails da lista de descadastro do banco de dados.
        Retorna um set de emails em lower case.
        """
        unsubscribed_emails_set = set()
        conn = None
        try:
            # Get table name from postgres_config
            # Using .get for safety, though direct access was in prompt, this is more robust
            table_name = self.config.postgres_config.get('POSTGRES_UNSUBSCRIBE_TABLE', 'unsubscribed_users')
            if not table_name: # Should not happen if config is well-defined
                log.error("PostgreSQL unsubscribe table name not configured.")
                return unsubscribed_emails_set

            conn = get_db_connection(self.config)
            if conn:
                email_list = db_get_unsubscribed_emails(conn, table_name)
                unsubscribed_emails_set = {email.lower() for email in email_list if isinstance(email, str)}
                log.info(f"Carregados {len(unsubscribed_emails_set)} emails da lista de descadastro (tabela: {table_name}).")
            else:
                log.error("Falha ao obter conexão com o banco de dados para carregar emails descadastrados.")
        except AttributeError:
            log.error("Erro ao acessar postgres_config. Certifique-se de que está configurado corretamente.")
        except Exception as e:
            log.error(f"Erro ao carregar emails descadastrados do banco de dados: {e}")
        finally:
            if conn:
                conn.close()
        return unsubscribed_emails_set

    def load_bounced_emails(self, bounces_file: Optional[str] = None) -> set:
        """
        Carrega emails da lista de bounces ativos.
        Retorna um set de emails em lower case.
        """
        bounces_path = Path(bounces_file or self.config.email_config.get("bounces_file", "data/bounces.csv"))
        bounced_emails = set()
        if bounces_path.exists():
            try:
                df_bounces = pd.read_csv(bounces_path, dtype=str)
                if "email" in df_bounces.columns:
                    bounced_emails = set(df_bounces["email"].str.lower().dropna().unique())
                    log.info(f"Carregados {len(bounced_emails)} emails da lista de bounces: {bounces_path}")
                else:
                    log.warning(f"Coluna 'email' não encontrada em {bounces_path}. Nenhum email de bounce carregado.")
            except Exception as e:
                log.error(f"Erro ao carregar arquivo de bounces {bounces_path}: {e}")
        else:
            log.warning(f"Arquivo de bounces {bounces_path} não encontrado. Nenhum email de bounce carregado.")
        return bounced_emails

    def sync_unsubscribed_emails(self, csv_file: str) -> int:
        """
        Marca emails descadastrados no arquivo CSV principal.
        Adiciona/atualiza a coluna 'unsubscribed' para True para emails encontrados na lista de descadastro.
        Retorna o número de emails atualizados.
        """
        log.info(f"Iniciando sincronização de descadastrados para {csv_file} usando banco de dados.")
        unsubscribed_set = self.load_unsubscribed_emails() # Updated call
        if not unsubscribed_set:
            log.info("Nenhum email na lista de descadastro do banco de dados. Nenhuma sincronização necessária.")
            return 0

        try:
            df = pd.read_csv(csv_file, dtype=str)
            if "email" not in df.columns:
                raise ValueError(f"Coluna 'email' não encontrada no arquivo CSV principal {csv_file}")

            original_unsubscribed_count = 0
            if "unsubscribed" in df.columns:
                # Lida com a coluna unsubscribed sem causar warning de downcasting
                df["unsubscribed"] = df["unsubscribed"].astype(str).replace(
                    {'true': 'True', '1': 'True', 'yes': 'True', 'nan': '', '': ''}).map(
                    {'True': True}).fillna(False)
                original_unsubscribed_count = df["unsubscribed"].sum()
            else:
                df["unsubscribed"] = False

            updated_count = 0
            for index, row in df.iterrows():
                if pd.notna(row["email"]):
                    email_lower = str(row["email"]).lower()
                    if email_lower in unsubscribed_set:
                        if not df.at[index, "unsubscribed"]:
                            df.at[index, "unsubscribed"] = True
                            updated_count += 1
            
            if updated_count > 0:
                df.to_csv(csv_file, index=False)
                log.info(f"{updated_count} emails marcados como descadastrados em {csv_file}.")
            else:
                log.info(f"Nenhum email novo precisou ser marcado como descadastrado em {csv_file}.")
            
            current_unsubscribed_count = df["unsubscribed"].sum()
            log.info(f"Total de descadastrados antes: {original_unsubscribed_count}, depois: {current_unsubscribed_count}")
            return updated_count

        except FileNotFoundError:
            log.error(f"Arquivo CSV principal {csv_file} não encontrado para sincronização de descadastrados.")
            raise
        except Exception as e:
            log.error(f"Erro ao sincronizar emails descadastrados em {csv_file}: {e}")
            raise

    def sync_bounced_emails(self, csv_file: str, bounces_file: Optional[str] = None) -> int:
        """
        Marca emails com bounce no arquivo CSV principal.
        Adiciona/atualiza a coluna 'bounced' para True para emails encontrados na lista de bounces.
        Retorna o número de emails atualizados.
        """
        # Configuração do Rich
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn
        
        console = Console()
        console.print(f"[bold]Iniciando sincronização de bounces[/bold] para [cyan]{csv_file}[/cyan]")
        
        bounced_set = self.load_bounced_emails(bounces_file)
        if not bounced_set:
            console.print("[yellow]Nenhum email na lista de bounces. Nenhuma sincronização necessária.[/yellow]")
            return 0

        try:
            with console.status(f"Lendo arquivo CSV {csv_file}...") as status:
                df = pd.read_csv(csv_file, dtype=str)
                
            if "email" not in df.columns:
                console.print(f"[bold red]Erro: Coluna 'email' não encontrada no arquivo CSV principal {csv_file}[/bold red]")
                raise ValueError(f"Coluna 'email' não encontrada no arquivo CSV principal {csv_file}")

            original_bounced_count = 0
            if "bounced" in df.columns:
                # Lida com a coluna bounced sem causar warning de downcasting
                df["bounced"] = df["bounced"].astype(str).replace(
                    {'true': 'True', '1': 'True', 'yes': 'True', 'nan': '', '': ''}).map(
                    {'True': True}).fillna(False)
                original_bounced_count = df["bounced"].sum()
                console.print(f"Encontrados [yellow]{original_bounced_count}[/yellow] emails já marcados como bounce.")
            else:
                df["bounced"] = False
                console.print("Coluna 'bounced' não encontrada. Criando nova coluna.")

            updated_count = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[green]Sincronizando emails com bounce...", total=len(df))
                
                for index, row in df.iterrows():
                    progress.update(task, advance=1)
                    
                    if pd.notna(row["email"]):
                        email_lower = str(row["email"]).lower()
                        if email_lower in bounced_set:
                            if not df.at[index, "bounced"]:
                                df.at[index, "bounced"] = True
                                updated_count += 1
            
            if updated_count > 0:
                # Salvar o arquivo atualizado
                console.print(f"[bold green]Salvando {updated_count} novos emails marcados como bounce...[/bold green]")
                df.to_csv(csv_file, index=False)
                console.print(f"[green]✓[/green] {updated_count} emails marcados como bounced em {csv_file}.")
            else:
                console.print("[yellow]Nenhum email novo precisou ser marcado como bounced.[/yellow]")

            current_bounced_count = df["bounced"].sum()
            console.print(f"[bold]Total de bounces:[/bold] antes: [cyan]{original_bounced_count}[/cyan], depois: [cyan]{current_bounced_count}[/cyan]")
            return updated_count

        except FileNotFoundError:
            console.print(f"[bold red]Erro: Arquivo CSV principal {csv_file} não encontrado.[/bold red]")
            raise
        except Exception as e:
            console.print(f"[bold red]Erro ao sincronizar emails com bounce: {e}[/bold red]")
            raise

    def send_batch(self, recipients: List[Dict], content: str, subject: str, is_html: bool = False) -> None:
        if not recipients:
            log.warning("send_batch called with no recipients.")
            return

        recipient_email = recipients[0].get("email")
        if not recipient_email:
            log.error("Recipient email missing in send_batch call.")
            raise ValueError("Recipient email missing in send_batch call")

        try:
            log.debug(f"Using SmtpManager to send email to {recipient_email} with subject \"{subject}\"")
            self.smtp_manager.send_email(
                to_email=recipient_email,
                subject=subject,
                content=content,
                is_html=is_html
            )
            log.debug(f"Email to {recipient_email} passed to SmtpManager.")
        except Exception as e:
            log.error(f"SmtpManager failed to send email to {recipient_email}: {str(e)}")
            raise

    def process_email_template(self, template_path: str, recipient: Dict, email_subject: str) -> str:
        """
        Processa o template HTML, substituindo as variáveis pelos valores do destinatário.
        
        Args:
            template_path: Caminho para o arquivo de template HTML
            recipient: Dicionário com os dados do destinatário
            email_subject: Assunto do email (can be used by template processor if needed)
            
        Returns:
            HTML formatado
        """
        try:
            # Corrected method call to 'process' and ensure template_path is a Path object
            return self.template_processor.process(Path(template_path), recipient)
        except Exception as e:
            log.error(f"Erro ao processar template via TemplateProcessor: {str(e)}")
            if isinstance(e, AttributeError):
                log.exception("AttributeError details:")
            raise

    def generate_report(self, start_time: float, end_time: float, total_sent: int, successful: int, failed: int) -> Dict[str, Any]:
        """
        Gera um relatório do processo de envio de emails usando ReportGenerator.
        """
        try:
            return self.report_generator.generate_report(start_time, end_time, total_sent, successful, failed)
        except Exception as e:
            log.error(f"Erro ao gerar relatório via ReportGenerator: {str(e)}")
            raise

    def remove_duplicates(self, csv_file: str, column: str = "email", keep: str = "first", output_file: Optional[str] = None) -> Dict[str, Any]:
        try:
            log.info(f"Removendo duplicados do arquivo {csv_file} baseado na coluna '{column}'...")
            
            if not Path(csv_file).exists():
                raise FileNotFoundError(f"Arquivo {csv_file} não encontrado")
            
            try:
                df = pd.read_csv(csv_file, sep=None, engine='python')
            except Exception as e:
                raise ValueError(f"Erro ao ler o arquivo CSV: {str(e)}")
            
            if column not in df.columns:
                raise ValueError(f"Coluna '{column}' não encontrada no arquivo CSV")
            
            total_antes = len(df)
            df_without_duplicates = df.drop_duplicates(subset=[column], keep=keep)
            total_depois = len(df_without_duplicates)
            duplicados_removidos = total_antes - total_depois
            
            if not output_file:
                backup_dir = Path("backup")
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"{Path(csv_file).stem}_{timestamp}.csv"
                
                shutil.copy2(csv_file, backup_file)
                log.info(f"Backup criado em: {backup_file}")
                
                output_path = csv_file
            else:
                output_path = output_file
                backup_file = None
            
            df_without_duplicates.to_csv(output_path, index=False)
            
            result = {
                "status": "success",
                "total_antes": total_antes,
                "total_depois": total_depois,
                "duplicados_removidos": duplicados_removidos,
                "output_file": str(output_path),
                "backup_file": str(backup_file) if backup_file else None
            }
            
            if duplicados_removidos > 0:
                log.info(f"{duplicados_removidos} duplicados removidos com sucesso!")
            else:
                log.info(f"Nenhum duplicado encontrado para a coluna '{column}'.")
                
            return result
                
        except Exception as e:
            log.error(f"Erro ao remover duplicados: {str(e)}")
            raise

    def send_test_email(self, recipient: str) -> bool:
        """
        Envia um email de teste para verificar a conexão com o servidor SMTP.
        
        Args:
            recipient: Endereço de email do destinatário de teste
            
        Returns:
            True se o email foi enviado com sucesso, False caso contrário
        """
        try:
            # Configurar console e formatação Rich
            from rich.console import Console
            from rich.panel import Panel
            
            console = Console()
            console.rule("[bold blue]Envio de Email de Teste[/bold blue]")
            
            email_subject = self.config.content_config.get("email", {}).get("subject", "SMTP Test Email")
            message_content = "This is a test email from the email-sender application."
            
            console.print(f"[bold]Enviando email de teste para:[/bold] [cyan]{recipient}[/cyan]")
            console.print(f"[bold]Assunto:[/bold] [magenta]{email_subject}[/magenta]")
            
            with console.status("[bold yellow]Enviando email de teste...[/bold yellow]") as status:
                self.smtp_manager.send_email(
                    to_email=recipient,
                    subject=email_subject,
                    content=message_content,
                    is_html=False
                )
            
            # Mostrar painel de sucesso
            success_message = f"✅ Email de teste enviado com sucesso para {recipient}!"
            console.print(Panel.fit(
                success_message,
                title="Sucesso",
                border_style="green",
                padding=(1, 2)
            ))
            
            # Mostrar informações do servidor SMTP usado
            servidor = self.config.email_config.get("smtp_server", "N/A")
            porta = self.config.email_config.get("smtp_port", "N/A")
            usuario = self.config.email_config.get("smtp_user", "N/A")
            
            console.print("\n[bold]Detalhes da conexão:[/bold]")
            console.print(f"Servidor SMTP: [cyan]{servidor}[/cyan]")
            console.print(f"Porta: [cyan]{porta}[/cyan]")
            console.print(f"Usuário: [cyan]{usuario}[/cyan]")
            
            return True
            
        except Exception as e:
            # Configurar console e formatação Rich para erro
            from rich.console import Console
            from rich.panel import Panel
            
            console = Console()
            
            # Mostrar painel de erro
            error_message = f"❌ Falha ao enviar email de teste para {recipient}:\n\n{str(e)}"
            console.print(Panel.fit(
                error_message,
                title="Erro",
                border_style="red",
                padding=(1, 2)
            ))
            
            # Verificar se é um problema de autenticação ou conexão
            error_str = str(e).lower()
            if "authentication" in error_str or "auth" in error_str:
                console.print("[bold yellow]Dica:[/bold yellow] Parece ser um problema de autenticação. Verifique seu nome de usuário e senha SMTP.")
            elif "connection" in error_str or "timeout" in error_str:
                console.print("[bold yellow]Dica:[/bold yellow] Parece ser um problema de conexão. Verifique se o servidor SMTP está acessível e a porta correta está sendo usada.")
            
            # Mostrar informações do servidor que tentou usar
            servidor = self.config.email_config.get("smtp_server", "N/A")
            porta = self.config.email_config.get("smtp_port", "N/A")
            usuario = self.config.email_config.get("smtp_user", "N/A")
            
            console.print("\n[bold]Detalhes da conexão tentada:[/bold]")
            console.print(f"Servidor SMTP: [cyan]{servidor}[/cyan]")
            console.print(f"Porta: [cyan]{porta}[/cyan]")
            console.print(f"Usuário: [cyan]{usuario}[/cyan]")
            
            log.error(f"Error sending test email via SmtpManager: {str(e)}")
            raise

    def create_backup(self, file_path: str) -> str:
        """
        Cria um backup do arquivo especificado.
        
        Args:
            file_path: Caminho do arquivo a ser copiado
            
        Returns:
            Caminho do arquivo de backup criado
        """
        try:
            backup_dir = Path("backup")
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"{Path(file_path).stem}_{timestamp}.csv"
            
            shutil.copy2(file_path, backup_file)
            log.info(f"Backup criado em: {backup_file}")
            
            return str(backup_file)
        except Exception as e:
            log.error(f"Erro ao criar backup: {str(e)}")
            raise

    def process_email_sending(self, csv_file: str = None, template: str = "", skip_unsubscribed_sync: bool = False, is_test_mode: bool = True, bounces_file_path: str = "data/bounces.csv") -> Dict[str, Any]:
        """
        Processa o envio de emails em lote com base em um arquivo CSV e um template HTML.
        """
        try:
            # Configurar console e formatação Rich
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
            from rich.rule import Rule
            from rich.box import ROUNDED
            from rich.text import Text
            
            console = Console()
            console.rule("[bold blue]Iniciando Processo de Envio de Emails[/bold blue]", style="blue")
            
            start_time = time.time()
            successful = 0
            failed = 0
            skipped_unsubscribed = 0
            skipped_bounced = 0
            total_send_attempts = 0

            # Determine the CSV file to use
            if csv_file:
                actual_csv_file = csv_file
            elif is_test_mode:
                actual_csv_file = self.config.email_config.get("test_csv_file", "data/test_emails.csv")
                console.print(f"Modo de teste: Usando CSV de teste: [cyan]{actual_csv_file}[/cyan]")
            else:
                actual_csv_file = self.config.email_config.get("csv_file")
                console.print(f"Modo de produção: Usando CSV padrão: [cyan]{actual_csv_file}[/cyan]")

            if not actual_csv_file:
                console.print("[bold red]Erro: Caminho do arquivo CSV não especificado e não encontrado na configuração.[/bold red]")
                raise ValueError("Caminho do arquivo CSV não especificado e não encontrado na configuração.")
            
            if not Path(actual_csv_file).exists():
                console.print(f"[bold red]Erro: Arquivo CSV especificado não encontrado: {actual_csv_file}[/bold red]")
                raise FileNotFoundError(f"Arquivo CSV especificado não encontrado: {actual_csv_file}")

            pause_duration_after_attempts = self.config.email_config.get("batch_delay", 60)
            retry_attempts_config = self.config.email_config.get("retry_attempts", 3)
            retry_delay_config = self.config.email_config.get("retry_delay", 60)
            send_timeout = self.config.email_config.get("send_timeout", 10)
            max_retry_minutes = self.config.email_config.get("max_retry_minutes", 5)  # Tempo máximo para tentativas em caso de falha de conexão
            
            # Exibir configurações de envio
            console.print("\n[bold]Configurações de envio:[/bold]")
            console.print(f"Tempo máximo de tentativas: [cyan]{max_retry_minutes} minutos[/cyan]")
            console.print(f"Número máximo de tentativas: [cyan]{retry_attempts_config}[/cyan]")
            console.print(f"Tempo entre tentativas: [cyan]{retry_delay_config}s[/cyan]")
            console.print(f"Timeout por tentativa: [cyan]{send_timeout}s[/cyan]")
            console.print(f"Pausa entre lotes: [cyan]{pause_duration_after_attempts}s[/cyan]")

            # Carregar lista de emails descadastrados e bounces
            console.print("\n[bold]Carregando listas de descadastros e bounces...[/bold]")
            unsubscribed = self.load_unsubscribed_emails()
            active_bounced_set = self.load_bounced_emails(bounces_file_path)

            # Load batch_size with a default and ensure it's positive
            configured_batch_size = self.config.email_config.get("batch_size", 30)
            if configured_batch_size <= 0:
                log.warning(f"Configured batch_size ({configured_batch_size}) is not positive. Defaulting to 30.")
                configured_batch_size = 30
            
            csv_reader = CSVReader(actual_csv_file, configured_batch_size)
            email_subject = self.config.content_config.get("email", {}).get("subject", "Sem assunto")
            console.print(f"Assunto do email: [bold magenta]'{email_subject}'[/bold magenta]")

            if not template.endswith('.html'):
                template += '.html'
                
            template_path_obj = Path(template)
            if not template_path_obj.exists():
                root_template_path = Path("templates") / template_path_obj.name
                if root_template_path.exists():
                    template_path_obj = root_template_path
                    console.print(f"Template encontrado em: [green]templates/{template_path_obj.name}[/green]")
                else:
                    console.print(f"[bold red]Erro: Template não encontrado: {template}[/bold red]")
                    raise FileNotFoundError(f"Template file not found: {template}")
            else:
                template_path_obj = template_path_obj.resolve()
                console.print(f"Template encontrado em: [green]{template_path_obj}[/green]")

            total_records = csv_reader.total_records
            if total_records == 0:
                console.print(f"[bold yellow]Atenção: Nenhum registro encontrado no arquivo CSV: {actual_csv_file}[/bold yellow]")
                return {"status": "no_emails", "total_records": 0}
                
            console.print(f"\n[bold]Total de registros para processar: [cyan]{total_records}[/cyan][/bold]")
            
            # Configurar tabela para exibir informações de envio em tempo real
            email_table = Table(title="Informações de Envio de Emails", box=ROUNDED, show_header=True)
            email_table.add_column("Email", style="cyan")
            email_table.add_column("Status", style="bold")
            email_table.add_column("Tentativas", style="yellow")
            email_table.add_column("Detalhes", style="dim")
            
            # Lista para armazenar resultados de envio para exibir depois
            email_results = []

            try:
                class TimeoutException(Exception):
                    pass
                
                def timeout_handler(signum, frame):
                    raise TimeoutException
                
                signal.signal(signal.SIGALRM, timeout_handler)
                
                total_batches = 0
                if csv_reader.batch_size > 0:
                    total_batches = math.ceil(csv_reader.total_records / csv_reader.batch_size)
                
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    progress_task = progress.add_task("[green]Processando emails...", total=total_records)
                    
                    processed_in_batch_count = 0 # Counter for actual emails processed in the current batch period
                    
                    for batch_idx, batch_recipients in enumerate(csv_reader.get_batches()):
                        if not batch_recipients: # If the batch from CSVReader is empty, skip to next potential batch
                            log.debug(f"Lote {batch_idx + 1}/{int(total_batches)} estava vazio (todos os destinatários filtrados). Pulando.")
                            continue

                        batch_panel = Text(f"Lote {batch_idx + 1}/{int(total_batches)} - Processando {len(batch_recipients)} destinatários", style="bold blue")
                        progress.console.print(batch_panel)
                        
                        current_batch_processed_count = 0 # Emails processed in this specific non-empty batch

                        for recipient in batch_recipients:
                            progress.update(progress_task, advance=1) # Advance based on total_records from CSVReader
                            recipient_email = recipient.get('email', '').strip()
                            
                            if not recipient_email:
                                email_results.append({
                                    'email': 'Missing email',
                                    'status': '[red]Erro[/red]',
                                    'tentativas': '0',
                                    'detalhes': 'Email ausente no CSV'
                                })
                                failed += 1
                                continue
                                
                            recipient_email_lower = recipient_email.lower()

                            # Verificar se o email está na lista de bounces
                            if recipient_email_lower in active_bounced_set:
                                email_results.append({
                                    'email': recipient_email,
                                    'status': '[yellow]Pulado[/yellow]',
                                    'tentativas': '0',
                                    'detalhes': 'Email na lista de bounces'
                                })
                                skipped_bounced += 1
                                continue 

                            # Verificar se o email está na lista de descadastros
                            if recipient_email_lower in unsubscribed:
                                email_results.append({
                                    'email': recipient_email,
                                    'status': '[yellow]Pulado[/yellow]',
                                    'tentativas': '0',
                                    'detalhes': 'Email descadastrado'
                                })
                                skipped_unsubscribed += 1
                                continue
                            
                            total_send_attempts += 1
                            
                            attempts = 0
                            max_retry_minutes = 5  # Tempo máximo de tentativas em minutos
                            start_retry_time = time.time()
                            max_retry_time = start_retry_time + (max_retry_minutes * 60)
                            # Lista de padrões que indicam problemas de conexão ou rede
                            connection_errors = [
                                "connection refused", "network is unreachable", "timed out", 
                                "name or service not known", "temporary failure", "no route to host",
                                "connection reset", "connection error", "network error", "socket error",
                                "dns unavailable", "timeout", "service unavailable", "try again later", 
                                "server busy", "connection lost", "temporarily rejected", "network down",
                                "eof", "broken pipe", "refused", "host unreachable", "operation timed out", 
                                "operation would block", "no address associated", "network dropped",
                                "bad connection", "no response", "port unreachable", "cannot connect", 
                                "temporary error", "network failure", "proxy error", "ssl error", 
                                "name resolution", "circuit", "disconnected", "internet access", 
                                "resource unavailable", "gateway", "routing"
                            ]
                            
                            # Define uma função para verificar se uma string contém algum padrão de erro de conexão
                            def is_connection_error(error_text):
                                error_text = error_text.lower()
                                return any(err_pattern in error_text for err_pattern in connection_errors)
                            
                            while True:
                                # Verificar se atingiu o número máximo de tentativas OU o tempo máximo de tentativas
                                if attempts >= retry_attempts_config and time.time() >= max_retry_time:
                                    progress.console.print(f"[red]❌ Número máximo de tentativas e tempo esgotados para {recipient_email}[/red]")
                                    failed += 1
                                    
                                    email_results.append({
                                        'email': recipient_email,
                                        'status': '[red]Falha[/red]',
                                        'tentativas': f"{attempts} (tempo esgotado)",
                                        'detalhes': 'Tempo máximo de tentativas esgotado (5 minutos)'
                                    })
                                    break
                                
                                try:
                                    attempts += 1
                                    tempo_decorrido = time.time() - start_retry_time
                                    tempo_restante = max(0, max_retry_time - time.time())
                                    
                                    progress.console.print(
                                        f"Tentando enviar para: [bold cyan]{recipient_email}[/bold cyan] "
                                        f"(Tentativa {attempts}/{retry_attempts_config}, "
                                        f"Tempo restante: {tempo_restante:.1f}s)"
                                    )
                                    signal.alarm(send_timeout)
                                    
                                    html_content = self.process_email_template(str(template_path_obj), recipient, email_subject)
                                    
                                    self.smtp_manager.send_email(
                                        to_email=recipient_email,
                                        subject=email_subject,
                                        content=html_content,
                                        is_html=True
                                    )
                                    
                                    signal.alarm(0)
                                    progress.console.print(f"[green]✅ Email enviado com sucesso para {recipient_email}[/green]")
                                    successful += 1
                                    
                                    email_results.append({
                                        'email': recipient_email,
                                        'status': '[green]Enviado[/green]',
                                        'tentativas': str(attempts),
                                        'detalhes': 'Enviado com sucesso'
                                    })
                                    break
                                    
                                except TimeoutException:
                                    signal.alarm(0)
                                    # Timeout é um problema de conexão, então ele tentará novamente se ainda estiver dentro do limite de tempo
                                    if time.time() < max_retry_time:
                                        progress.console.print(f"[yellow]⚠️ Timeout ao enviar para {recipient_email}. Tentando novamente em {retry_delay_config}s...[/yellow]")
                                        time.sleep(retry_delay_config)
                                        continue
                                    else:
                                        progress.console.print(f"[red]❌ Timeout ao enviar para {recipient_email} - tempo máximo excedido[/red]")
                                        failed += 1
                                        
                                        email_results.append({
                                            'email': recipient_email,
                                            'status': '[red]Falha[/red]',
                                            'tentativas': str(attempts),
                                            'detalhes': f'Timeout após {send_timeout}s (tempo máximo excedido)'
                                        })
                                        break
                                    
                                except Exception as e:
                                    signal.alarm(0)
                                    error_str = str(e).lower()
                                    error_is_connection_related = is_connection_error(error_str)
                                    
                                    # Se for erro de conexão e ainda estiver dentro do limite de tempo, tenta novamente
                                    if error_is_connection_related and time.time() < max_retry_time:
                                        wait_time = min(retry_delay_config, 30)  # No máximo 30s entre tentativas
                                        tempo_restante = max(0, (max_retry_time - time.time()) / 60)
                                        
                                        progress.console.print(
                                            f"[yellow]⚠️ Erro de conexão ao enviar para {recipient_email} "
                                            f"(Tentativa {attempts}): {str(e)}[/yellow]"
                                        )
                                        progress.console.print(f"[blue]🔄 Aguardando {wait_time}s antes de tentar novamente... "
                                                              f"(Tempo restante: {tempo_restante:.1f} min)[/blue]")
                                        time.sleep(wait_time)
                                        continue
                                    # Se atingiu o número de tentativas OU não é erro de conexão OU tempo esgotado
                                    elif attempts >= retry_attempts_config or not error_is_connection_related or time.time() >= max_retry_time:
                                        if error_is_connection_related:
                                            reason = "tempo máximo excedido" if time.time() >= max_retry_time else f"após {attempts} tentativas"
                                            progress.console.print(f"[red]❌ Falha de conexão ao enviar para {recipient_email} - {reason}: {str(e)}[/red]")
                                        else:
                                            progress.console.print(f"[red]❌ Falha ao enviar para {recipient_email}: {str(e)}[/red]")
                                        
                                        failed += 1
                                        email_results.append({
                                            'email': recipient_email,
                                            'status': '[red]Falha[/red]',
                                            'tentativas': str(attempts),
                                            'detalhes': str(e)[:50] + ('...' if len(str(e)) > 50 else '')
                                        })
                                        break
                                    else:
                                        progress.console.print(f"[yellow]⚠️ Falha temporária ao enviar para {recipient_email} (Tentativa {attempts}/{retry_attempts_config}): {str(e)}[/yellow]")
                                        if retry_delay_config > 0:
                                            progress.console.print(f"[yellow]Aguardando {retry_delay_config}s antes da próxima tentativa...[/yellow]")
                                            time.sleep(retry_delay_config)
                            
                            # Increment counter for emails actually attempted in this batch
                            if recipient_email: # Ensure we count only if there was an email to process
                                current_batch_processed_count +=1
                        
                        # NEW PAUSE LOGIC: Pause after processing a non-empty batch, if it's not the last batch and delay is positive
                        # And if actual emails were processed in this batch.
                        if current_batch_processed_count > 0 and total_batches > 0 and batch_idx < total_batches - 1 and pause_duration_after_attempts > 0:
                            pause_message = f"Pausa de {pause_duration_after_attempts}s após o lote {batch_idx + 1}/{int(total_batches)} (processou {current_batch_processed_count} emails)"
                            progress.console.print(f"[blue]{pause_message}[/blue]")
                            time.sleep(pause_duration_after_attempts)
                    
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Processo interrompido pelo usuário.[/bold yellow]")
            finally:
                signal.alarm(0)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Exibir resultados em uma tabela formatada
            console.rule("[bold blue]Relatório de Envio de Emails[/bold blue]")
            
            # Mostrar tabela de resultados
            for result in email_results:
                email_table.add_row(
                    result['email'],
                    result['status'],
                    result['tentativas'],
                    result['detalhes']
                )
            
            console.print(email_table)
            
            # Tabela de resumo
            summary_table = Table(title="Resumo de Envio", box=ROUNDED)
            summary_table.add_column("Métrica", style="cyan")
            summary_table.add_column("Valor", style="bold")
            
            # Calcular métricas adicionais
            total_attempts = sum(int(r.get('tentativas', '1').split()[0]) for r in email_results if r.get('tentativas', '').strip() != '')
            avg_attempts_per_email = total_attempts / max(1, successful + failed)
            total_connection_errors = sum(1 for r in email_results if 'tempo' in r.get('detalhes', '').lower() or 'timeout' in r.get('detalhes', '').lower())
            tempo_total_min = duration / 60
            
            summary_table.add_row("Total de Registros", str(total_records))
            summary_table.add_row("Emails Enviados com Sucesso", f"[green]{successful}[/green]")
            summary_table.add_row("Emails com Falha", f"[red]{failed}[/red]")
            summary_table.add_row("Emails Descadastrados (Pulados)", f"[yellow]{skipped_unsubscribed}[/yellow]")
            summary_table.add_row("Emails com Bounce (Pulados)", f"[yellow]{skipped_bounced}[/yellow]")
            summary_table.add_row("Total de Tentativas", str(total_attempts))
            summary_table.add_row("Média de Tentativas por Email", f"{avg_attempts_per_email:.2f}")
            summary_table.add_row("Falhas por Erro de Conexão", str(total_connection_errors))
            summary_table.add_row("Tempo Total de Execução", f"{tempo_total_min:.2f} minutos ({duration:.1f}s)")
            
            console.print(summary_table)
            
            # Gerar relatório usando o report_generator
            report_data = self.generate_report(start_time, end_time, total_send_attempts, successful, failed)
            
            # Adicionar informações adicionais ao relatório para referência futura
            report_data["skipped_unsubscribed"] = skipped_unsubscribed
            report_data["skipped_bounced"] = skipped_bounced
            
            console.print(f"Relatório salvo em: [bold cyan]{report_data.get('report_file', 'N/A')}[/bold cyan]")
            
            return report_data
        
        except Exception as e:
            import traceback
            log.error(f"Erro no processo de envio de emails: {str(e)}")
            log.debug(traceback.format_exc())
            raise