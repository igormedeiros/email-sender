import typer
from pathlib import Path
from .config import Config
from .email_service import EmailService
from .utils.csv_reader import CSVReader
import time
from datetime import datetime
import signal
import sys
import logging
import pandas as pd
from typing import List, Dict, Optional
import csv
from enum import Enum
import re

class SendMode(str, Enum):
    test = "test"
    production = "production"

app = typer.Typer()
log = logging.getLogger("email_sender")

# Timeout handler
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException

def interrupt_handler(signum, frame):
    print("\nProcess interrupted by user. Saving progress...")
    sys.exit(1)

# Set up signal handlers
signal.signal(signal.SIGALRM, timeout_handler)
signal.signal(signal.SIGINT, interrupt_handler)

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

def load_unsubscribed_emails(unsubscribe_file: str = "data/descadastros.csv") -> List[str]:
    """Load unsubscribed emails from CSV file"""
    try:
        df = pd.read_csv(unsubscribe_file)
        return df['email'].str.lower().tolist()
    except FileNotFoundError:
        print(f"⚠️ Unsubscribed emails file {unsubscribe_file} not found. Proceeding without list.")
        return []
    except Exception as e:
        print(f"⚠️ Error loading unsubscribed emails: {str(e)}. Proceeding without list.")
        return []

def sync_unsubscribed_emails(csv_path: str, unsubscribe_file: str) -> int:
    """
    Sincroniza a lista de emails descadastrados com o arquivo principal.
    
    Args:
        csv_path: Caminho para o arquivo CSV principal
        unsubscribe_file: Caminho para o arquivo CSV de descadastros
        
    Returns:
        Número de emails marcados como descadastrados
    """
    try:
        print(f"Sincronizando lista de emails descadastrados de {unsubscribe_file} com {csv_path}...")
        
        start_time = time.time()
        
        # Verificar se os arquivos existem
        if not Path(csv_path).exists():
            print(f"❌ Arquivo principal {csv_path} não encontrado.")
            return 0
            
        if not Path(unsubscribe_file).exists():
            print(f"⚠️ Arquivo de descadastros {unsubscribe_file} não encontrado.")
            return 0
            
        # Otimização: Usar sets para operações mais rápidas
        unsubscribed = set()
        
        # Lê lista de descadastros de forma eficiente 
        try:
            # Tenta primeiro ler como CSV com cabeçalho
            df_unsubscribed = pd.read_csv(unsubscribe_file, low_memory=False)
            if 'email' in df_unsubscribed.columns:
                unsubscribed = set(df_unsubscribed['email'].str.lower().dropna())
            else:
                # Se não tiver coluna 'email', tenta ler a primeira coluna
                unsubscribed = set(df_unsubscribed.iloc[:, 0].str.lower().dropna())
        except Exception as e:
            # Se falhar, tenta ler linha por linha como texto
            print(f"Tentando ler arquivo como texto simples: {str(e)}")
            with open(unsubscribe_file, 'r', encoding='utf-8') as file:
                for line in file:
                    email = line.strip().lower()
                    if email and not email.startswith('email'):
                        unsubscribed.add(email)
            
        if not unsubscribed:
            print(f"⚠️ Nenhum email encontrado na lista de descadastros.")
            return 0
            
        print(f"Encontrados {len(unsubscribed)} emails descadastrados.")
        
        # Atualiza o arquivo principal - carregando por chunks para maior eficiência com arquivos grandes
        # O processamento por chunks reduz significativamente o uso de memória
        chunked_processing = True
        update_count = 0
        added_count = 0
        
        try:
            # Verificar tamanho do arquivo
            csv_size = Path(csv_path).stat().st_size
            large_file = csv_size > 10 * 1024 * 1024  # 10MB é considerado um arquivo grande
            
            if large_file and chunked_processing:
                # Processamento por chunks para arquivos grandes
                chunk_size = 10000  # Ajuste baseado em testes de performance
                chunks_updated = 0
                total_rows = 0
                
                # Carregar a lista completa para verificar emails inexistentes
                df = pd.read_csv(csv_path)
                
                # Verifica se a coluna descadastro existe, senão cria
                if 'descadastro' not in df.columns:
                    df['descadastro'] = ''
                
                # Obtém lista de emails existentes (lowercase para comparação correta)
                existing_emails = set(df['email'].str.lower())
                
                # Identifica emails descadastrados que não existem na lista principal
                missing_emails = unsubscribed - existing_emails
                
                if missing_emails:
                    print(f"Encontrados {len(missing_emails)} emails na lista de descadastros que não existem na lista principal.")
                    
                    # Prepara novos registros para adicionar à lista principal
                    new_rows = []
                    for email in missing_emails:
                        new_rows.append({
                            'email': email,
                            'descadastro': 'S',
                            'enviado': '',
                            'falhou': ''
                        })
                    
                    # Adiciona novos registros ao DataFrame
                    if new_rows:
                        df_new = pd.DataFrame(new_rows)
                        df = pd.concat([df, df_new], ignore_index=True)
                        added_count = len(new_rows)
                        print(f"Adicionados {added_count} novos emails descadastrados à lista principal.")
                
                # Backup dos valores atuais para contar alterações
                previous_status = df['descadastro'].copy()
                
                # Atualiza a coluna de forma vetorizada para todos os emails
                df['descadastro'] = df['email'].str.lower().isin(unsubscribed).map({True: 'S', False: ''})
                
                # Conta quantos emails foram atualizados (excluindo os novos adicionados)
                update_count = ((df['descadastro'] != previous_status) & 
                               (df.index < len(previous_status))).sum()
                
                # Salva o arquivo atualizado
                df.to_csv(csv_path, index=False)
                
            else:
                # Processamento direto para arquivos menores
                df = pd.read_csv(csv_path)
                
                # Verifica se a coluna descadastro existe, senão cria
                if 'descadastro' not in df.columns:
                    df['descadastro'] = ''
                
                # Obtém lista de emails existentes (lowercase para comparação correta)
                existing_emails = set(df['email'].str.lower())
                
                # Identifica emails descadastrados que não existem na lista principal
                missing_emails = unsubscribed - existing_emails
                
                if missing_emails:
                    print(f"Encontrados {len(missing_emails)} emails na lista de descadastros que não existem na lista principal.")
                    
                    # Prepara novos registros para adicionar à lista principal
                    new_rows = []
                    for email in missing_emails:
                        new_rows.append({
                            'email': email,
                            'descadastro': 'S',
                            'enviado': '',
                            'falhou': ''
                        })
                    
                    # Adiciona novos registros ao DataFrame
                    if new_rows:
                        df_new = pd.DataFrame(new_rows)
                        df = pd.concat([df, df_new], ignore_index=True)
                        added_count = len(new_rows)
                        print(f"Adicionados {added_count} novos emails descadastrados à lista principal.")
                
                # Backup dos valores atuais para contar alterações (excluindo novos registros)
                previous_status = df['descadastro'].copy()
                
                # Atualiza a coluna de forma vetorizada
                df['descadastro'] = df['email'].str.lower().isin(unsubscribed).map({True: 'S', False: ''})
                
                # Conta quantos emails foram atualizados (excluindo os novos adicionados)
                update_count = ((df['descadastro'] != previous_status) & 
                               (df.index < len(previous_status))).sum()
                
                # Salva o arquivo atualizado
                df.to_csv(csv_path, index=False)
        
        except Exception as e:
            print(f"❌ Erro ao processar arquivo principal: {str(e)}")
            return 0
            
        total_blacklisted = len(df[df['descadastro'] == 'S'])
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Sincronização concluída em {duration:.2f} segundos!")
        print(f"Total de emails na lista: {len(df)}")
        print(f"Total de emails descadastrados: {total_blacklisted}")
        
        if update_count > 0 or added_count > 0:
            print(f"Emails atualizados nesta sincronização: {update_count}")
            if added_count > 0:
                print(f"Novos emails descadastrados adicionados: {added_count}")
            
        return total_blacklisted
        
    except Exception as e:
        print(f"❌ Erro ao sincronizar lista de descadastros: {str(e)}")
        return 0

@app.command()
def sync_unsubscribed_command(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    unsubscribe_file: str = typer.Option(None, help="Path to CSV file with unsubscribed emails"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
):
    """
    Sincroniza a lista de emails descadastrados com o arquivo principal.
    Além de marcar os emails descadastrados existentes, também adiciona emails
    que estão na lista de descadastro mas não existem na lista principal.
    """
    try:
        config = Config(config_file, content_file)
        csv_path = csv_file or config.email_config["csv_file"]
        unsubscribe_path = unsubscribe_file or config.email_config.get("unsubscribe_file", "data/descadastros.csv")
        
        sync_unsubscribed_emails(csv_path, unsubscribe_path)
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        raise typer.Exit(1)

@app.command()
def send_emails(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    template: str = typer.Argument(..., help="Name of the HTML template file to use"),
    subject: str = typer.Option(None, "--subject", "-s", help="[OBSOLETO] O assunto será sempre lido do arquivo email.yaml"),
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
        email_service = EmailService(config)
        
        # Verificar configurações SMTP
        print("\n----- Configurações SMTP -----")
        print(f"Servidor: {config.smtp_config['host']}:{config.smtp_config['port']}")
        print(f"Usuário: {config.smtp_config['username']}")
        print(f"TLS ativado: {config.smtp_config['use_tls']}")
        
        # Determine which file to use based on the mode
        is_test_mode = (mode == SendMode.test)
        
        if is_test_mode:
            test_emails_file = config.email_config.get("test_emails_file", "data/test_emails.csv")
            csv_path = test_emails_file
            print(f"\n⚠️ MODO TESTE: Usando arquivo de teste {test_emails_file}")
        else:
            csv_path = csv_file or config.email_config["csv_file"]
            print(f"\n🚨 MODO PRODUÇÃO: Usando arquivo principal {csv_path}")
            print("⚠️ CUIDADO: Envios em modo produção podem atingir muitos destinatários!")
            
        # Usar subject do arquivo email.yaml, ignorando o parâmetro na linha de comando
        email_subject = config.content_config.get("email", {}).get("subject", "Sem assunto")
        print(f"Assunto do email: {email_subject}")
        
        # Sincronizar lista de descadastros antes de enviar (a menos que seja explicitamente ignorado)
        # Só sincroniza no modo produção
        if not skip_unsubscribed_sync and not is_test_mode:
            unsubscribe_file = config.email_config.get("unsubscribe_file", "data/descadastros.csv")
            sync_unsubscribed_emails(csv_path, unsubscribe_file)
        
        csv_reader = CSVReader(csv_path, config.email_config["batch_size"])
        
        # Ensure template has .html extension
        if not template.endswith('.html'):
            template += '.html'
            
        # Check if the template exists in the provided path or in templates/ directory
        template_path = Path(template)
        if not template_path.exists():
            root_template_path = Path("templates") / template_path.name
            if root_template_path.exists():
                template_path = root_template_path
            else:
                raise FileNotFoundError(f"Template file not found: {template}")
        else:
            template_path = template_path.resolve()

        total_records = csv_reader.total_records
        if total_records == 0:
            print("⚠️ No emails to send!")
            return
            
        print(f"Starting HTML email send process...")
        
        # Verificar total de emails no arquivo
        total_emails_in_file = len(csv_reader.df)
        unsubscribed_count = 0
        
        # Verificar total de emails descadastrados se a coluna existir
        if 'descadastro' in csv_reader.df.columns:
            unsubscribed_count = len(csv_reader.df[csv_reader.df['descadastro'] == 'S'])
            
        already_sent = len(csv_reader.df[csv_reader.df['enviado'] == 'ok'])
        failed_count = len(csv_reader.df[csv_reader.df['falhou'] == 'ok'])
        
        # Mostrar estatísticas
        print(f"Total de emails na lista: {total_emails_in_file}")
        print(f"Emails válidos para envio: {total_records}")
        
        if unsubscribed_count > 0:
            print(f"Emails descadastrados (ignorados): {unsubscribed_count}")
            
        if already_sent > 0:
            print(f"Emails já enviados: {already_sent}")
            
        if failed_count > 0:
            print(f"Emails que falharam: {failed_count}")
            
        print("Press Ctrl+C to safely stop the process")
        
        start_time = time.time()
        successful = 0
        failed = 0
        current_record = 0
        batch_delay = config.email_config.get("batch_delay", 60)
        retry_attempts = config.email_config.get("retry_attempts", 5)
        retry_delay = config.email_config.get("retry_delay", 60)
        send_timeout = config.email_config.get("send_timeout", 10)
        
        unsubscribed = load_unsubscribed_emails()
        
        try:
            for batch in csv_reader.get_batches():
                batch_successful = []  # Keep track of successful sends in this batch
                batch_failed = 0  # Count failures in this batch
                
                for recipient in batch:
                    if recipient['email'].lower() in unsubscribed:
                        print(f"⚠️ Email {recipient['email']} is unsubscribed. Skipping.")
                        failed += 1
                        batch_failed += 1
                        continue
                    
                    attempts = 0
                    while attempts < retry_attempts:
                        try:
                            print(f"Enviando para: {recipient['email']}")
                            signal.alarm(send_timeout)  # Set timeout for email sending
                            
                            # Load and modify HTML template
                            try:
                                with open(template_path, 'r', encoding='utf-8') as file:
                                    html_content = file.read()
                                
                                # Primeiro substituir os campos obrigatórios
                                html_content = html_content.replace("{unsubscribe_url}", config.content_config.get("urls", {}).get("unsubscribe", ""))
                                html_content = html_content.replace("{subscribe_url}", config.content_config.get("urls", {}).get("subscribe", ""))
                                html_content = html_content.replace("{email}", recipient['email'])
                                
                                # Substituir variáveis do evento
                                html_content = html_content.replace("{link_evento}", config.content_config.get("evento", {}).get("link", ""))
                                html_content = html_content.replace("{data_evento}", config.content_config.get("evento", {}).get("data", ""))
                                html_content = html_content.replace("{cidade}", config.content_config.get("evento", {}).get("cidade", ""))
                                html_content = html_content.replace("{local}", config.content_config.get("evento", {}).get("local", ""))
                                
                                # Processar parágrafo condicional de desconto
                                desconto_paragrafo = ""
                                if "promocao" in config.content_config and "desconto" in config.content_config["promocao"]:
                                    desconto_valor = config.content_config["promocao"]["desconto"]
                                    desconto_paragrafo = f"""
                                    <div style="background-color: #e9f2fa; border-left: 4px solid #0066CC; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                        <p style="margin: 0; font-size: 1.1em;">
                                            <strong style="color: #0066CC;">OFERTA ESPECIAL:</strong> Estamos oferecendo <strong style="color: #0066CC; font-size: 1.15em;">{desconto_valor} de desconto</strong> 
                                            no treinamento para quem está recebendo este email.
                                        </p>
                                        <p style="margin: 10px 0 0 0;">
                                            Não é necessário digitar nenhum código promocional – ele já está aplicado e o 
                                            desconto é aplicado automaticamente no link acima.
                                        </p>
                                    </div>
                                    """
                                html_content = html_content.replace("{desconto_paragrafo}", desconto_paragrafo)
                                
                                # Substituir campos de conteúdo dinâmico da configuração
                                for key, value in config.content_config.items():
                                    placeholder = f"{{{key}}}"
                                    if placeholder in html_content:
                                        html_content = html_content.replace(placeholder, str(value))
                                        print(f"  - Substituindo conteúdo dinâmico: {key}")
                                
                                # Verificar todos os campos nas chaves de formatação {campo}
                                placeholders = re.findall(r'\{([^}]+)\}', html_content)
                                print(f"  - Campos encontrados no template: {placeholders}")
                                print(f"  - Campos disponíveis no registro: {list(recipient.keys())}")
                                
                                # Substituir campos extras se existirem no destinatário
                                for placeholder in placeholders:
                                    if placeholder in recipient:
                                        value = recipient[placeholder]
                                        html_content = html_content.replace(f"{{{placeholder}}}", str(value))
                                    else:
                                        print(f"  - ⚠️ Campo {placeholder} não encontrado no registro, substituindo por vazio.")
                                        html_content = html_content.replace(f"{{{placeholder}}}", "")
                            
                                # Use modified HTML template for sending
                                email_service.send_batch([recipient], html_content, email_subject, is_html=True)
                                print(f"✅ Email enviado com sucesso para: {recipient['email']}")
                            except Exception as template_error:
                                print(f"❌ Erro ao preparar ou enviar o email: {str(template_error)}")
                                raise template_error
                                
                            signal.alarm(0)  # Reset the alarm
                            successful += 1
                            batch_successful.append(recipient['email'])  # Add to successful list
                            break
                        except TimeoutException:
                            print(f"Timeout ao enviar para: {recipient['email']}")
                            failed += 1
                            batch_failed += 1
                            break
                        except Exception as e:
                            attempts += 1
                            if attempts >= retry_attempts:
                                print(f"Failed to send to {recipient['email']} after {retry_attempts} attempts: {str(e)}")
                                failed += 1
                                batch_failed += 1
                            else:
                                print(f"Retrying to send to {recipient['email']} in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})")
                                if retry_delay > 0:  # Only sleep if delay is greater than 0
                                    time.sleep(retry_delay)
                    signal.alarm(0)  # Ensure the alarm is reset after processing
                    current_record += 1
                    
                    # Progress indication every 50 emails
                    if current_record % 50 == 0:
                        percentage = (current_record / total_records) * 100
                        print(f"Progresso: {current_record}/{total_records} emails processados ({percentage:.1f}%)")
                
                # Mark all successful emails in this batch before delay
                for email in batch_successful:
                    csv_reader.mark_as_sent(email)
                
                # Summary after each batch
                batch_size = len(batch_successful) + batch_failed
                batch_success_rate = (len(batch_successful) / batch_size) * 100 if batch_size > 0 else 0
                total_success_rate = (successful / current_record) * 100 if current_record > 0 else 0
                remaining = total_records - current_record
                
                print("\nResumo do lote atual:")
                print(f"✓ Enviados neste lote: {len(batch_successful)}")
                print(f"✗ Falhas neste lote: {batch_failed}")
                print(f"Taxa de sucesso do lote: {batch_success_rate:.1f}%")
                print("\nResumo geral:")
                print(f"✓ Total enviados: {successful}")
                print(f"✗ Total falhas: {failed}")
                print(f"Taxa de sucesso geral: {total_success_rate:.1f}%")
                print(f"Faltam: {remaining} emails\n")
                
                # Delay between batches
                if batch_delay > 0:  # Only sleep if delay is greater than 0
                    print(f"Aguardando {batch_delay} segundos antes do próximo lote...")
                    time.sleep(batch_delay)

        except KeyboardInterrupt:
            print("\nProcesso interrompido pelo usuário.")
            print("Salvando progresso...")
            # The CSVReader will handle the safe shutdown
        
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
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
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
            
        print(f"\nEnviando email de teste para: {test_recipient}")
        
        # Usar subject do arquivo email.yaml
        email_subject = config.content_config.get("email", {}).get("subject", "SMTP Test Email")
        
        message = "This is a test email from the email-sender application."
        
        with email_service._create_smtp_connection() as smtp:
            test_message = email_service._create_message(
                to_email=test_recipient,
                subject=email_subject,
                content=message
            )
            smtp.send_message(test_message)
            
        print(f"✅ SMTP test successful! Test email sent to {test_recipient}")
    
    except Exception as e:
        print(f"❌ SMTP test failed: {str(e)}")
        raise typer.Exit(1)

@app.command()
def clear_sent_flags(
    csv_file: str = typer.Option(None, help="Path to CSV file containing email recipients"),
    config_file: str = typer.Option("config/config.yaml", "--config", "-c", help="Path to config file"),
    content_file: str = typer.Option("config/email.yaml", "--content", help="Path to email content file"),
):
    """
    Limpa as flags de 'enviado' e 'falhou' do arquivo CSV, permitindo o reenvio para todos os emails.
    """
    try:
        config = Config(config_file, content_file)
        csv_path = csv_file or config.email_config["csv_file"]
        csv_reader = CSVReader(csv_path)
        
        print("Clearing sent flags...")
        csv_reader.clear_sent_flags()
        print("✅ All flags cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing flags: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    app()