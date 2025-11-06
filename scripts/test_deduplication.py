#!/usr/bin/env python3
"""
Script de teste para validar que nenhum contato recebe email duplicado.
Simula cenários de multiplicação de linhas e verifica proteções.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.email_sender.config import Config
from src.email_sender.db import Database
from src.email_sender.email_service import EmailService
from datetime import datetime

def test_database_integrity():
    """Teste 1: Verificar integridade do banco de dados"""
    print("\n" + "="*80)
    print("🧪 TESTE 1: Integridade do Banco de Dados")
    print("="*80)
    
    config = Config()
    with Database(config) as db:
        # Verificar duplicatas no send_logs
        result = db.fetch_one("""
            SELECT 
                (SELECT COUNT(*) FROM tbl_message_logs WHERE event_type = 'sent') as total_logs,
                (SELECT COUNT(DISTINCT (contact_id, message_id)) FROM tbl_message_logs WHERE event_type = 'sent') as unique_pairs,
                CASE 
                    WHEN (SELECT COUNT(*) FROM tbl_message_logs WHERE event_type = 'sent') = 
                         (SELECT COUNT(DISTINCT (contact_id, message_id)) FROM tbl_message_logs WHERE event_type = 'sent')
                    THEN TRUE
                    ELSE FALSE
                END as no_duplicates
        """)
        
        print(f"Total de logs de envio: {result['total_logs']}")
        print(f"Pares únicos (contato, mensagem): {result['unique_pairs']}")
        print(f"Status: {'✅ OK - Sem duplicatas' if result['no_duplicates'] else '❌ ERRO - Duplicatas detectadas!'}")
        
        return result['no_duplicates']

def test_query_deduplication():
    """Teste 2: Verificar se query de seleção de recipientes retorna valores únicos"""
    print("\n" + "="*80)
    print("🧪 TESTE 2: Query de Seleção de Recipientes")
    print("="*80)
    
    config = Config()
    with Database(config) as db:
        # Buscar última mensagem não processada
        msg = db.fetch_one("SELECT id FROM tbl_messages WHERE processed = FALSE ORDER BY id DESC LIMIT 1")
        
        if not msg:
            print("⚠️ Nenhuma mensagem não processada encontrada")
            return None
        
        message_id = msg['id']
        
        # Executar query de seleção com a nova versão otimizada
        recipients = db.fetch_all(
            "sql/contacts/select_recipients_for_message_dedup.sql",
            (False, message_id)  # is_test_mode=False
        )
        
        # Verificar duplicatas na query
        emails = [r['email'] for r in recipients]
        ids = [r['id'] for r in recipients]
        
        unique_emails = len(set(emails))
        unique_ids = len(set(ids))
        total = len(recipients)
        
        print(f"Mensagem ID: {message_id}")
        print(f"Total de recipientes: {total}")
        print(f"Emails únicos: {unique_emails}")
        print(f"IDs únicos: {unique_ids}")
        
        if total == unique_emails == unique_ids:
            print(f"✅ OK - Todos os recipientes são únicos!")
            return True
        else:
            print(f"❌ ERRO - Encontradas duplicatas na query!")
            print(f"   Diferença: {total - unique_emails} duplicatas de email")
            return False

def test_deduplication_logic():
    """Teste 3: Verificar lógica de deduplicação em memória"""
    print("\n" + "="*80)
    print("🧪 TESTE 3: Lógica de Deduplicação em Memória")
    print("="*80)
    
    config = Config()
    service = EmailService(config)
    
    # Simular envios
    test_recipients = [
        {'id': 1, 'email': 'test1@example.com'},
        {'id': 2, 'email': 'test2@example.com'},
        {'id': 1, 'email': 'test1@example.com'},  # Duplicata
        {'id': 3, 'email': 'test3@example.com'},
    ]
    
    processed = []
    duplicate_detected = 0
    
    print(f"Simulando processamento de {len(test_recipients)} recipientes...")
    
    for recipient in test_recipients:
        recipient_id = recipient['id']
        
        # Simular verificação em memória
        with service._state_lock:
            if recipient_id in service._sent_contacts:
                print(f"  ⚠️  Duplicata detectada: {recipient['email']}")
                duplicate_detected += 1
                continue
            
            service._sent_contacts.add(recipient_id)
            processed.append(recipient)
    
    print(f"\nResultado:")
    print(f"  Recipientes processados: {len(processed)}")
    print(f"  Duplicatas detectadas: {duplicate_detected}")
    print(f"  Status: {'✅ OK' if duplicate_detected == 1 else '❌ ERRO'}")
    
    return duplicate_detected == 1

def generate_test_report():
    """Gerar relatório completo de testes"""
    print("\n\n" + "="*80)
    print("📊 RELATÓRIO DE TESTES DE DEDUPLICAÇÃO")
    print("="*80)
    print(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    tests = [
        ("Integridade BD", test_database_integrity),
        ("Query Recipientes", test_query_deduplication),
        ("Lógica Memória", test_deduplication_logic),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERRO ao executar {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "="*80)
    print("📈 RESUMO FINAL")
    print("="*80)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result is True else ("❌ FALHOU" if result is False else "⚠️  INCONCLUSIVO")
        print(f"{test_name:.<40} {status}")
    
    print("="*80)
    print(f"Total: {passed} passou, {failed} falhou")
    print("="*80)
    
    return passed == len(tests)

if __name__ == "__main__":
    success = generate_test_report()
    sys.exit(0 if success else 1)
