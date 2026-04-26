import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, 'src')
from email_sender.config import Config
from email_sender.db import Database
from email_sender.smtp_manager import SmtpManager

def export_csv(db: Database, message_id: int, is_test: bool, csv_path: str):
    print("=" * 60)
    print("📥 EXPORTANDO CONTATOS DO BANCO DE DADOS PARA CSV")
    print("=" * 60)
    db.connect()
    try:
        query_path = "sql/contacts/select_recipients_for_message.sql"
        contacts = db.fetch_all(query_path, [is_test, message_id])
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'email'])
            for c in contacts:
                writer.writerow([c['id'], c['email']])
        print(f"✅ {len(contacts)} contatos exportados com sucesso para o arquivo '{csv_path}'!\n")
        return len(contacts)
    except Exception as e:
        print(f"❌ Erro ao exportar para CSV: {e}")
        raise
    finally:
        db.close()

def load_sent_emails(log_file: str) -> set:
    sent = set()
    path = Path(log_file)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    sent.add(line.strip())
    return sent

def append_sent_email(log_file: str, email: str):
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{email}\n")

def send_from_csv(csv_path: str, log_file: str):
    print("=" * 60)
    print("🚀 INICIANDO ENVIO DE EMAILS A PARTIR DO CSV")
    print("=" * 60)
    
    config = Config()
    smtp = SmtpManager(config)
    
    # Prepara conteudo da mensagem
    content_config = config.content_config
    message_subject = content_config.get('email', {}).get('subject', 'Sem assunto')
    
    print(f"Assunto da mensagem: '{message_subject}'")
    
    template_path = config.email_config.get('template_path', 'config/templates/email.html')
    message_html = Path(template_path).read_text(encoding='utf-8')
    
    evento = content_config.get('evento', {})
    promocao = content_config.get('promocao', {})
    
    message_html = message_html.replace('{data_evento}', evento.get('data', ''))
    message_html = message_html.replace('{cidade}', evento.get('cidade', ''))
    message_html = message_html.replace('{link_evento}', evento.get('link', ''))
    message_html = message_html.replace('{uf}', evento.get('uf', ''))
    message_html = message_html.replace('{local}', evento.get('local', ''))
    message_html = message_html.replace('{horario}', evento.get('horario', ''))
    
    desconto = promocao.get('desconto', '')
    if desconto:
        desconto_para = f"<p><strong>🎉 DESCONTO ESPECIAL: {desconto} OFF!</strong> Use o cupom <strong>{evento.get('cupom', '')}</strong> para garantir esse preço exclusivo.</p>"
    else:
        desconto_para = ""
    message_html = message_html.replace('{desconto_paragrafo}', desconto_para)
    message_html = message_html.replace('{unsubscribe_full}', 'https://treineinsite.com.br/descadastro')
    message_html = message_html.replace('{unsubscribe_safe_url}', 'https://treineinsite.com.br/descadastro')

    sent_emails = load_sent_emails(log_file)
    print(f"Lidos {len(sent_emails)} emails do histórico '{log_file}' (já enviados).")

    contacts = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            contacts.append(row)

    to_send = [c for c in contacts if c['email'] not in sent_emails]
    print(f"Restam {len(to_send)} contatos para enviar nesta sessão.\n")

    if not to_send:
        print("🎉 Todos os emails já foram enviados! Nada a fazer.")
        return

    # Forçando batch pequeno e delay seguro pelo histórico de timeouts
    batch_size = config.email_config.get('batch_size', 50) 
    batch_delay = config.email_config.get('batch_delay', 10)

    print(f"Tentando conectar ao SMTP...")
    smtp.connect()
    print(f"✅ SMTP conectado e pronto.\n")
    
    sent_count = 0
    err_count = 0

    try:
        for i, contact in enumerate(to_send):
            email = contact['email']
            print(f"[{i+1}/{len(to_send)}] Enviando para: {email} ", end="")
            sys.stdout.flush()
            
            try:
                smtp.send_email(
                    to_email=email,
                    subject=message_subject,
                    content=message_html,
                    is_html=True
                )
                append_sent_email(log_file, email)
                sent_count += 1
                print("✓ Sucesso!")
                
                # Se for final de batch, dorme um pouco para desafogar o servior SMTP da Locaweb
                if (i + 1) % batch_size == 0 and (i + 1) < len(to_send):
                    print(f"\n[LOTE DE {batch_size} ATINGIDO] Desconectando SMTP e esperando {batch_delay}s...")
                    smtp.disconnect()
                    time.sleep(batch_delay)
                    print(f"Reconectando SMTP...")
                    smtp.connect()
                    print("✅ Reconectado!")
                    
            except Exception as e:
                print(f"❌ Falha: {e}")
                err_count += 1
                
                # Se SMTP desconectou ou deu erro severo, tenta limpar a conexao pro proximo
                if not smtp.smtp_connection:
                    print(f"Atenção: SMTP desconectado. Aguardando 5s para tentar novamente...")
                    time.sleep(5)
                    try:
                        smtp.connect()
                        print("✅ Reconectado com sucesso.")
                    except:
                        print("⚠️ Erro ao reconectar o SMTP.")
                
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário!")
    finally:
        smtp.disconnect()
        print("\n" + "=" * 60)
        print(f"✅ RESUMO: {sent_count} emails enviados com sucesso, {err_count} com erros nesta sessão.")
        print("=" * 60)

if __name__ == '__main__':
    MESSAGE_ID = 247
    CSV_PATH = 'contatos_producao.csv'
    LOG_FILE = 'csv_sent_emails_log.txt'
    
    # 1. Exportar contatos atualizados
    config = Config()
    db = Database(config)
    export_csv(db, MESSAGE_ID, False, CSV_PATH)
    
    # 2. Iniciar / Continuar o envio
    send_from_csv(CSV_PATH, LOG_FILE)
