#!/bin/bash

# ============================================================================
# Script para enviar emails em lote
# ============================================================================

set -e

cd /home/igormedeiros/projects/treineinsite/treineinsite

# Carregar variáveis de ambiente
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Menu
echo ""
echo "======================================================================="
echo "�� TREINEINSITE EMAIL SENDER - v2.0"
echo "======================================================================="
echo ""
echo "Opções:"
echo "  1) TESTE - Enviar apenas para igor.medeiros@gmail.com (tag 'Test')"
echo "  2) PRODUÇÃO - Enviar para TODOS os contatos elegíveis"
echo "  3) LIMPAR flags e depois TESTE"
echo "  4) LIMPAR flags e depois PRODUÇÃO"
echo ""
read -p "Escolha uma opção (1-4): " option

case $option in
    1)
        echo ""
        echo "📧 Enviando em MODO TESTE..."
        python3 << 'PYSCRIPT'
import sys
sys.path.insert(0, '/home/igormedeiros/projects/treineinsite/treineinsite/src')
from email_sender.config import Config
from email_sender.db import Database
from email_sender.smtp_manager import SmtpManager
from email_sender.email_service import EmailService

config = Config()
db = Database(config)
smtp = SmtpManager(config)
service = EmailService(config, db, smtp)

print("=" * 70)
print("📧 MODO TESTE - igor.medeiros@gmail.com")
print("=" * 70)
print()

result = service.send_batch(message_id=247, dry_run=False, is_test_mode=True)

print("\n" + "=" * 70)
print("✅ RESULTADO")
print("=" * 70)
print(f"Enviados: {result['sent']}")
print(f"Falhados: {result['failed']}")

if result['sent_emails']:
    print("\n✅ Emails enviados:")
    for item in result['sent_emails']:
        print(f"   → {item['email']}")
if result['failed_emails']:
    print("\n❌ Falhas:")
    for item in result['failed_emails']:
        print(f"   ✗ {item['email']}: {item['error']}")

print("\n" + "=" * 70)
PYSCRIPT
        ;;
    2)
        echo ""
        echo "📧 Enviando em MODO PRODUÇÃO..."
        python3 << 'PYSCRIPT'
import sys
sys.path.insert(0, '/home/igormedeiros/projects/treineinsite/treineinsite/src')
from email_sender.config import Config
from email_sender.db import Database
from email_sender.smtp_manager import SmtpManager
from email_sender.email_service import EmailService

config = Config()
db = Database(config)
smtp = SmtpManager(config)
service = EmailService(config, db, smtp)

print("=" * 70)
print("📧 MODO PRODUÇÃO - TODOS os contatos")
print("=" * 70)
print()

result = service.send_batch(message_id=247, dry_run=False, is_test_mode=False)

print("\n" + "=" * 70)
print("✅ RESULTADO")
print("=" * 70)
print(f"Enviados: {result['sent']}")
print(f"Falhados: {result['failed']}")
print(f"Total processado: {result['total_processed']}")

if result['sent'] > 0:
    print(f"\n✅ {result['sent']} emails enviados com sucesso!")
if result['failed'] > 0:
    print(f"\n❌ {result['failed']} emails falharam")

print("\n" + "=" * 70)
PYSCRIPT
        ;;
    3)
        echo ""
        echo "🧹 Limpando flags..."
        python3 << 'PYSCRIPT'
import psycopg, os
conn = psycopg.connect(
    host=os.getenv('PGHOST'),
    port=int(os.getenv('PGPORT', 5432)),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    dbname=os.getenv('PGDATABASE'),
    autocommit=True
)
with conn.cursor() as cur:
    cur.execute("DELETE FROM tbl_message_logs WHERE message_id = 247")
    print(f"✅ {cur.rowcount} registros de envio removidos")
    cur.execute("UPDATE tbl_messages SET processed = FALSE WHERE id = 247")
    print(f"✅ Mensagem marcada como não processada")
conn.close()
PYSCRIPT

        echo ""
        echo "📧 Enviando em MODO TESTE..."
        python3 << 'PYSCRIPT'
import sys
sys.path.insert(0, '/home/igormedeiros/projects/treineinsite/treineinsite/src')
from email_sender.config import Config
from email_sender.db import Database
from email_sender.smtp_manager import SmtpManager
from email_sender.email_service import EmailService

config = Config()
db = Database(config)
smtp = SmtpManager(config)
service = EmailService(config, db, smtp)

print("=" * 70)
print("📧 MODO TESTE - igor.medeiros@gmail.com")
print("=" * 70)
print()

result = service.send_batch(message_id=247, dry_run=False, is_test_mode=True)

print("\n" + "=" * 70)
print("✅ RESULTADO")
print("=" * 70)
print(f"Enviados: {result['sent']}")
if result['sent_emails']:
    for item in result['sent_emails']:
        print(f"   ✓ {item['email']}")
print("=" * 70)
PYSCRIPT
        ;;
    4)
        echo ""
        echo "🧹 Limpando flags..."
        python3 << 'PYSCRIPT'
import psycopg, os
conn = psycopg.connect(
    host=os.getenv('PGHOST'),
    port=int(os.getenv('PGPORT', 5432)),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    dbname=os.getenv('PGDATABASE'),
    autocommit=True
)
with conn.cursor() as cur:
    cur.execute("DELETE FROM tbl_message_logs WHERE message_id = 247")
    print(f"✅ {cur.rowcount} registros de envio removidos")
    cur.execute("UPDATE tbl_messages SET processed = FALSE WHERE id = 247")
    print(f"✅ Mensagem marcada como não processada")
conn.close()
PYSCRIPT

        echo ""
        echo "📧 Enviando em MODO PRODUÇÃO..."
        python3 << 'PYSCRIPT'
import sys
sys.path.insert(0, '/home/igormedeiros/projects/treineinsite/treineinsite/src')
from email_sender.config import Config
from email_sender.db import Database
from email_sender.smtp_manager import SmtpManager
from email_sender.email_service import EmailService

config = Config()
db = Database(config)
smtp = SmtpManager(config)
service = EmailService(config, db, smtp)

print("=" * 70)
print("📧 MODO PRODUÇÃO - TODOS os contatos")
print("=" * 70)
print()

result = service.send_batch(message_id=247, dry_run=False, is_test_mode=False)

print("\n" + "=" * 70)
print("✅ RESULTADO")
print("=" * 70)
print(f"Enviados: {result['sent']}")
print(f"Falhados: {result['failed']}")
print(f"Total processado: {result['total_processed']}")

if result['sent'] > 0:
    print(f"\n✅ {result['sent']} emails enviados com sucesso!")
print("=" * 70)
PYSCRIPT
        ;;
    *)
        echo "❌ Opção inválida"
        exit 1
        ;;
esac

echo ""
