#!/usr/bin/env python3
"""
Script para verificar um contato no banco de dados.
"""

import psycopg2
import os
import argparse

def get_db_connection():
    """Obtém uma conexão com o banco de dados usando as variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', ''),
        database=os.getenv('PGDATABASE', 'treineinsite')
    )

def check_contact(email):
    """Verifica o status de um contato no banco de dados."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar o contato pelo email
        cursor.execute("SELECT id, email, unsubscribed, is_buyer FROM tbl_contacts WHERE email = %s;", (email,))
        contact = cursor.fetchone()
        
        if not contact:
            print(f"❌ Contato com email '{email}' não encontrado.")
            return

        contact_id, email, unsubscribed, is_buyer = contact
        print(f"✅ Contato encontrado:")
        print(f"  ID: {contact_id}")
        print(f"  Email: {email}")
        print(f"  Unsubscribed: {unsubscribed}")
        print(f"  Is Buyer: {is_buyer}")

        # Buscar as tags do contato
        cursor.execute("""
            SELECT t.tag_name 
            FROM tbl_contact_tags ct
            JOIN tbl_tags t ON ct.tag_id = t.id
            WHERE ct.contact_id = %s;
        """, (contact_id,))
        
        tags = cursor.fetchall()
        
        if tags:
            print("  Tags:")
            for tag in tags:
                print(f"    - '{tag[0]}'")
        else:
            print("  Tags: Nenhuma tag associada.")

    except Exception as e:
        print(f"❌ Erro ao verificar o contato: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal para verificar o contato."""
    parser = argparse.ArgumentParser(description='Verificar um contato no banco de dados.')
    parser.add_argument('email', type=str, help='O email do contato a ser verificado.')
    args = parser.parse_args()
    
    print(f"🔍 Verificando o contato com email '{args.email}'...")
    check_contact(args.email)

if __name__ == "__main__":
    main()
