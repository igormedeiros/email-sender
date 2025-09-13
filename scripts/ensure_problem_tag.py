#!/usr/bin/env python3
"""
Script para garantir que a tag 'problem' exista no banco de dados.
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

def ensure_problem_tag_exists():
    """Garante que a tag 'problem' exista no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se a tag 'problem' já existe
        cursor.execute("""
            SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem';
        """)
        
        existing_tag = cursor.fetchone()
        
        if existing_tag:
            print(f"✅ Tag 'problem' já existe (ID: {existing_tag[0]})")
        else:
            # Criar a tag 'problem'
            cursor.execute("""
                INSERT INTO tbl_tags (tag_name) VALUES ('Problem');
            """)
            conn.commit()
            print("✅ Tag 'problem' criada com sucesso!")
            
        # Verificar novamente para confirmar
        cursor.execute("""
            SELECT id, tag_name FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem';
        """)
        
        tag = cursor.fetchone()
        print(f"ℹ️  Tag 'problem' atual: ID={tag[0]}, Nome='{tag[1]}'")
        
    except Exception as e:
        print(f"❌ Erro ao garantir que a tag 'problem' exista: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal."""
    print("🔍 Garantindo que a tag 'problem' exista...")
    ensure_problem_tag_exists()

if __name__ == "__main__":
    main()