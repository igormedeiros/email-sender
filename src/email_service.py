import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from pathlib import Path
import re
import time
import logging
from contextlib import contextmanager
from .config import Config

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config

    def _extract_email_address(self, sender: str) -> str:
        """Extract email address from sender string format 'Name | Company <email@domain.com>'"""
        match = re.search(r'<([^>]+)>', sender)
        return match.group(1) if match else sender

    @contextmanager
    def _create_smtp_connection(self):
        retry_attempts = self.config.smtp_config.get("retry_attempts", 3)
        retry_delay = self.config.smtp_config.get("retry_delay", 5)
        timeout = self.config.smtp_config.get("send_timeout", 10)
        last_exception = None
        smtp = None

        for attempt in range(retry_attempts):
            try:
                if attempt > 0:
                    log.info(f"Tentativa {attempt + 1} de {retry_attempts} de conectar ao SMTP...")
                
                smtp = smtplib.SMTP(
                    self.config.smtp_config["host"],
                    self.config.smtp_config["port"],
                    timeout=timeout
                )
                
                if self.config.smtp_config["use_tls"]:
                    smtp.starttls()
                    
                smtp.login(
                    self.config.smtp_config["username"],
                    self.config.smtp_config["password"]
                )
                
                break
            except Exception as e:
                last_exception = e
                if smtp:
                    try:
                        smtp.close()
                    except:
                        pass
                if attempt < retry_attempts - 1 and retry_delay > 0:
                    log.error(f"Falha na conexão SMTP: {str(e)}")
                    time.sleep(retry_delay)
                smtp = None
        
        if smtp is None:
            raise Exception(f"Falha ao conectar ao servidor SMTP após {retry_attempts} tentativas: {str(last_exception)}")

        try:
            yield smtp
        finally:
            try:
                smtp.quit()
            except:
                try:
                    smtp.close()
                except:
                    pass

    def _create_message(self, to_email: str, subject: str, content: str, is_html: bool = False) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        sender_email = self._extract_email_address(self.config.email_config["sender"])
        message["From"] = self.config.email_config["sender"]
        message["Reply-To"] = sender_email
        message["Return-Path"] = sender_email
        message["To"] = to_email
        
        # Se não for HTML, envia como texto simples
        if not is_html:
            text_part = MIMEText(content, "plain", "utf-8")
            message.attach(text_part)
        # Se for HTML, envia a parte HTML e também uma versão em texto simples convertida
        else:
            # Versão texto simples - versão básica sem formatação
            text_content = re.sub(r'<.*?>', '', content)
            text_content = re.sub(r'\s+', ' ', text_content)
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)
            
            # Versão HTML
            html_part = MIMEText(content, "html", "utf-8")
            message.attach(html_part)
            
        return message

    def _read_template(self, template_path: str) -> str:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _format_template(self, template: str, recipient: Dict) -> str:
        """Format template with recipient data."""
        # Substituir parâmetros do formato {param}
        result = template
        for key, value in recipient.items():
            placeholder = '{' + key + '}'
            result = result.replace(placeholder, str(value))
        return result

    def send_batch(self, recipients: List[Dict], content: str, subject: str, is_html: bool = False) -> None:
        try:
            log.info(f"Iniciando envio em lote para {len(recipients)} destinatários")
            log.info(f"Modo HTML: {'Sim' if is_html else 'Não'}")
            
            with self._create_smtp_connection() as smtp:
                for recipient in recipients:
                    try:
                        # Formatar o conteúdo com os dados do destinatário
                        formatted_content = self._format_template(content, recipient)
                        
                        # Criar a mensagem
                        message = self._create_message(
                            to_email=recipient["email"],
                            subject=subject,
                            content=formatted_content,
                            is_html=is_html
                        )
                        
                        # Log de debug antes do envio
                        log.info(f"Pronto para enviar email para: {recipient['email']}")
                        
                        # Enviar a mensagem
                        try:
                            smtp.send_message(message)
                            log.info(f"Email enviado com sucesso para: {recipient['email']}")
                        except smtplib.SMTPException as smtp_error:
                            log.error(f"Erro SMTP ao enviar para {recipient['email']}: {str(smtp_error)}")
                            raise smtp_error
                        except Exception as send_error:
                            log.error(f"Erro geral ao enviar para {recipient['email']}: {str(send_error)}")
                            raise send_error
                            
                    except smtplib.SMTPServerDisconnected:
                        # Se a conexão foi perdida, tenta reconectar e reenviar este email
                        log.warning("Conexão SMTP perdida. Tentando reconectar...")
                        with self._create_smtp_connection() as new_smtp:
                            new_smtp.send_message(message)
                    except Exception as e:
                        # Outros erros devem ser propagados
                        log.error(f"Erro no processamento do destinatário {recipient['email']}: {str(e)}")
                        raise e
        except Exception as e:
            log.error(f"Erro no envio em lote: {str(e)}")
            raise