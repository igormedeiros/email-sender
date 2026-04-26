#!/usr/bin/env python3
"""
Script de importação inteligente de contatos para o Email Sender.
- Valida emails
- Verifica duplicatas no banco
- Insere como contatos válidos (elegíveis para envio)
- Gera relatório detalhado

Uso:
    python scripts/import_contacts_smart.py <arquivo.csv> [--mode prod|test]

Arquivo CSV deve ter coluna 'email':
    email
    contact1@example.com
    contact2@example.com
"""

import sys
import csv
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import psycopg
from psycopg.rows import dict_row

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
log = logging.getLogger(__name__)

# Regex para validar email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'


class ContactImporter:
    """Importador inteligente de contatos."""
    
    def __init__(self, db_host: str, db_port: int, db_user: str, db_password: str, db_name: str):
        """Inicializa conexão com banco."""
        self.conn_params = {
            'host': db_host,
            'port': db_port,
            'user': db_user,
            'password': db_password,
            'dbname': db_name,
        }
        self.conn = None
        self.stats = {
            'read': 0,
            'valid': 0,
            'duplicates': 0,
            'invalid': 0,
            'inserted': 0,
            'errors': [],
        }
    
    def connect(self):
        """Conecta ao banco de dados."""
        try:
            self.conn = psycopg.connect(**self.conn_params)
            log.info(f"✅ Conectado ao banco: {self.conn_params['dbname']}")
        except Exception as e:
            log.error(f"❌ Erro ao conectar: {e}")
            sys.exit(1)
    
    def close(self):
        """Fecha conexão."""
        if self.conn:
            self.conn.close()
            log.info("✅ Conexão fechada")
    
    def validate_email(self, email: str) -> bool:
        """Valida formato de email."""
        if not email:
            return False
        email = email.strip().lower()
        return bool(re.match(EMAIL_REGEX, email))
    
    def email_exists(self, email: str) -> bool:
        """Verifica se email já existe no banco."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM tbl_contacts WHERE LOWER(TRIM(email)) = %s LIMIT 1",
                    (email.strip().lower(),)
                )
                return cur.fetchone() is not None
        except Exception as e:
            log.error(f"❌ Erro ao verificar email {email}: {e}")
            return False
    
    def read_csv(self, csv_path: str) -> List[str]:
        """Lê emails do CSV."""
        emails = []
        path = Path(csv_path)
        
        if not path.exists():
            log.error(f"❌ Arquivo não encontrado: {csv_path}")
            sys.exit(1)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_idx, row in enumerate(reader, start=2):
                    email = row.get('email', '').strip().lower()
                    self.stats['read'] += 1
                    
                    if not email:
                        log.warning(f"  Linha {row_idx}: Email vazio")
                        continue
                    
                    if not self.validate_email(email):
                        log.warning(f"  Linha {row_idx}: Email inválido: {email}")
                        self.stats['invalid'] += 1
                        self.stats['errors'].append(f"Linha {row_idx}: Email inválido ({email})")
                        continue
                    
                    self.stats['valid'] += 1
                    emails.append(email)
            
            log.info(f"✅ Lidos {self.stats['read']} emails do arquivo")
            log.info(f"   ✓ Válidos: {self.stats['valid']}")
            log.info(f"   ✗ Inválidos: {self.stats['invalid']}")
            
        except Exception as e:
            log.error(f"❌ Erro ao ler CSV: {e}")
            sys.exit(1)
        
        return emails
    
    def check_duplicates(self, emails: List[str]) -> Tuple[List[str], int]:
        """Filtra emails que não existem no banco."""
        new_emails = []
        duplicates = 0
        
        log.info(f"\n📋 Verificando duplicatas no banco...")
        
        for email in emails:
            if self.email_exists(email):
                log.warning(f"  ⚠️  Já existe: {email}")
                duplicates += 1
                self.stats['duplicates'] += 1
            else:
                new_emails.append(email)
        
        log.info(f"✅ Verificação concluída")
        log.info(f"   ✓ Novos: {len(new_emails)}")
        log.info(f"   ⚠️  Duplicados: {duplicates}")
        
        return new_emails, duplicates
    
    def insert_contacts(self, emails: List[str]) -> int:
        """Insere contatos como válidos (elegíveis para envio)."""
        if not emails:
            log.warning("Nenhum contato para inserir")
            return 0
        
        log.info(f"\n📧 Inserindo {len(emails)} novos contatos como VÁLIDOS...")
        
        inserted = 0
        
        try:
            with self.conn.cursor() as cur:
                for email in emails:
                    try:
                        # Inserir como contato válido (válido para envio)
                        # is_buyer=FALSE (pode receber emails)
                        # unsubscribed=FALSE (não está descadastrado)
                        cur.execute(
                            """
                            INSERT INTO tbl_contacts 
                            (email, unsubscribed, is_buyer) 
                            VALUES (%s, FALSE, FALSE)
                            ON CONFLICT (email) DO NOTHING
                            RETURNING id
                            """,
                            (email,)
                        )
                        
                        result = cur.fetchone()
                        if result:
                            contact_id = result[0]
                            log.info(f"  ✓ Inserido: {email} (id={contact_id})")
                            inserted += 1
                        else:
                            log.debug(f"  ℹ️  Já existia: {email}")
                    
                    except Exception as e:
                        log.error(f"  ❌ Erro ao inserir {email}: {e}")
                        self.stats['errors'].append(f"Erro ao inserir {email}: {str(e)}")
                
                self.conn.commit()
                self.stats['inserted'] = inserted
                log.info(f"\n✅ Inseridos {inserted} contatos com sucesso")
                
        except Exception as e:
            self.conn.rollback()
            log.error(f"❌ Erro ao inserir: {e}")
            sys.exit(1)
        
        return inserted
    
    def verify_inserted_contacts(self, emails: List[str]):
        """Verifica se contatos foram de fato inseridos."""
        log.info(f"\n✔️  Verificando contatos inseridos...")
        
        try:
            with self.conn.cursor(row_factory=dict_row) as cur:
                for email in emails:
                    cur.execute(
                        """
                        SELECT 
                            id,
                            email,
                            unsubscribed,
                            is_buyer,
                            created_at,
                            (SELECT array_agg(tg.tag_name) 
                             FROM tbl_contact_tags ctg
                             JOIN tbl_tags tg ON ctg.tag_id = tg.id
                             WHERE ctg.contact_id = tbl_contacts.id) as tags
                        FROM tbl_contacts 
                        WHERE LOWER(TRIM(email)) = %s
                        """,
                        (email.lower(),)
                    )
                    
                    contact = cur.fetchone()
                    if contact:
                        log.info(f"  ✓ {contact['email']}")
                        log.debug(f"      ID: {contact['id']}")
                        log.debug(f"      Unsubscribed: {contact['unsubscribed']}")
                        log.debug(f"      Is Buyer: {contact['is_buyer']}")
                        log.debug(f"      Tags: {contact['tags'] or '(nenhuma)'}")
        
        except Exception as e:
            log.warning(f"⚠️  Erro ao verificar contatos: {e}")
    
    def print_summary(self):
        """Imprime relatório final."""
        log.info("\n" + "="*70)
        log.info("📊 RELATÓRIO DE IMPORTAÇÃO")
        log.info("="*70)
        log.info(f"  Total lido:        {self.stats['read']}")
        log.info(f"  Válidos:           {self.stats['valid']}")
        log.info(f"  Inválidos:         {self.stats['invalid']}")
        log.info(f"  Duplicados (BD):   {self.stats['duplicates']}")
        log.info(f"  Inseridos:         {self.stats['inserted']}")
        
        if self.stats['errors']:
            log.info(f"\n  ⚠️  Erros encontrados ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:10]:
                log.error(f"     - {error}")
            if len(self.stats['errors']) > 10:
                log.error(f"     ... e mais {len(self.stats['errors']) - 10}")
        
        log.info("="*70 + "\n")
    
    def run(self, csv_path: str):
        """Executa o fluxo completo."""
        try:
            self.connect()
            
            # 1. Ler e validar emails
            emails = self.read_csv(csv_path)
            
            if not emails:
                log.warning("Nenhum email válido para processar")
                self.print_summary()
                return
            
            # 2. Verificar duplicatas
            new_emails, duplicates = self.check_duplicates(emails)
            
            if not new_emails:
                log.warning("Todos os emails já existem no banco")
                self.print_summary()
                return
            
            # 3. Inserir contatos
            self.insert_contacts(new_emails)
            
            # 4. Verificar
            self.verify_inserted_contacts(new_emails)
            
            # 5. Relatório
            self.print_summary()
            
        finally:
            self.close()


def main():
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: python scripts/import_contacts_smart.py <arquivo.csv>")
        print("\nExemplo:")
        print("  python scripts/import_contacts_smart.py contacts.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    
    # Ler credenciais do .env
    from pathlib import Path
    import os
    
    env_file = Path(".env")
    if not env_file.exists():
        log.error("❌ Arquivo .env não encontrado")
        sys.exit(1)
    
    # Carregar .env manualmente
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    db_host = env_vars.get('PGHOST', 'localhost')
    db_port = int(env_vars.get('PGPORT', 5432))
    db_user = env_vars.get('PGUSER', 'postgres')
    db_password = env_vars.get('PGPASSWORD', '')
    db_name = env_vars.get('PGDATABASE', 'treineinsite')
    
    log.info(f"📍 Conectando ao banco: {db_user}@{db_host}:{db_port}/{db_name}")
    
    importer = ContactImporter(db_host, db_port, db_user, db_password, db_name)
    importer.run(csv_path)


if __name__ == '__main__':
    main()
