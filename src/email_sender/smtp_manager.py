\
import smtplib
import logging
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from contextlib import contextmanager
from typing import Dict, Any, List, Tuple

from .config import Config # Assuming Config is accessible like this

log = logging.getLogger(__name__) # Use module-specific logger

class SmtpManager:
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
                    log.info(f"Attempt {attempt + 1} of {retry_attempts} to connect to SMTP...")
                
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
                log.info(f"Successfully connected to SMTP server: {self.config.smtp_config['host']}:{self.config.smtp_config['port']}")
                break
            except Exception as e:
                last_exception = e
                log.error(f"SMTP connection attempt {attempt + 1} failed: {str(e)}")
                if smtp:
                    try:
                        smtp.close()
                    except:
                        pass # Ignore errors during close on a failed connection
                if attempt < retry_attempts - 1 and retry_delay > 0:
                    time.sleep(retry_delay)
                smtp = None # Ensure smtp is None if connection failed
        
        if smtp is None:
            log.error(f"Failed to connect to SMTP server after {retry_attempts} attempts. Last error: {str(last_exception)}")
            raise Exception(f"Failed to connect to SMTP server after {retry_attempts} attempts: {str(last_exception)}")

        try:
            yield smtp
        finally:
            if smtp:
                try:
                    smtp.quit()
                    log.info("SMTP connection closed.")
                except Exception as e:
                    log.warning(f"Error during SMTP quit: {e}. Attempting close().")
                    try:
                        smtp.close()
                        log.info("SMTP connection closed via close().")
                    except Exception as e_close:
                        log.error(f"Error during SMTP close: {e_close}")


    def _create_message(self, to_email: str, subject: str, content: str, is_html: bool = False) -> MIMEMultipart:
        log.debug(f"Criando mensagem para: {to_email}")
        log.debug(f"Assunto: {subject}")
        log.debug(f"Conteúdo (primeiros 200 caracteres): {content[:200] if content else 'Conteúdo vazio'}")
        log.debug(f"is_html: {is_html}")
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        
        # Use sender from email_config, extract only the email address for From, Reply-To, Return-Path
        sender_display_name = self.config.email_config.get("sender", "Default Sender <default@example.com>")
        sender_email = self._extract_email_address(sender_display_name)

        message["From"] = sender_display_name # Full sender for display
        message["Reply-To"] = sender_email
        message["Return-Path"] = sender_email
        message["To"] = to_email
        
        if not is_html:
            log.debug("Criando parte de texto simples")
            text_part = MIMEText(content, "plain", "utf-8")
            message.attach(text_part)
        else:
            log.debug("Criando partes MIME para email HTML")
            # Create plain text version from HTML
            text_content = re.sub(r'<style[^<]*</style>', '', content, flags=re.IGNORECASE | re.DOTALL) # Remove style blocks
            text_content = re.sub(r'<[^>]+>', '', text_content) # Strip all other HTML tags
            text_content = re.sub(r'\\s+', ' ', text_content).strip() # Normalize whitespace
            
            log.debug(f"Texto plano gerado (primeiros 200 caracteres): {text_content[:200] if text_content else 'Texto vazio'}")
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)
            
            html_part = MIMEText(content, "html", "utf-8")
            message.attach(html_part)
            log.debug("Partes HTML e texto adicionadas à mensagem")
            
        return message

    def send_email(self, to_email: str, subject: str, content: str, is_html: bool = False) -> None:
        """
        Sends a single email.
        """
        try:
            log.debug(f"Iniciando envio de email para: {to_email}")
            log.debug(f"Assunto: {subject}")
            log.debug(f"Tamanho do conteúdo: {len(content) if content else 0}")
            log.debug(f"is_html: {is_html}")
            
            message = self._create_message(to_email, subject, content, is_html)
            with self._create_smtp_connection() as smtp:
                log.info(f"Sending email to: {to_email} with subject: '{subject}'")
                smtp.send_message(message)
                log.info(f"Successfully sent email to: {to_email}")
        except smtplib.SMTPServerDisconnected:
            # This specific exception might indicate a need to re-establish connection and retry.
            # For a single send, we might retry once or let the higher level handle retries for batches.
            log.warning(f"SMTP server disconnected while trying to send to {to_email}. Attempting one reconnect and send.")
            try:
                message = self._create_message(to_email, subject, content, is_html) # Recreate message just in case
                with self._create_smtp_connection() as smtp: # New connection
                    smtp.send_message(message)
                    log.info(f"Successfully sent email to: {to_email} after reconnect.")
            except Exception as e_retry:
                log.error(f"Failed to send email to {to_email} after reconnect: {str(e_retry)}")
                raise e_retry # Re-raise the exception from the retry attempt
        except Exception as e:
            log.error(f"Failed to send email to {to_email}: {str(e)}")
            raise e # Re-raise other exceptions

    def send_bulk_emails(self, recipients_data: List[Dict[str, Any]], subject_template: str, body_template_path: str, template_processor_func) -> Tuple[int, int]:
        """
        Sends emails in bulk using a template processor.
        Manages SMTP connection for the batch.
        Args:
            recipients_data: List of dictionaries, each with recipient info (must include 'email').
            subject_template: The subject line for the email (can have placeholders).
            body_template_path: Path to the HTML body template.
            template_processor_func: A function that takes (template_path, recipient_data, subject) and returns processed HTML.
        Returns:
            A tuple (successful_sends, failed_sends)
        """
        successful_sends = 0
        failed_sends = 0

        if not recipients_data:
            log.info("No recipients provided for bulk email sending.")
            return 0, 0
        
        log.info(f"Starting bulk email sending to {len(recipients_data)} recipients.")

        try:
            with self._create_smtp_connection() as smtp:
                for recipient in recipients_data:
                    recipient_email = recipient.get("email")
                    if not recipient_email:
                        log.warning(f"Skipping recipient due to missing email address: {recipient}")
                        failed_sends += 1
                        continue

                    try:
                        # Process subject template (simple formatting for now)
                        processed_subject = subject_template
                        for key, value in recipient.items():
                            processed_subject = processed_subject.replace(f"{{{key}}}", str(value))
                        
                        # Process body template using the provided processor function
                        # The template_processor_func is expected to handle its own errors and raise if critical
                        processed_body = template_processor_func(body_template_path, recipient, processed_subject)

                        message = self._create_message(
                            to_email=recipient_email,
                            subject=processed_subject,
                            content=processed_body,
                            is_html=True  # Assuming bulk emails are HTML
                        )
                        
                        log.debug(f"Attempting to send email to: {recipient_email}")
                        smtp.send_message(message)
                        log.info(f"Successfully sent email to: {recipient_email}")
                        successful_sends += 1
                    
                    except smtplib.SMTPServerDisconnected:
                        log.warning(f"SMTP server disconnected before sending to {recipient_email}. Attempting to resend this email with a new connection.")
                        # This is a critical failure for this specific email in the batch.
                        # We'll try to resend this one email immediately with a fresh connection.
                        try:
                            # Re-process templates and recreate message as they might be stateful or connection dependent
                            processed_subject_retry = subject_template
                            for key, value in recipient.items():
                                processed_subject_retry = processed_subject_retry.replace(f"{{{key}}}", str(value))
                            processed_body_retry = template_processor_func(body_template_path, recipient, processed_subject_retry)
                            
                            message_retry = self._create_message(recipient_email, processed_subject_retry, processed_body_retry, is_html=True)
                            
                            with self._create_smtp_connection() as new_smtp: # Fresh connection for this one email
                                new_smtp.send_message(message_retry)
                            log.info(f"Successfully resent email to {recipient_email} after server disconnection.")
                            successful_sends += 1
                        except Exception as e_resend:
                            log.error(f"Failed to resend email to {recipient_email} after server disconnection: {e_resend}")
                            failed_sends += 1
                            # Optionally, re-raise or log this specific failure and continue with the batch.
                            # For now, we log and increment failed_sends.

                    except Exception as e_recipient:
                        log.error(f"Error sending email to {recipient_email}: {str(e_recipient)}")
                        failed_sends += 1
                        # Log the error and continue with the next recipient in the batch.
            
            log.info(f"Bulk email sending finished. Successful: {successful_sends}, Failed: {failed_sends}")

        except Exception as e_outer:
            # This catches failure in the initial _create_smtp_connection() or other unexpected errors
            log.error(f"Critical error during bulk email sending setup or outer loop: {str(e_outer)}")
            # All remaining emails that weren't attempted are effectively failed if connection couldn't be established.
            # However, successful_sends and failed_sends would reflect those processed *before* this critical error.
            # To be more precise, one might adjust counts here, but it's complex.
            # For now, we assume this error means the batch couldn't proceed further.
            # The current failed_sends count will include those that failed before this point.
            # We might consider all *remaining* emails as failed if the connection itself failed.
            # For simplicity, we'll rely on the loop's accounting.
            if successful_sends == 0 and failed_sends == 0: # If no emails were even attempted
                 failed_sends = len(recipients_data) # Mark all as failed if connection never established

        return successful_sends, failed_sends

