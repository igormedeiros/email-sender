import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from datetime import datetime
import signal
import math

from .config import Config
from .email_templating import TemplateProcessor
from .reporting import ReportGenerator
from .smtp_manager import SmtpManager
from .db import Database

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config
        # Passa apenas content_config para o TemplateProcessor para garantir compatibilidade
        self.template_processor = TemplateProcessor(config.content_config if hasattr(config, 'content_config') else config)
        self.report_generator = ReportGenerator(reports_dir=self.config.email_config.get("reports_dir", "reports"))
        self.smtp_manager = SmtpManager(config)

    def send_email_to_test_recipient(self, template: str) -> Dict[str, Any]:
        """Envio simplificado para AMBIENTE de teste: pega 1 destinatário de teste via SQL e envia.

        Usa as queries em sql/ para criar campanha, selecionar destinatário (modo teste) e registrar log 'sent'.
        """
        from rich.console import Console
        console = Console()

        email_subject = self.config.content_config.get("email", {}).get("subject", "Sem assunto")
        # Resolver template path
        if not template.endswith('.html'):
            template += '.html'
        template_path_obj = Path(template)
        if not template_path_obj.exists():
            root_template_path = Path("templates") / template_path_obj.name
            if root_template_path.exists():
                template_path_obj = root_template_path
            else:
                raise FileNotFoundError(f"Template file not found: {template}")

        start_time = time.time()
        successful = 0
        failed = 0
        total_send_attempts = 0

        with Database(self.config) as db:
            # Dados do evento devem vir do YAML (config/email.yaml -> seção 'evento')
            evento_cfg = (self.config.content_config or {}).get("evento", {}) if hasattr(self.config, 'content_config') else {}
            state = str(evento_cfg.get("uf") or evento_cfg.get("state") or "")
            now = datetime.now()
            month = f"{now.month:02d}"
            year = f"{now.year}"
            # sympla_id pode ser alfanumérico; buscar id interno no Postgres
            sympla_code = (evento_cfg.get("sympla_id") or "").strip()
            event_id = None
            try:
                if sympla_code:
                    found = db.fetch_one("sql/events/select_event_internal_id_by_sympla_id.sql", (sympla_code,))
                    if found and "id" in found:
                        event_id = int(found["id"]) if found["id"] is not None else None
            except Exception:
                event_id = None

            created = db.fetch_one(
                "sql/messages/create_message.sql",
                (email_subject, state, month, year, event_id),
            )
            if not created or "id" not in created:
                raise RuntimeError("Falha ao criar campanha em tbl_messages")
            message_id = created["id"]

            recipients = db.fetch_all(
                "sql/contacts/select_recipients_for_message.sql",
                (True, message_id),  # True => modo teste
            )
            if not recipients:
                # marca como processada e encerra
                db.execute("sql/messages/mark_message_processed.sql", (message_id,))
                return {"status": "no_emails", "total_records": 0, "message_id": message_id}

            recipient = recipients[0]
            recipient_email = str(recipient.get("email", "")).strip()
            if not recipient_email:
                db.execute("sql/messages/mark_message_processed.sql", (message_id,))
                return {"status": "no_emails", "total_records": 0, "message_id": message_id}

            total_send_attempts = 1
            try:
                console.print(f"Tentando enviar para: [bold cyan]{recipient_email}[/bold cyan]")
                html_content = self.process_email_template(str(template_path_obj), recipient, email_subject)
                self.smtp_manager.send_email(
                    to_email=recipient_email,
                    subject=email_subject,
                    content=html_content,
                    is_html=True,
                )
                console.print(f"[green]✅ Email enviado com sucesso para {recipient_email}[/green]")
                successful = 1
                # log 'sent'
                db.execute(
                    "sql/messages/insert_message_sent_log.sql",
                    (recipient.get("id"), message_id, 'OK', ''),
                )
            except Exception as e:
                console.print(f"[red]❌ Falha ao enviar para {recipient_email}: {str(e)}[/red]")
                failed = 1
                try:
                    db.execute(
                        "sql/messages/insert_message_sent_log.sql",
                        (recipient.get("id"), message_id, 'ERROR', str(e)[:200]),
                    )
                except Exception:
                    pass
            finally:
                # fechar campanha
                try:
                    db.execute("sql/messages/mark_message_processed.sql", (message_id,))
                except Exception:
                    pass

        end_time = time.time()
        report = self.generate_report(start_time, end_time, total_send_attempts, successful, failed)
        report["test_recipient"] = recipient_email
        return report

    # Legacy CSV-related methods removed as part of code cleanup.

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

    # Legacy helpers removed: remove_duplicates, create_backup, send_test_email.

    def process_email_sending(self, csv_file: str | None = None, template: str = "", skip_unsubscribed_sync: bool = True, is_test_mode: bool = True, bounces_file_path: str | None = None) -> Dict[str, Any]:
        """Processa envio em lote usando Postgres via SQL (fluxo simplificado)."""
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
            console.rule("[bold blue]Iniciando Processo de Envio de Emails (Postgres)[bold blue]", style="blue")
            
            start_time = time.time()
            successful = 0
            failed = 0
            total_send_attempts = 0
            
            pause_duration_after_attempts = self.config.email_config.get("batch_delay", 60)
            retry_attempts_config = self.config.email_config.get("retry_attempts", 3)
            retry_delay_config = self.config.email_config.get("retry_delay", 60)
            send_timeout = self.config.email_config.get("send_timeout", 10)
            max_retry_minutes = self.config.email_config.get("max_retry_minutes", 5)
            
            # Exibir configurações de envio
            console.print("\n[bold]Configurações de envio:[/bold]")
            console.print(f"Tempo máximo de tentativas: [cyan]{max_retry_minutes} minutos[/cyan]")
            console.print(f"Número máximo de tentativas: [cyan]{retry_attempts_config}[/cyan]")
            console.print(f"Tempo entre tentativas: [cyan]{retry_delay_config}s[/cyan]")
            console.print(f"Timeout por tentativa: [cyan]{send_timeout}s[/cyan]")
            console.print(f"Pausa entre lotes: [cyan]{pause_duration_after_attempts}s[/cyan]")
            
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
            
            # Conectar ao Postgres e buscar destinatários (fluxo simplificado)
            with Database(self.config) as db:
                # Estado: último contact_id enviado com sucesso
                STATE_KEY = "last_success_contact_id"
                last_sent_row = db.fetch_one("sql/runtime/get_send_state.sql", (STATE_KEY,)) or {}
                try:
                    last_id = int(str((last_sent_row.get("state_value") or "0").strip()))
                except Exception:
                    last_id = 0

                recipients = db.fetch_all(
                    "sql/contacts/select_contacts_simple.sql",
                    (last_id,),
                )

                total_records = len(recipients)
                if total_records == 0:
                    console.print("[bold yellow]Atenção: Nenhum destinatário elegível encontrado no Postgres[/bold yellow]")
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
                configured_batch_size = self.config.email_config.get("batch_size", 30)
                if configured_batch_size <= 0:
                    configured_batch_size = 30
                total_batches = math.ceil(total_records / configured_batch_size) if total_records > 0 else 0
                
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
                    
                    def _iter_batches(items: List[Dict[str, Any]], size: int):
                        for i in range(0, len(items), size):
                            yield items[i:i+size]

                    for batch_idx, batch_recipients in enumerate(_iter_batches(recipients, configured_batch_size)):
                        if not batch_recipients:
                            continue

                        batch_panel = Text(f"Lote {batch_idx + 1}/{int(total_batches)} - Processando {len(batch_recipients)} destinatários", style="bold blue")
                        progress.console.print(batch_panel)
                        
                        current_batch_processed_count = 0 # Emails processed in this specific non-empty batch

                        for recipient in batch_recipients:
                            progress.update(progress_task, advance=1)
                            recipient_email = str(recipient.get('email', '')).strip()
                            
                            if not recipient_email:
                                email_results.append({
                                    'email': 'Missing email',
                                    'status': '[red]Erro[/red]',
                                    'tentativas': '0',
                                    'detalhes': 'Email ausente'
                                })
                                failed += 1
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
                                    # Atualizar estado do último enviado com sucesso
                                    try:
                                        db.execute(
                                            "sql/runtime/upsert_send_state.sql",
                                            (STATE_KEY, str(recipient.get('id'))),
                                        )
                                    except Exception as st_exc:
                                        log.warning(f"Falha ao atualizar estado de envio: {st_exc}")
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
                    # Nada a marcar no fluxo simplificado
                    
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
            # Descadastros/bounces já são filtrados na SQL
            summary_table.add_row("Total de Tentativas", str(total_attempts))
            summary_table.add_row("Média de Tentativas por Email", f"{avg_attempts_per_email:.2f}")
            summary_table.add_row("Falhas por Erro de Conexão", str(total_connection_errors))
            summary_table.add_row("Tempo Total de Execução", f"{tempo_total_min:.2f} minutos ({duration:.1f}s)")
            
            console.print(summary_table)
            
            # Gerar relatório usando o report_generator
            report_data = self.generate_report(start_time, end_time, total_send_attempts, successful, failed)
            
            console.print(f"Relatório salvo em: [bold cyan]{report_data.get('report_file', 'N/A')}[/bold cyan]")
            
            return report_data
        
        except Exception as e:
            import traceback
            log.error(f"Erro no processo de envio de emails: {str(e)}")
            log.debug(traceback.format_exc())
            raise