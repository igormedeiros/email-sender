#!/usr/bin/env python3
"""
Script para verificar contatos marcados como problemáticos.
"""

import psycopg2
import os
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Obtém uma conexão com o banco de dados usando as variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', ''),
        database=os.getenv('PGDATABASE', 'treineinsite')
    )

def check_problematic_contacts():
    """Verifica contatos marcados como problemáticos."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar contatos com a tag 'problem'
        cursor.execute("""
            SELECT 
                tc.id,
                tc.email,
                ctt.assigned_at,
                COUNT(tml.id) as total_failures
            FROM tbl_contacts tc
            JOIN tbl_contact_tags ctt ON tc.id = ctt.contact_id
            JOIN tbl_tags t ON ctt.tag_id = t.id
            LEFT JOIN tbl_message_logs tml ON tc.id = tml.contact_id 
                AND tml.event_type = 'sent' 
                AND tml.status IN ('failed', 'timeout', 'error')
            WHERE LOWER(TRIM(t.tag_name)) = 'problem'
            GROUP BY tc.id, tc.email, ctt.assigned_at
            ORDER BY ctt.assigned_at DESC
        """)
        
        problematic_contacts = cursor.fetchall()
        
        if problematic_contacts:
            print("Contatos marcados como problemáticos:")
            print("=" * 60)
            for contact in problematic_contacts:
                contact_id, email, assigned_at, total_failures = contact
                print(f"ID: {contact_id}")
                print(f"Email: {email}")
                print(f"Marcado em: {assigned_at}")
                print(f"Total de falhas registradas: {total_failures}")
                print("-" * 40)
        else:
            print("Não há contatos marcados como problemáticos.")
            
        return len(problematic_contacts)
        
    except Exception as e:
        logger.error(f"Erro ao verificar contatos problemáticos: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()

def remove_problem_tag(contact_id):
    """
    Remove a tag 'problem' de um contato.
    
    Args:
        contact_id (int): ID do contato
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            DELETE FROM tbl_contact_tags 
            WHERE contact_id = %s 
            AND tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem' LIMIT 1)
        """, (contact_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Tag 'problem' removida do contato ID {contact_id}")
            return True
        else:
            logger.warning(f"Nenhuma tag 'problem' encontrada para o contato ID {contact_id}")
            return False
            
    except Exception as e:
        logger.error(f"Erro ao remover tag 'problem' do contato {contact_id}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal."""
    logger.info("Verificando contatos marcados como problemáticos...")
    
    count = check_problematic_contacts()
    
    if count > 0:
        print(f"\nTotal de contatos problemáticos: {count}")
        print("\nPara remover a tag 'problem' de um contato, use o comando:")
        print("python remove_problem_tag.py <contact_id>")
    else:
        print("\nNenhum contato problemático encontrado.")

if __name__ == "__main__":
    main()