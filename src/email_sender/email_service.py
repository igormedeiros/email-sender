import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from pathlib import Path
from .config import Config

class EmailService:
    def __init__(self, config: Config):
        self.config = config

    def _create_smtp_connection(self):
        smtp = smtplib.SMTP(self.config.smtp_config["host"], self.config.smtp_config["port"])
        if self.config.smtp_config["use_tls"]:
            smtp.starttls()
        smtp.login(
            self.config.smtp_config["username"],
            self.config.smtp_config["password"]
        )
        return smtp

    def _create_message(self, to_email: str, subject: str, text_content: str) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.config.email_config["sender"]
        message["To"] = to_email
        
        text_part = MIMEText(text_content, "plain")
        message.attach(text_part)
        return message

    def _read_template(self, template_path: str) -> str:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _format_template(self, template: str, recipient: Dict) -> str:
        """Format template with recipient data."""
        return template.format(**recipient)

    def send_batch(self, recipients: List[Dict], template_path: str, subject: str) -> None:
        template_content = self._read_template(template_path)
        
        with self._create_smtp_connection() as smtp:
            for recipient in recipients:
                formatted_content = self._format_template(template_content, recipient)
                message = self._create_message(
                    to_email=recipient["email"],
                    subject=subject,
                    text_content=formatted_content
                )
                smtp.send_message(message)