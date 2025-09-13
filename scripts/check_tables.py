#!/usr/bin/env python3
"""
Script para verificar se as tabelas necessárias existem no banco de dados.
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

def check_required_tables():
    """Verifica se as tabelas necessárias existem no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se as tabelas existem
        required_tables = ['tbl_contacts', 'tbl_contact_tags', 'tbl_tags']
        
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table,))
            
            exists = cursor.fetchone()[0]
            
            if exists:
                print(f"✅ Tabela {table} existe no banco de dados!")
            else:
                print(f"❌ Tabela {table} NÃO existe no banco de dados!")
        
        # Verificar se a tabela tbl_send_state existe (já criamos anteriormente)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tbl_send_state'
            );
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✅ Tabela tbl_send_state existe no banco de dados!")
        else:
            print("❌ Tabela tbl_send_state NÃO existe no banco de dados!")
            
    except Exception as e:
        print(f"❌ Erro ao verificar as tabelas: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal para verificar as tabelas."""
    print("🔍 Verificando as tabelas necessárias...")
    check_required_tables()

if __name__ == "__main__":
    main()