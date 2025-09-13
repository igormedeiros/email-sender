#!/usr/bin/env python3
"""
Script para verificar o estado atual da tabela tbl_send_state e limpar se necessário.
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

def check_and_reset_send_state():
    """Verifica e reseta o estado de envio se necessário."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar o conteúdo da tabela tbl_send_state
        cursor.execute("SELECT * FROM tbl_send_state;")
        rows = cursor.fetchall()
        
        if rows:
            print("📊 Conteúdo atual da tabela tbl_send_state:")
            for row in rows:
                print(f"  state_key: {row[0]}, state_value: {row[1]}, updated_at: {row[2]}")
            
            # Perguntar se deseja limpar a tabela
            resposta = input("\nDeseja limpar a tabela tbl_send_state? (s/n): ")
            if resposta.lower() in ['s', 'sim', 'y', 'yes']:
                cursor.execute("DELETE FROM tbl_send_state;")
                conn.commit()
                print("✅ Tabela tbl_send_state limpa com sucesso!")
            else:
                print("ℹ️  Tabela tbl_send_state mantida como está.")
        else:
            print("✅ Tabela tbl_send_state está vazia.")
            
    except Exception as e:
        print(f"❌ Erro ao verificar/limpar a tabela tbl_send_state: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal."""
    print("🔍 Verificando o estado de envio...")
    check_and_reset_send_state()

if __name__ == "__main__":
    main()