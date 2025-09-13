#!/usr/bin/env python3
"""
Script para verificar contatos com a tag 'problem'.
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

def check_problem_contacts():
    """Verifica contatos com a tag 'problem'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar contatos com a tag 'problem'
        cursor.execute("""
            SELECT tc.id, tc.email, ctt.assigned_at
            FROM tbl_contacts tc
            JOIN tbl_contact_tags ctt ON tc.id = ctt.contact_id
            JOIN tbl_tags t ON ctt.tag_id = t.id
            WHERE LOWER(TRIM(t.tag_name)) = 'problem'
            ORDER BY ctt.assigned_at DESC
            LIMIT 10;
        """)
        
        problem_contacts = cursor.fetchall()
        
        if problem_contacts:
            print("✅ Contatos com a tag 'problem':")
            for contact in problem_contacts:
                print(f"  ID: {contact[0]}, Email: {contact[1]}, Marcado em: {contact[2]}")
        else:
            print("ℹ️  Não há contatos com a tag 'problem'.")
            
    except Exception as e:
        print(f"❌ Erro ao verificar contatos com a tag 'problem': {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal."""
    print("🔍 Verificando contatos com a tag 'problem'...")
    check_problem_contacts()

if __name__ == "__main__":
    main()