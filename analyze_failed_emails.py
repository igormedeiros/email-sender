#!/usr/bin/env python3
"""
Script para analisar relatórios de envio e gerar listas de emails que devem ser marcados com a tag 'problem'.
"""

import psycopg2
import os
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    \"\"\"Obtém uma conexão com o banco de dados usando as variáveis de ambiente.\"\"\"
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', ''),
        database=os.getenv('PGDATABASE', 'treineinsite')
    )

def analyze_failed_emails(days_back=7, min_failures=2):
    \"\"\"
    Analisa os relatórios de envio para identificar emails com falhas repetidas.
    
    Args:
        days_back (int): Número de dias para analisar (padrão: 7)
        min_failures (int): Número mínimo de falhas para considerar um email problemático (padrão: 2)
    
    Returns:
        list: Lista de emails identificados como problemáticos
    \"\"\"
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Calcular a data limite para análise
        date_limit = datetime.now() - timedelta(days=days_back)
        
        # Buscar emails com falhas repetidas nos últimos X dias
        cursor.execute(\"\"\"
            SELECT 
                tc.email,
                COUNT(tml.id) as failure_count,
                STRING_AGG(tml.status, '; ') as failure_statuses,
                MAX(tml.event_timestamp) as last_failure
            FROM tbl_message_logs tml
            JOIN tbl_contacts tc ON tml.contact_id = tc.id
            WHERE tml.event_type = 'sent'
              AND tml.status IN ('failed', 'timeout', 'error')
              AND tml.event_timestamp >= %s
            GROUP BY tc.email, tc.id
            HAVING COUNT(tml.id) >= %s
            ORDER BY failure_count DESC, last_failure DESC
        \"\"\", (date_limit, min_failures))
        
        problematic_emails = cursor.fetchall()
        
        logger.info(f\"Encontrados {len(problematic_emails)} emails com {min_failures} ou mais falhas nos últimos {days_back} dias\")
        
        return problematic_emails
        
    except Exception as e:
        logger.error(f\"Erro ao analisar emails com falhas: {e}\")
        return []
    finally:
        cursor.close()
        conn.close()

def mark_problematic_emails(emails_list):
    \"\"\"
    Marca os emails identificados como problemáticos com a tag 'problem'.
    
    Args:
        emails_list (list): Lista de emails a serem marcados
    \"\"\"
    if not emails_list:
        logger.info(\"Nenhum email para marcar como problemático\")
        return
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        marked_count = 0
        
        for email_data in emails_list:
            email = email_data[0]
            
            # Marcar o contato com a tag 'problem'
            cursor.execute(\"\"\"
                INSERT INTO tbl_contact_tags (contact_id, tag_id, assigned_at)
                SELECT 
                    tc.id,
                    (SELECT id FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem' LIMIT 1),
                    NOW()
                FROM tbl_contacts tc
                WHERE LOWER(TRIM(tc.email)) = LOWER(TRIM(%s))
                  AND EXISTS (SELECT 1 FROM tbl_tags WHERE LOWER(TRIM(tag_name)) = 'problem')
                ON CONFLICT (contact_id, tag_id) DO NOTHING
            \"\"\", (email,))
            
            if cursor.rowcount > 0:
                marked_count += 1
                logger.info(f\"Marcado email como problemático: {email}\")
        
        conn.commit()
        logger.info(f\"Marcados {marked_count} emails como problemáticos\")
        
    except Exception as e:
        logger.error(f\"Erro ao marcar emails como problemáticos: {e}\")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def generate_problematic_emails_report(emails_list, output_file=None):
    \"\"\"
    Gera um relatório dos emails identificados como problemáticos.
    
    Args:
        emails_list (list): Lista de emails problemáticos
        output_file (str): Caminho do arquivo de saída (opcional)
    \"\"\"
    if not emails_list:
        report_content = \"Não foram encontrados emails com falhas repetidas.\\n\"
    else:
        report_content = f\"Relatório de Emails Problemáticos\\n\"
        report_content += f\"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\\n\"
        report_content += f\"Total de emails identificados: {len(emails_list)}\\n\"
        report_content += \"=\" * 50 + \"\\n\\n\"
        
        for i, email_data in enumerate(emails_list, 1):
            email, failure_count, failure_statuses, last_failure = email_data
            report_content += f\"{i}. Email: {email}\\n\"
            report_content += f\"   Falhas: {failure_count}\\n\"
            report_content += f\"   Status: {failure_statuses}\\n\"
            report_content += f\"   Última falha: {last_failure}\\n\"
            report_content += \"-\" * 30 + \"\\n\"
    
    # Exibir no console
    print(report_content)
    
    # Salvar em arquivo se especificado
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f\"Relatório salvo em: {output_file}\")
        except Exception as e:
            logger.error(f\"Erro ao salvar relatório: {e}\")

def main():
    \"\"\"Função principal.\"\"\"
    logger.info(\"Iniciando análise de relatórios de envio...\")
    
    # Analisar emails com falhas repetidas
    problematic_emails = analyze_failed_emails(days_back=7, min_failures=2)
    
    # Gerar relatório
    report_file = f\"reports/problematic_emails_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt\"
    generate_problematic_emails_report(problematic_emails, report_file)
    
    # Marcar emails como problemáticos (opcional - pode ser feito manualmente)
    # mark_problematic_emails(problematic_emails)
    
    logger.info(\"Análise concluída!\")

if __name__ == \"__main__\":
    main()