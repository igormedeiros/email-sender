import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.logging import RichHandler
from pathlib import Path
import logging
from .config import Config
from .email_service import EmailService
from .utils.xlsx_reader import XLSXReader
import time
from datetime import datetime

app = typer.Typer()
console = Console()

# Configure logging with Rich handler
logging.basicConfig(
    level=logging.INFO,  # Changed back to INFO level
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
log = logging.getLogger("email_sender")

def generate_report(start_time, end_time, total_sent, successful, failed, output_file):
    duration = end_time - start_time
    avg_time = duration/total_sent if total_sent > 0 else 0
    report = f"""Relatório de Envio de Emails
Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
-----------------------------------------
Total de emails tentados: {total_sent}
Enviados com sucesso: {successful}
Falhas: {failed}
Tempo total: {duration:.2f} segundos
Tempo médio por email: {avg_time:.2f} segundos
"""
    # Ensure reports directory exists
    Path("reports").mkdir(exist_ok=True)
    
    # Save report in reports directory
    report_path = Path("reports") / output_file
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    return report

@app.command()
def send_emails(
    xlsx_file: str = typer.Option(None, help="Path to XLSX file containing email recipients"),
    template: str = typer.Argument(..., help="Name of the template file to use"),
    subject: str = typer.Option(None, "--subject", "-s", help="Email subject (optional, uses default from config if not provided)"),
    config_file: str = typer.Option("dev.properties", "--config", "-c", help="Path to config file"),
):
    """
    Send batch emails using a XLSX file and email template.
    """
    try:
        config = Config(config_file)
        email_service = EmailService(config)
        xlsx_path = xlsx_file or config.email_config["xlsx_file"]
        email_subject = subject or config.email_config["default_subject"]
        xlsx_reader = XLSXReader(xlsx_path, config.email_config["batch_size"])
        
        total_records = xlsx_reader.total_records
        if (total_records == 0):
            console.print("\n⚠️ No emails to send! All emails have been sent or marked as failed.", style="yellow")
            return
            
        log.info(f"Starting email send process using spreadsheet: {xlsx_path}")
        log.info(f"Email subject: {email_subject}")
        log.info("Press 'q' to quit at any time")
        
        start_time = time.time()
        successful = 0
        failed = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,  # This ensures the progress bar doesn't leave artifacts
        ) as progress:
            task = progress.add_task(
                f"[cyan]Enviando emails... [white]({total_records} restantes)",
                total=total_records
            )
            
            import sys, select
            current_record = 0
            
            for batch in xlsx_reader.get_batches():
                # Check for 'q' key press between batches
                if (sys.stdin in select.select([sys.stdin], [], [], 0)[0]):
                    char = sys.stdin.read(1)
                    if (char == 'q'):
                        console.print("\n🛑 Process interrupted by user", style="yellow")
                        break
                
                for recipient in batch:
                    try:
                        log.info(f"Sending email to: {recipient['email']}")
                        email_service.send_batch([recipient], template, email_subject)
                        xlsx_reader.mark_as_sent(recipient['email'])
                        successful += 1
                    except Exception as e:
                        log.error(f"Failed to send email to {recipient['email']}: {str(e)}")
                        xlsx_reader.mark_as_failed(recipient['email'])
                        failed += 1
                    current_record += 1
                    remaining = total_records - current_record
                    progress.update(task, completed=current_record, description=f"[cyan]Enviando emails... [white]({remaining} restantes)")

        end_time = time.time()
        report_file = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report = generate_report(start_time, end_time, total_records, successful, failed, report_file)
        
        console.print(f"\n✅ Email sending completed!", style="green")
        console.print(f"📊 Report saved to: {report_file}", style="blue")
        console.print("\nReport Summary:", style="yellow")
        console.print(report)
    
    except Exception as e:
        console.print(f"\n❌ Error: {str(e)}", style="red")
        raise typer.Exit(1)

@app.command()
def test_smtp(
    config_file: str = typer.Option("dev.properties", "--config", "-c", help="Path to config file"),
):
    """
    Test SMTP connection by sending a test email to the configured test recipient.
    """
    try:
        config = Config(config_file)
        email_service = EmailService(config)
        test_recipient = config.email_config.get("test_recipient")
        
        if (not test_recipient):
            raise ValueError("test_recipient not configured in properties file")
            
        console.print("🔄 Testing SMTP connection...", style="yellow")
        
        message = "This is a test email from the email-sender application."
        
        with email_service._create_smtp_connection() as smtp:
            test_message = email_service._create_message(
                to_email=test_recipient,
                subject="SMTP Test Email",
                text_content=message
            )
            smtp.send_message(test_message)
            
        console.print(f"✅ SMTP test successful! Test email sent to {test_recipient}", style="green")
    
    except Exception as e:
        console.print(f"❌ SMTP test failed: {str(e)}", style="red")
        raise typer.Exit(1)

@app.command()
def clear_sent_flags(
    xlsx_file: str = typer.Option(None, help="Path to XLSX file containing email recipients"),
    config_file: str = typer.Option("dev.properties", "--config", "-c", help="Path to config file"),
):
    """
    Clear all 'sent' and 'failed' flags from the XLSX file.
    """
    try:
        config = Config(config_file)
        xlsx_path = xlsx_file or config.email_config["xlsx_file"]
        xlsx_reader = XLSXReader(xlsx_path)
        
        console.print("🔄 Clearing sent flags...", style="yellow")
        xlsx_reader.clear_sent_flags()
        console.print("✅ All flags cleared successfully!", style="green")
    
    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()