import typer
from pathlib import Path
from .config import Config
from .email_service import EmailService
from .utils.xlsx_reader import XLSXReader
import time
from datetime import datetime
import signal

app = typer.Typer()

# Timeout handler
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

signal.signal(signal.SIGALRM, timeout_handler)

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
    Send batch emails using a XLSX file and email template (Fast version).
    """
    try:
        config = Config(config_file)
        email_service = EmailService(config)
        xlsx_path = xlsx_file or config.email_config["xlsx_file"]
        email_subject = subject or config.email_config["default_subject"]
        xlsx_reader = XLSXReader(xlsx_path, config.email_config["batch_size"])
        
        total_records = xlsx_reader.total_records
        if total_records == 0:
            print("⚠️ No emails to send!")
            return
            
        print(f"Starting email send process...")
        print(f"Total emails to send: {total_records}")
        
        start_time = time.time()
        successful = 0
        failed = 0
        current_record = 0
        batch_delay = config.email_config.get("batch_delay", 60)
        retry_attempts = config.email_config.get("retry_attempts", 5)
        retry_delay = config.email_config.get("retry_delay", 60)
        send_timeout = config.email_config.get("send_timeout", 10)
        
        for batch in xlsx_reader.get_batches():
            for recipient in batch:
                attempts = 0
                while attempts < retry_attempts:
                    try:
                        print(f"Enviando para: {recipient['email']}")
                        signal.alarm(send_timeout)  # Set timeout for email sending
                        email_service.send_batch([recipient], template, email_subject)
                        signal.alarm(0)  # Reset the alarm
                        successful += 1
                        break
                    except TimeoutException:
                        print(f"Timeout ao enviar para: {recipient['email']}")
                        failed += 1
                        break
                    except Exception as e:
                        attempts += 1
                        if attempts >= retry_attempts:
                            print(f"Failed to send to {recipient['email']} after {retry_attempts} attempts: {str(e)}")
                            failed += 1
                        else:
                            print(f"Retrying to send to {recipient['email']} in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})")
                            if retry_delay > 0:  # Only sleep if delay is greater than 0
                                time.sleep(retry_delay)
                signal.alarm(0)  # Ensure the alarm is reset after processing
                current_record += 1
                
                # Minimal progress indication
                if current_record % 50 == 0:
                    print(f"Processed {current_record}/{total_records} emails")
            
            # Delay between batches
            if batch_delay > 0:  # Only sleep if delay is greater than 0
                print(f"Aguardando {batch_delay} segundos antes de enviar o próximo lote...")
                time.sleep(batch_delay)

        end_time = time.time()
        report_file = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report = generate_report(start_time, end_time, total_records, successful, failed, report_file)
        
        print("\n✅ Email sending completed!")
        print(f"📊 Report saved to: reports/{report_file}")
        print("\nReport Summary:")
        print(report)
    
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
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
        
        if not test_recipient:
            raise ValueError("test_recipient not configured in properties file")
            
        print("Testing SMTP connection...")
        
        message = "This is a test email from the email-sender application."
        
        with email_service._create_smtp_connection() as smtp:
            test_message = email_service._create_message(
                to_email=test_recipient,
                subject="SMTP Test Email",
                text_content=message
            )
            smtp.send_message(test_message)
            
        print(f"✅ SMTP test successful! Test email sent to {test_recipient}")
    
    except Exception as e:
        print(f"❌ SMTP test failed: {str(e)}")
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
        
        print("Clearing sent flags...")
        xlsx_reader.clear_sent_flags()
        print("✅ All flags cleared successfully!")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()