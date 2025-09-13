#!/usr/bin/env python3
"""
Script para verificar se a tabela tbl_send_state foi criada corretamente.
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

def check_send_state_table():
    """Verifica se a tabela tbl_send_state existe e mostra sua estrutura."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'tbl_send_state'
            );
        """)
        
        exists = cursor.fetchone()[0]
        
        if exists:
            print("✅ Tabela tbl_send_state existe no banco de dados!")
            
            # Mostrar a estrutura da tabela
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'tbl_send_state'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            print("\nEstrutura da tabela tbl_send_state:")
            print("-" * 60)
            for column in columns:
                print(f"Coluna: {column[0]}")
                print(f"  Tipo: {column[1]}")
                print(f"  Permite NULL: {column[2]}")
                print(f"  Valor padrão: {column[3]}")
                print()
        else:
            print("❌ Tabela tbl_send_state NÃO existe no banco de dados!")
        
    except Exception as e:
        print(f"❌ Erro ao verificar a tabela tbl_send_state: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal para verificar a tabela."""
    print("🔍 Verificando a tabela tbl_send_state...")
    check_send_state_table()

if __name__ == "__main__":
    main()