#!/usr/bin/env python3
"""
Script para inicializar o banco de dados com as tabelas necessárias.
"""

import psycopg2
import os
from pathlib import Path

def get_db_connection():
    """Obtém uma conexão com o banco de dados usando as variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', ''),
        database=os.getenv('PGDATABASE', 'treineinsite')
    )

def create_send_state_table():
    """Cria a tabela tbl_send_state se ela não existir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Criar a tabela tbl_send_state
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tbl_send_state (
            state_key text PRIMARY KEY,
            state_value text,
            updated_at timestamptz DEFAULT now()
        );
        """
        
        cursor.execute(create_table_query)
        conn.commit()
        print("✅ Tabela tbl_send_state criada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar a tabela tbl_send_state: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal para inicializar o banco de dados."""
    print("🚀 Inicializando o banco de dados...")
    
    # Criar a tabela tbl_send_state
    create_send_state_table()
    
    print("✅ Banco de dados inicializado com sucesso!")

if __name__ == "__main__":
    main()