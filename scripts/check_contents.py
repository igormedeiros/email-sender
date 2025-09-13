#!/usr/bin/env python3
"""
Script para verificar o conteúdo das tabelas necessárias.
"""

import psycopg2
import os

def get_db_connection():
    """Obtém uma conexão com o banco de dados usando as variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', ''),
        database=os.getenv('PGDATABASE', 'treineinsite')
    )

def check_table_contents():
    """Verifica o conteúdo das tabelas necessárias."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar conteúdo da tabela tbl_contacts
        cursor.execute("SELECT COUNT(*) FROM tbl_contacts;")
        count = cursor.fetchone()[0]
        print(f"📊 Tabela tbl_contacts tem {count} registros")
        
        # Verificar conteúdo da tabela tbl_tags
        cursor.execute("SELECT COUNT(*) FROM tbl_tags;")
        count = cursor.fetchone()[0]
        print(f"📊 Tabela tbl_tags tem {count} registros")
        
        # Verificar conteúdo da tabela tbl_contact_tags
        cursor.execute("SELECT COUNT(*) FROM tbl_contact_tags;")
        count = cursor.fetchone()[0]
        print(f"📊 Tabela tbl_contact_tags tem {count} registros")
        
        # Verificar conteúdo da tabela tbl_send_state
        cursor.execute("SELECT COUNT(*) FROM tbl_send_state;")
        count = cursor.fetchone()[0]
        print(f"📊 Tabela tbl_send_state tem {count} registros")
        
        # Verificar se há contatos elegíveis para envio
        cursor.execute("""
            SELECT COUNT(*) 
            FROM tbl_contacts tc
            WHERE tc.email IS NOT NULL AND tc.email <> ''
              AND COALESCE(tc.unsubscribed, FALSE) = FALSE
              AND NOT EXISTS (
                SELECT 1
                FROM tbl_contact_tags ctu
                JOIN tbl_tags tu ON ctu.tag_id = tu.id
                WHERE ctu.contact_id = tc.id AND LOWER(TRIM(tu.tag_name)) = 'unsubscribed'
              )
              AND NOT EXISTS (
                SELECT 1
                FROM tbl_contact_tags ctb
                JOIN tbl_tags t ON ctb.tag_id = t.id
                WHERE ctb.contact_id = tc.id AND LOWER(TRIM(t.tag_name)) IN ('bounce','bouncy')
              );
        """)
        count = cursor.fetchone()[0]
        print(f"📊 Há {count} contatos elegíveis para envio")
        
    except Exception as e:
        print(f"❌ Erro ao verificar o conteúdo das tabelas: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal para verificar o conteúdo das tabelas."""
    print("🔍 Verificando o conteúdo das tabelas...")
    check_table_contents()

if __name__ == "__main__":
    main()