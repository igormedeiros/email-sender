#!/usr/bin/env python3
"""
Script para remover a tag 'problem' de um contato.
"""

import psycopg2
import os
import sys
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

def remove_problem_tag(contact_id):
    """
    Remove a tag 'problem' de um contato.
    
    Args:
        contact_id (int): ID do contato
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se o contato existe
        cursor.execute("SELECT email FROM tbl_contacts WHERE id = %s", (contact_id,))
        contact = cursor.fetchone()
        
        if not contact:
            logger.error(f"Contato com ID {contact_id} não encontrado")
            return False
            
        email = contact[0]
        logger.info(f"Removendo tag 'problem' do contato {contact_id} ({email})")
        
        # Remover a tag 'problem'
        cursor.execute("""
            DELETE FROM tbl_contact_tags 
            WHERE contact_id = %s 
            AND tag_id = (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem' LIMIT 1)
        """, (contact_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Tag 'problem' removida com sucesso do contato {contact_id} ({email})")
            return True
        else:
            logger.warning(f"Nenhuma tag 'problem' encontrada para o contato {contact_id} ({email})")
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
    if len(sys.argv) != 2:
        print("Uso: python remove_problem_tag.py <contact_id>")
        print("Exemplo: python remove_problem_tag.py 12345")
        sys.exit(1)
    
    try:
        contact_id = int(sys.argv[1])
    except ValueError:
        logger.error("ID do contato deve ser um número inteiro")
        sys.exit(1)
    
    success = remove_problem_tag(contact_id)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()