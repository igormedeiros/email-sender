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
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn
from rich.table import Table
from rich.logging import RichHandler
from rich.text import Text
from rich.live import Live
from rich.panel import Panel
from rich.box import ROUNDED

from .config import Config
from .utils.csv_reader import CSVReader
from .email_templating import TemplateProcessor
from .reporting import ReportGenerator
from .smtp_manager import SmtpManager

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config
        self.template_processor = TemplateProcessor(config)
        self.report_generator = ReportGenerator(reports_dir=self.config.email_config.get("reports_dir", "reports"))
        self.smtp_manager = SmtpManager(config)

    def clear_sent_flags(self, csv_file: str, columns_to_clear: List[str] = ["enviado", "falhou"]) -> Dict[str, Any]:
        """
        Clears specified flag columns in a CSV file.
        Sets the values in these columns to False.
        Creates a backup of the original file.
        """
        console = Console()
        try:
            console.print(f"[bold]Limpando flags {columns_to_clear} do arquivo [cyan]{csv_file}[/cyan]...[/bold]")
            
            if not Path(csv_file).exists():
                console.print(f"[bold red]Erro: Arquivo {csv_file} não encontrado[/bold red]")
                raise FileNotFoundError(f"Arquivo {csv_file} não encontrado")

            # Create backup
            backup_file_path = self.create_backup(csv_file)
            console.print(f"Backup do arquivo criado em: [cyan]{backup_file_path}[/cyan]")

            try:
                df = pd.read_csv(csv_file, sep=None, engine='python', dtype=str) # Read all as string to preserve data
            except Exception as e:
                console.print(f"[bold red]Erro ao ler o arquivo CSV: {str(e)}[/bold red]")
                raise ValueError(f"Erro ao ler o arquivo CSV {csv_file}: {str(e)}")

            original_row_count = len(df)
            cleared_flags_count = {}

            # Create a table to show changes
            table = Table(title="Limpeza de Flags", box=ROUNDED)
            table.add_column("Coluna", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Qtd. Limpa", style="yellow")

            for col in columns_to_clear:
                if col in df.columns:
                    cleared_flags_count[col] = df[col].astype(bool).sum()
                    df[col] = ""
                    table.add_row(col, "✓ Limpa", str(cleared_flags_count[col]))
                else:
                    cleared_flags_count[col] = 0
                    table.add_row(col, "⚠️ Não encontrada", "0")
            
            df.to_csv(csv_file, index=False)
            
            console.print(table)
            console.print(f"[green]✓ Flags limpas com sucesso em {csv_file}.[/green]")

            return {
                "status": "success",
                "csv_file": csv_file,
                "backup_file": backup_file_path,
                "original_row_count": original_row_count,
                "cleared_flags_count": cleared_flags_count
            }

        except Exception as e:
            console.print(f"[bold red]Erro ao limpar flags no arquivo {csv_file}: {str(e)}[/bold red]")
            console.print_exception()
            raise

    def load_unsubscribed_emails(self, unsubscribe_file: Optional[str] = None) -> set:
        """
        Carrega emails da lista de descadastro.
        Retorna um set de emails em lower case.
        """
        console = Console()
        unsubscribe_path = Path(unsubscribe_file or self.config.email_config.get("unsubscribe_file", "data/descadastros.csv"))
        unsubscribed_emails = set()
        
        if unsubscribe_path.exists():
            try:
                console.print(f"Carregando lista de descadastro de: [cyan]{unsubscribe_path}[/cyan]")
                df_unsubscribed = pd.read_csv(unsubscribe_path, dtype=str)
                if "email" in df_unsubscribed.columns:
                    # Usamos dtype=str para garantir que todos os dados são strings
                    # Mas precisamos limpar e remover NaNs explicitamente
                    emails = df_unsubscribed["email"].fillna("").astype(str)
                    # Remove strings vazias e "nan" e converte para lowercase
                    valid_emails = [email.lower().strip() for email in emails 
                                  if email and email.strip() and email.strip().lower() != 'nan']
                    unsubscribed_emails = set(valid_emails)
                    console.print(f"[green]✓[/green] Carregados {len(unsubscribed_emails)} emails da lista de descadastro")
                else:
                    console.print(f"[yellow]⚠️ Coluna 'email' não encontrada em {unsubscribe_path}.[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Erro ao carregar arquivo de descadastro {unsubscribe_path}: {str(e)}[/red]")
        else:
            console.print(f"[yellow]⚠️ Arquivo de descadastro {unsubscribe_path} não encontrado.[/yellow]")
            
        return unsubscribed_emails

    def load_bounced_emails(self, bounces_file: Optional[str] = None) -> set:
        """
        Carrega emails da lista de bounces ativos.
        Retorna um set de emails em lower case.
        """
        console = Console()
        bounces_path = Path(bounces_file or self.config.email_config.get("bounces_file", "data/bounces.csv"))
        bounced_emails = set()
        
        if bounces_path.exists():
            try:
                console.print(f"Carregando lista de bounces de: [cyan]{bounces_path}[/cyan]")
                df_bounces = pd.read_csv(bounces_path, dtype=str)
                if "email" in df_bounces.columns:
                    # Usamos dtype=str para garantir que todos os dados são strings
                    # Mas precisamos limpar e remover NaNs explicitamente
                    emails = df_bounces["email"].fillna("").astype(str)
                    # Remove strings vazias e "nan" e converte para lowercase
                    valid_emails = [email.lower().strip() for email in emails 
                                  if email and email.strip() and email.strip().lower() != 'nan']
                    bounced_emails = set(valid_emails)
                    console.print(f"[green]✓[/green] Carregados {len(bounced_emails)} emails da lista de bounces")
                else:
                    console.print(f"[yellow]⚠️ Coluna 'email' não encontrada em {bounces_path}.[/yellow]")
            except Exception as e:
                console.print(f"[red]❌ Erro ao carregar arquivo de bounces {bounces_path}: {str(e)}[/red]")
        else:
            console.print(f"[yellow]⚠️ Arquivo de bounces {bounces_path} não encontrado.[/yellow]")
            
        return bounced_emails

    def sync_unsubscribed_emails(self, csv_path: str, unsubscribe_file: str) -> int:
        console = Console()
        unsubscribed = set()
        
        console.print(f"[bold blue]Sincronizando lista de descadastros...[/bold blue]")
        
        try:
            if not Path(unsubscribe_file).exists():
                console.print(f"[yellow]⚠️ Arquivo de descadastros não encontrado: {unsubscribe_file}[/yellow]")
                console.print("Nenhuma flag 'descadastro' será definida como 'S'. As existentes podem ser limpas.")
                # Prossegue com 'unsubscribed' vazio, o que limpará as flags no arquivo principal.
            else:
                # Tenta ler o arquivo de descadastros, tratando possíveis problemas
                try:
                    console.print(f"Lendo lista de descadastros de: [cyan]{unsubscribe_file}[/cyan]")
                    df_unsubscribed = pd.read_csv(unsubscribe_file, sep=None, engine='python', on_bad_lines='warn', low_memory=False)
                    if 'email' in df_unsubscribed.columns:
                        unsubscribed = set(df_unsubscribed['email'].astype(str).str.lower().str.strip().dropna())
                    elif not df_unsubscribed.empty: # Se não tem coluna 'email', mas tem dados
                        console.print("[yellow]⚠️ Coluna 'email' não encontrada, usando primeira coluna[/yellow]")
                        unsubscribed = set(df_unsubscribed.iloc[:, 0].astype(str).str.lower().str.strip().dropna())
                except pd.errors.EmptyDataError:
                    console.print(f"[yellow]⚠️ Arquivo de descadastros {unsubscribe_file} está vazio.[/yellow]")
                except Exception as e_csv:
                    console.print(f"[yellow]⚠️ Erro ao ler {unsubscribe_file} como CSV: {str(e_csv)}. Tentando ler como texto.[/yellow]")
                    try:
                        with open(unsubscribe_file, 'r', encoding='utf-8') as file:
                            for line in file:
                                email = line.strip().lower()
                                # Checagem básica para ser um email e não um cabeçalho
                                if email and '@' in email and not email.lower().startswith('email'):
                                    unsubscribed.add(email)
                    except Exception as e_txt:
                        console.print(f"[red]❌ Falha ao ler {unsubscribe_file} como CSV e como texto: {str(e_txt)}.[/red]")
            
            if not unsubscribed:
                console.print(f"[yellow]⚠️ Nenhum email válido encontrado na lista de descadastros.[/yellow]")
                console.print(f"Flags 'descadastro' existentes no arquivo principal serão limpas.")
            else:
                console.print(f"[green]✓[/green] Encontrados {len(unsubscribed)} emails na lista de descadastros.")

        except Exception as e_outer: # Captura exceções na leitura do unsubscribe_file
            console.print(f"[red]❌ Erro crítico ao processar o arquivo de descadastros: {str(e_outer)}[/red]")
            return 0

        try:
            if not Path(csv_path).exists():
                console.print(f"[red]❌ Arquivo CSV principal não encontrado: {csv_path}[/red]")
                return 0

            console.print(f"Lendo arquivo CSV principal: [cyan]{csv_path}[/cyan]")
            df = pd.read_csv(csv_path, sep=None, engine='python', on_bad_lines='warn')

            if 'email' not in df.columns:
                console.print(f"[red]❌ Coluna 'email' não encontrada no arquivo principal.[/red]")
                return 0

            if df.empty:
                console.print(f"[yellow]⚠️ Arquivo CSV principal está vazio. Nada a sincronizar.[/yellow]")
                df.to_csv(csv_path, index=False)
                return 0

            # Garante que a coluna 'descadastro' exista.
            if 'descadastro' not in df.columns:
                console.print("Criando coluna 'descadastro' que não existia no CSV.")
                df['descadastro'] = ''
            else:
                # Converte para string e preenche NaNs para evitar erros com o .map e garantir consistência.
                df['descadastro'] = df['descadastro'].astype(str).fillna('')

            # Atualiza a flag 'descadastro' APENAS para emails existentes no DataFrame principal (df).
            # Não adiciona novas linhas.
            # Se o email do df está em 'unsubscribed', marca 'S'.
            # Se o email do df NÃO está em 'unsubscribed', marca '' (limpa a flag).
            df['descadastro'] = df['email'].astype(str).str.lower().str.strip().isin(unsubscribed).map({True: 'S', False: ''})

            update_count = (df['descadastro'] == 'S').sum()

            # Salva o arquivo com as alterações
            console.print(f"Salvando alterações em: [cyan]{csv_path}[/cyan]")
            df.to_csv(csv_path, index=False)

            console.print(f"[green]✓ Sincronização concluída![/green] {update_count} emails estão marcados como descadastro.")
            
            # Criar uma tabela simples para mostrar o resultado
            result_table = Table(title="Resumo da Sincronização", box=ROUNDED)
            result_table.add_column("Métrica", style="dim")
            result_table.add_column("Valor", style="bold")
            
            result_table.add_row("Total de emails no CSV", str(len(df)))
            result_table.add_row("Emails na lista de descadastros", str(len(unsubscribed)))
            result_table.add_row("Emails marcados como descadastro", str(update_count))
            
            console.print(result_table)
            
            return update_count

        except pd.errors.EmptyDataError:
            console.print(f"[yellow]⚠️ Arquivo CSV principal está vazio após tentativa de leitura.[/yellow]")
            try:
                # Tenta salvar um DataFrame vazio com colunas
                pd.DataFrame(columns=['email', 'descadastro']).to_csv(csv_path, index=False)
                console.print(f"Arquivo vazio salvo com as colunas corretas.")
            except Exception as e_save_empty:
                console.print(f"[red]❌ Erro ao tentar salvar arquivo CSV vazio: {str(e_save_empty)}[/red]")
            return 0
        except Exception as e:
            console.print(f"[red]❌ Erro crítico ao processar o arquivo CSV principal: {str(e)}[/red]")
            console.print_exception()
            return 0 # Indica que 0 emails foram atualizados devido ao erro.

    def sync_bounced_emails(self, csv_file: str, bounces_file: Optional[str] = None) -> int:
        """
        Marca emails com bounce no arquivo CSV principal.
        Adiciona/atualiza a coluna 'bounced' para True para emails encontrados na lista de bounces.
        Retorna o número de emails atualizados.
        """
        console = Console()
        console.rule("[bold blue]Sincronizando Bounces[/bold blue]")
        console.print(f"Iniciando sincronização de bounces para [cyan]{csv_file}[/cyan] usando [cyan]{bounces_file or 'config default'}[/cyan]")
        
        bounced_set = self.load_bounced_emails(bounces_file)
        if not bounced_set:
            console.print("[yellow]⚠️ Nenhum email na lista de bounces. Nenhuma sincronização necessária.[/yellow]")
            return 0

        try:
            console.print(f"Lendo arquivo CSV principal: [cyan]{csv_file}[/cyan]")
            df = pd.read_csv(csv_file, dtype=str)
            
            if "email" not in df.columns:
                console.print(f"[red]❌ Coluna 'email' não encontrada no arquivo CSV principal {csv_file}[/red]")
                raise ValueError(f"Coluna 'email' não encontrada no arquivo CSV principal {csv_file}")

            original_bounced_count = 0
            if "bounced" in df.columns:
                df["bounced"] = df["bounced"].fillna("").astype(str).str.lower().map({'true': True, '1': True, 'yes': True}).fillna(False)
                original_bounced_count = df["bounced"].sum()
                console.print(f"Coluna 'bounced' existente com {original_bounced_count} emails marcados")
            else:
                console.print("Coluna 'bounced' não existente, criando...")
                df["bounced"] = False

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
            ) as progress:
                task = progress.add_task("[green]Verificando emails...", total=len(df))
                
                updated_count = 0
                for index, row in df.iterrows():
                    progress.update(task, advance=1)
                    
                    if pd.notna(row["email"]):
                        email_lower = str(row["email"]).lower().strip()
                        if email_lower in bounced_set:
                            if not df.at[index, "bounced"]:
                                df.at[index, "bounced"] = True
                                updated_count += 1
            
            if updated_count > 0:
                console.print(f"Salvando alterações em [cyan]{csv_file}[/cyan]...")
                df.to_csv(csv_file, index=False)
                console.print(f"[green]✓[/green] {updated_count} emails marcados como bounced em {csv_file}.")
            else:
                console.print(f"[yellow]⚠️ Nenhum email novo precisou ser marcado como bounced em {csv_file}.[/yellow]")

            current_bounced_count = df["bounced"].sum()
            
            # Criar uma tabela para mostrar o resultado
            result_table = Table(title="Resumo de Bounces", box=ROUNDED)
            result_table.add_column("Métrica", style="dim")
            result_table.add_column("Valor", style="bold")
            
            result_table.add_row("Total de emails no CSV", str(len(df)))
            result_table.add_row("Emails na lista de bounces", str(len(bounced_set)))
            result_table.add_row("Bounces antes da sincronização", str(original_bounced_count))
            result_table.add_row("Bounces depois da sincronização", str(current_bounced_count))
            result_table.add_row("Novos emails marcados", str(updated_count))
            
            console.print(result_table)
            
            return updated_count

        except FileNotFoundError:
            log.error(f"Arquivo CSV principal {csv_file} não encontrado para sincronização de bounces.")
            raise
        except Exception as e:
            log.error(f"Erro ao sincronizar emails com bounce em {csv_file}: {e}")
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
            # Log a more detailed traceback for AttributeError
            if isinstance(e, AttributeError):
                log.exception("AttributeError details:")
            raise

    def generate_report(self, start_time: float, end_time: float, total_processed_from_csv: int, successful_sends: int, failed_sends: int, skipped_unsubscribed: int, skipped_bounced: int, skipped_invalid_email: int) -> Dict[str, Any]:
        """
        Gera um relatório do processo de envio de emails usando ReportGenerator.
        """
        try:
            # Adapt to use the new parameters for ReportGenerator
            return self.report_generator.generate_report(
                start_time=start_time,
                end_time=end_time,
                total_processed_from_csv=total_processed_from_csv,
                successful_sends=successful_sends,
                failed_sends=failed_sends,
                skipped_unsubscribed=skipped_unsubscribed,
                skipped_bounced=skipped_bounced,
                skipped_invalid_email=skipped_invalid_email
            )
        except Exception as e:
            # Assuming log is already configured with Rich for this top-level call in EmailService
            log.error(f"Erro ao gerar relatório via ReportGenerator: {str(e)}")
            raise

    def remove_duplicates(self, csv_file: str, column: str = "email", keep: str = "first", output_file: Optional[str] = None) -> Dict[str, Any]:
        console = Console()
        try:
            console.rule("[bold blue]Removendo Duplicados[/bold blue]")
            console.print(f"Removendo duplicados do arquivo [cyan]{csv_file}[/cyan] baseado na coluna '[bold]{column}[/bold]'...")
            
            if not Path(csv_file).exists():
                console.print(f"[bold red]❌ Erro: Arquivo {csv_file} não encontrado[/bold red]")
                raise FileNotFoundError(f"Arquivo {csv_file} não encontrado")
            
            try:
                with console.status(f"Lendo arquivo CSV [cyan]{csv_file}[/cyan]..."):
                    df = pd.read_csv(csv_file, sep=None, engine='python')
            except Exception as e:
                console.print(f"[bold red]❌ Erro ao ler o arquivo CSV: {str(e)}[/bold red]")
                raise ValueError(f"Erro ao ler o arquivo CSV: {str(e)}")
            
            if column not in df.columns:
                console.print(f"[bold red]❌ Coluna '{column}' não encontrada no arquivo CSV[/bold red]")
                raise ValueError(f"Coluna '{column}' não encontrada no arquivo CSV")
            
            total_antes = len(df)
            with console.status(f"Processando {total_antes} registros..."):
                df_without_duplicates = df.drop_duplicates(subset=[column], keep=keep)
            total_depois = len(df_without_duplicates)
            duplicados_removidos = total_antes - total_depois
            
            if not output_file:
                backup_file = self.create_backup(csv_file)
                console.print(f"Backup criado em: [cyan]{backup_file}[/cyan]")
                output_path = csv_file
            else:
                output_path = output_file
                backup_file = None
                console.print(f"Salvando em arquivo de saída: [cyan]{output_path}[/cyan]")
            
            with console.status(f"Salvando {total_depois} registros no arquivo..."):
                df_without_duplicates.to_csv(output_path, index=False)
            
            # Criar uma tabela para o resultado
            table = Table(title="Resultado de Remoção de Duplicados", box=ROUNDED)
            table.add_column("Métrica", style="cyan")
            table.add_column("Valor", style="bold")
            
            table.add_row("Registros Originais", str(total_antes))
            table.add_row("Registros Após Remoção", str(total_depois))
            table.add_row("Duplicados Removidos", f"[bold {'green' if duplicados_removidos > 0 else 'yellow'}]{duplicados_removidos}[/bold]")
            table.add_row("Arquivo de Saída", output_path)
            if backup_file:
                table.add_row("Backup", str(backup_file))
            
            console.print(table)
            
            result = {
                "status": "success",
                "total_antes": total_antes,
                "total_depois": total_depois,
                "duplicados_removidos": duplicados_removidos,
                "output_file": str(output_path),
                "backup_file": str(backup_file) if backup_file else None
            }
            
            if duplicados_removidos > 0:
                console.print(f"[green]✓[/green] {duplicados_removidos} duplicados removidos com sucesso!")
            else:
                console.print(f"[yellow]⚠️[/yellow] Nenhum duplicado encontrado para a coluna '{column}'.")
                
            return result
                
        except Exception as e:
            console.print(f"[bold red]❌ Erro ao remover duplicados: {str(e)}[/bold red]")
            console.print_exception()
            raise

    def send_test_email(self, recipient: str) -> bool:
        """
        Envia um email de teste para verificar a conexão com o servidor SMTP.
        
        Args:
            recipient: Endereço de email do destinatário de teste
            
        Returns:
            True se o email foi enviado com sucesso, False caso contrário
        """
        console = Console()
        console.rule("[bold blue]Envio de Email de Teste[/bold blue]")
        
        # Validar o email antes de tentar enviar
        if not recipient or not isinstance(recipient, str):
            console.print(f"[bold red]❌ Email inválido: {recipient} (tipo: {type(recipient).__name__})[/bold red]")
            return False
            
        # Verificar formato básico de email usando regex
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(recipient):
            console.print(f"[bold yellow]⚠️ Formato de email potencialmente inválido: {recipient}[/bold yellow]")
            # Continua mesmo assim, pois podemos ter formatos especiais em ambientes de teste
        
        try:
            email_subject = self.config.content_config.get("email", {}).get("subject", "SMTP Test Email")
            message_content = "This is a test email from the email-sender application."
            
            console.print(f"Enviando email de teste para: [bold cyan]{recipient}[/bold cyan]")
            console.print(f"Assunto: [magenta]{email_subject}[/magenta]")
            
            with console.status("[bold green]Enviando email de teste...[/bold green]") as status:
                self.smtp_manager.send_email(
                    to_email=recipient,
                    subject=email_subject,
                    content=message_content,
                    is_html=False
                )
            
            console.print(f"[bold green]✓ Email de teste enviado com sucesso para {recipient}[/bold green]")
            
            # Criar uma tabela para mostrar detalhes
            table = Table(title="Detalhes do Email de Teste", box=ROUNDED)
            table.add_column("Campo", style="cyan")
            table.add_column("Valor", style="green")
            
            table.add_row("Destinatário", recipient)
            table.add_row("Assunto", email_subject)
            table.add_row("Conteúdo HTML", "Não")
            table.add_row("Status", "[bold green]Enviado com Sucesso[/bold green]")
            
            console.print(table)
            
            return True
        except Exception as e:
            console.print(f"[bold red]❌ Erro ao enviar email de teste para {recipient}:[/bold red]")
            console.print(f"[red]{str(e)}[/red]")
            console.print_exception()
            
            # Ainda criar uma tabela para mostrar detalhes, mesmo com erro
            table = Table(title="Detalhes do Email de Teste", box=ROUNDED)
            table.add_column("Campo", style="cyan")
            table.add_column("Valor", style="red")
            
            table.add_row("Destinatário", recipient)
            table.add_row("Assunto", email_subject if 'email_subject' in locals() else "Não definido")
            table.add_row("Status", "[bold red]Falha no Envio[/bold red]")
            table.add_row("Erro", str(e))
            
            console.print(table)
            
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
        csv_reader_instance = None  # Initialize to None
        # Initialize console for rich output
        console = Console()
        rich_log_handler = RichHandler(console=console, show_time=False, show_path=False, rich_tracebacks=True, tracebacks_show_locals=True)
        
        # Remove any existing RichHandler to avoid duplicates
        for handler in log.handlers[:]:
            if isinstance(handler, RichHandler):
                log.removeHandler(handler)
                
        log.addHandler(rich_log_handler)
        log.propagate = False # Prevent duplication if root logger also has handlers

        try:
            console.rule("[bold blue]Iniciando Processo de Envio de Emails[/bold blue]", style="blue")
            start_time = time.time()
            successful = 0
            failed = 0
            skipped_unsubscribed = 0
            skipped_bounced = 0
            skipped_invalid_email = 0
            total_records_in_csv = 0


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

            # Configuration for sending process
            pause_duration_after_attempts = self.config.email_config.get("batch_delay", 60)
            retry_attempts_config = self.config.email_config.get("retry_attempts", 3)
            retry_delay_config = self.config.email_config.get("retry_delay", 60)
            send_timeout = self.config.email_config.get("send_timeout", 10) # seconds

            # Load unsubscribed and bounced emails
            unsubscribed = self.load_unsubscribed_emails() # Uses its own logging
            active_bounced_set = self.load_bounced_emails(bounces_file_path) # Uses its own logging

            csv_reader_instance = CSVReader(actual_csv_file, self.config.email_config.get("batch_size", 10))
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
                    console.print(f"[bold red]Erro: Arquivo de template não encontrado: {template} (nem em templates/{template_path_obj.name})[/bold red]")
                    raise FileNotFoundError(f"Template file not found: {template}")
            else:
                template_path_obj = template_path_obj.resolve()
                console.print(f"Template encontrado em: [green]{template_path_obj}[/green]")

            total_records_in_csv = csv_reader_instance.total_records
            if total_records_in_csv == 0:
                console.print(f"[bold yellow]Atenção: Nenhum registro encontrado no arquivo CSV: {actual_csv_file}. Nenhum email para enviar.[/bold yellow]")
                if csv_reader_instance:
                    csv_reader_instance.cleanup()
                return {
                    "report_file": "", "duration": 0.0, "avg_time_per_email": 0.0,
                    "total_processed_from_csv": 0,
                    "total_send_attempts": 0, "successful": 0, "failed": failed, # failed can be > 0 if all were invalid
                    "skipped_unsubscribed": 0, "skipped_bounced": 0, "skipped_invalid_email": 0,
                    "report": "Nenhum email encontrado para enviar no arquivo CSV fornecido.",
                    "status": "no_emails_in_csv"
                }
            
            console.print(f"Total de registros no CSV para processar: [bold]{total_records_in_csv}[/bold]")
            
            # Initialize Rich Progress Bar
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False # Keep progress bar after completion
            ) as progress:
                
                task_id = progress.add_task("[green]Enviando emails...", total=total_records_in_csv)
                processed_recipients_count = 0

                # Inner try for the loop, handling KeyboardInterrupt and SIGALRM
                try:
                    class TimeoutException(Exception):
                        pass
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutException
                    
                    signal.signal(signal.SIGALRM, timeout_handler)
                    
                    total_batches = 0
                    if csv_reader_instance.batch_size > 0:
                        total_batches = math.ceil(total_records_in_csv / csv_reader_instance.batch_size)
                    
                    for batch_idx, batch_recipients in enumerate(csv_reader_instance.get_batches()):
                        console.print(f"Processando lote {batch_idx + 1}/{int(total_batches)} (Tamanho: {len(batch_recipients)})...")
                        
                        for recipient_data in batch_recipients:
                            processed_recipients_count +=1
                            progress.update(task_id, advance=1, description=f"[green]Processando {processed_recipients_count}/{total_records_in_csv}")

                            email_from_csv = recipient_data.get('email')

                            # --- Start Validation and Normalization Block ---
                            if pd.isna(email_from_csv):
                                console.print(f"[yellow]Aviso: Email ausente (NaN) no CSV. Pulando.[/yellow]")
                                failed += 1
                                skipped_invalid_email += 1
                                # Cannot mark as failed in CSVReader if email_from_csv is NaN
                                continue
                            
                            if not isinstance(email_from_csv, str):
                                console.print(f"[yellow]Aviso: Email não é uma string ('{email_from_csv}', tipo: {type(email_from_csv).__name__}). Pulando.[/yellow]")
                                failed += 1
                                skipped_invalid_email += 1
                                # Cannot mark as failed in CSVReader if email_from_csv is not a string
                                continue

                            validated_email = email_from_csv.strip().lower()

                            if not validated_email or '@' not in validated_email or validated_email == 'nan':
                                console.print(f"[yellow]Aviso: Formato de email inválido: '{email_from_csv}'. Pulando e marcando como falha.[/yellow]")
                                failed += 1
                                skipped_invalid_email += 1
                                try:
                                    csv_reader_instance.mark_as_failed(validated_email, "Formato de email inválido")
                                except Exception as e:
                                    console.print(f"[red]Erro ao marcar email como falha: {str(e)}[/red]")
                                continue
                            # --- End Validation and Normalization Block ---

                            # Check if bounced (using validated_email)
                            if validated_email in active_bounced_set:
                                console.print(f"[yellow]Pulando email com bounce ativo: {validated_email}[/yellow]")
                                skipped_bounced += 1
                                # Optionally mark in CSV if needed, e.g., csv_reader_instance.mark_as_bounced(validated_email)
                                continue 
                            
                            # Check if unsubscribed (using validated_email)
                            if validated_email in unsubscribed:
                                console.print(f"[yellow]Pulando email descadastrado: {validated_email}[/yellow]")
                                skipped_unsubscribed += 1
                                # csv_reader_instance.mark_as_unsubscribed(validated_email) # Assuming CSVReader has this
                                continue
                            
                            # If we reach here, the email is valid and not in bounce/unsubscribe lists.

                            attempts = 0
                            email_sent_successfully = False
                            current_send_error = "N/A"

                            while attempts < retry_attempts_config:
                                try:
                                    if attempts == 0:
                                        console.print(f"Enviando para: [bold]📧 {validated_email}[/bold]")
                                    else:
                                        console.print(f"Tentativa {attempts+1}/{retry_attempts_config} para: [bold]📧 {validated_email}[/bold]")
                                        
                                    signal.alarm(send_timeout) # Set timeout for this send attempt
                                    
                                    html_content = self.process_email_template(str(template_path_obj), recipient_data, email_subject)
                                    
                                    self.send_batch([recipient_data], html_content, email_subject, is_html=True) # send_batch expects a list
                                    
                                    signal.alarm(0) # Reset the alarm
                                    console.print(f"[green]✅ Email enviado para {validated_email}[/green]")
                                    successful += 1
                                    csv_reader_instance.mark_as_sent(validated_email)
                                    email_sent_successfully = True
                                    break # Exit retry loop on success

                                except TimeoutException:
                                    signal.alarm(0) # Reset alarm
                                    current_send_error = f"Timeout ({send_timeout}s) ao enviar email"
                                    console.print(f"[red]❌ Timeout ao enviar para {validated_email} (Tentativa {attempts + 1})[/red]")
                                    attempts += 1
                                    if attempts < retry_attempts_config and retry_delay_config > 0:
                                        console.print(f"[yellow]Aguardando {retry_delay_config}s antes da próxima tentativa...[/yellow]")
                                        time.sleep(retry_delay_config)
                                
                                except Exception as e:
                                    signal.alarm(0) # Reset alarm
                                    current_send_error = str(e)
                                    console.print(f"[red]❌ Erro ao enviar para {validated_email} (Tentativa {attempts + 1}): {str(e)}[/red]")
                                    attempts += 1
                                    if attempts < retry_attempts_config and retry_delay_config > 0:
                                        console.print(f"[yellow]Aguardando {retry_delay_config}s antes da próxima tentativa...[/yellow]")
                                        time.sleep(retry_delay_config)
                            
                            if not email_sent_successfully:
                                failed += 1
                                try:
                                    csv_reader_instance.mark_as_failed(validated_email, f"Falha após {retry_attempts_config} tentativas. Último erro: {current_send_error}")
                                except Exception as mark_err:
                                    console.print(f"[red]Erro ao marcar falha no CSV: {str(mark_err)}[/red]")
                                console.print(f"[red]Falha definitiva ao enviar para {validated_email} após {retry_attempts_config} tentativas.[/red]")
                        
                        # Pause between batches if configured
                        if batch_idx < total_batches - 1 and pause_duration_after_attempts > 0: # Don't pause after the last batch
                            console.print(f"[blue]Pausa de {pause_duration_after_attempts} segundos entre lotes...[/blue]")
                            time.sleep(pause_duration_after_attempts)
                    
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Processo interrompido pelo usuário.[/bold yellow]")
                    console.print("Salvando progresso...", style="yellow")
                    # CSVReader handles saving progress in its __del__ or if explicitly called
                finally:
                    signal.alarm(0) # Disable any pending alarm
                    progress.update(task_id, description="[blue]Processamento de emails concluído.[/blue]")
            
            end_time = time.time()
            
            # Ensure log handler is removed to prevent interference with other parts of the app or tests
            log.removeHandler(rich_log_handler)
            log.propagate = True


            console.rule("[bold blue]Relatório de Envio[/bold blue]", style="blue")
            report_data = self.generate_report(
                start_time, end_time, 
                total_processed_from_csv=total_records_in_csv, # Total records read from CSV
                successful_sends=successful, 
                failed_sends=failed,
                skipped_unsubscribed=skipped_unsubscribed,
                skipped_bounced=skipped_bounced,
                skipped_invalid_email=skipped_invalid_email
            )
            
            # Display summary with Rich
            summary_table = Table(title="Resumo do Envio de Emails", show_header=True, header_style="bold magenta", box=ROUNDED)
            summary_table.add_column("Métrica", style="dim", width=30)
            summary_table.add_column("Valor")
            
            summary_table.add_row("Arquivo CSV Processado", actual_csv_file)
            summary_table.add_row("Total de Registros no CSV", str(total_records_in_csv))
            summary_table.add_row("Emails Válidos para Tentativa", str(total_records_in_csv - skipped_unsubscribed - skipped_bounced - skipped_invalid_email))
            summary_table.add_row("[green]Enviados com Sucesso[/green]", f"[bold green]{successful}[/bold green]")
            summary_table.add_row("[red]Falharam no Envio[/red]", f"[bold red]{failed}[/bold red]")
            summary_table.add_row("[yellow]Pulados (Descadastrados)[/yellow]", str(skipped_unsubscribed))
            summary_table.add_row("[yellow]Pulados (Bounces Ativos)[/yellow]", str(skipped_bounced))
            summary_table.add_row("[yellow]Pulados (Email Inválido/Ausente)[/yellow]", str(skipped_invalid_email))
            summary_table.add_row("Duração Total", report_data.get("duration_formatted", f"{end_time - start_time:.2f}s"))
            summary_table.add_row("Relatório Salvo em", report_data.get("report_file", "N/A"))
            
            console.print(summary_table)
            
            if csv_reader_instance: 
                csv_reader_instance.cleanup() # Remove .bak file on successful completion
            
            return report_data
        
        except FileNotFoundError as fnf_error:
            console.print(f"[bold red]Erro de arquivo não encontrado: {str(fnf_error)}[/bold red]")
            # Ensure log handler is removed
            if 'rich_log_handler' in locals() and rich_log_handler in log.handlers:
                log.removeHandler(rich_log_handler)
                log.propagate = True
            # No cleanup of CSVReader if it wasn't initialized or if the error is critical before its use.
            # If CSVReader was initialized, its .bak should be preserved.
            raise # Re-raise to be caught by CLI
        except ValueError as val_error:
            console.print(f"[bold red]Erro de valor: {str(val_error)}[/bold red]")
            if 'rich_log_handler' in locals() and rich_log_handler in log.handlers:
                log.removeHandler(rich_log_handler)
                log.propagate = True
            raise
        except Exception as e:
            console.print_exception(show_locals=True)
            console.print(f"[bold red]Erro CRÍTICO no processo de envio de emails: {str(e)}[/bold red]")
            if 'rich_log_handler' in locals() and rich_log_handler in log.handlers:
                log.removeHandler(rich_log_handler)
                log.propagate = True
            # CSVReader's .bak should be preserved if it was initialized.
            raise