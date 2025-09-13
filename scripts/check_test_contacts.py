#!/usr/bin/env python3
"""
Script para verificar se há contatos de teste no banco de dados.
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

def check_test_contacts():
    """Verifica se há contatos de teste no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se há contatos com a tag 'test'
        cursor.execute("""
            SELECT tc.id, tc.email
            FROM tbl_contacts tc
            JOIN tbl_contact_tags ctt ON tc.id = ctt.contact_id
            JOIN tbl_tags t ON ctt.tag_id = t.id
            WHERE LOWER(TRIM(t.tag_name)) = 'test'
            LIMIT 10;
        """)
        
        test_contacts = cursor.fetchall()
        
        if test_contacts:
            print("✅ Há contatos de teste no banco de dados:")
            for contact in test_contacts:
                print(f"  ID: {contact[0]}, Email: {contact[1]}")
        else:
            print("❌ Não há contatos de teste no banco de dados.")
            
        # Verificar se há a tag 'test' na tabela tbl_tags
        cursor.execute("""
            SELECT id, tag_name FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'test';
        """)
        
        test_tag = cursor.fetchone()
        
        if test_tag:
            print(f"✅ Tag 'test' existe (ID: {test_tag[0]}, Nome: {test_tag[1]})")
        else:
            print("❌ Tag 'test' não existe na tabela tbl_tags.")
            
    except Exception as e:
        print(f"❌ Erro ao verificar contatos de teste: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal."""
    print("🔍 Verificando contatos de teste...")
    check_test_contacts()

if __name__ == "__main__":
    main()