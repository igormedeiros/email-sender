#!/usr/bin/env python3
"""
Script para remover duplicatas de emails no banco de dados.
Mantém apenas o registro mais antigo (ID menor) de cada email.
"""
import logging
from pathlib import Path
from src.email_sender.config import Config
from src.email_sender.db import Database

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def remove_duplicate_contacts():
    """Remove contatos duplicados mantendo apenas o primeiro (ID menor)."""
    config = Config()
    
    with Database(config) as db:
        # 1. Encontrar duplicatas
        log.info("🔍 Buscando duplicatas de email...")
        duplicates = db.fetch_all("""
            SELECT 
                email,
                COUNT(*) as count,
                array_agg(id ORDER BY id) as all_ids,
                array_agg(id ORDER BY id)[1] as keep_id
            FROM tbl_contacts 
            WHERE email IS NOT NULL AND email <> ''
            GROUP BY email 
            HAVING COUNT(*) > 1 
            ORDER BY count DESC
        """)
        
        if not duplicates:
            log.info("✅ Nenhuma duplicata encontrada!")
            return
        
        log.info(f"⚠️  Encontradas {len(duplicates)} emails duplicados")
        
        total_to_delete = 0
        for dup in duplicates:
            email = dup['email']
            count = dup['count']
            all_ids = dup['all_ids']
            keep_id = dup['keep_id']
            ids_to_delete = [id for id in all_ids if id != keep_id]
            
            log.info(f"  • {email}: {count} registros (mantendo ID {keep_id}, deletando {len(ids_to_delete)})")
            total_to_delete += len(ids_to_delete)
        
        # 2. Pedir confirmação
        print(f"\n📊 Resumo:")
        print(f"   Total de emails duplicados: {len(duplicates)}")
        print(f"   Total de registros a deletar: {total_to_delete}")
        
        response = input(f"\n⚠️  Deseja prosseguir com a remoção? (sim/não): ").strip().lower()
        
        if response != 'sim':
            log.info("❌ Operação cancelada.")
            return
        
        # 3. Remover duplicatas
        log.info("\n🗑️  Removendo duplicatas...")
        deleted_count = 0
        
        for dup in duplicates:
            all_ids = dup['all_ids']
            keep_id = dup['keep_id']
            ids_to_delete = [id for id in all_ids if id != keep_id]
            
            if ids_to_delete:
                placeholders = ','.join(['%s'] * len(ids_to_delete))
                db.execute(f"DELETE FROM tbl_contacts WHERE id IN ({placeholders})", ids_to_delete)
                deleted_count += len(ids_to_delete)
        
        log.info(f"✅ {deleted_count} registros duplicados removidos com sucesso!")
        
        # 4. Verificar resultado
        log.info("\n🔍 Verificando resultado...")
        remaining = db.fetch_one("""
            SELECT COUNT(*) as duplicates_remaining
            FROM (
                SELECT email, COUNT(*)
                FROM tbl_contacts 
                WHERE email IS NOT NULL AND email <> ''
                GROUP BY email 
                HAVING COUNT(*) > 1
            ) t
        """)
        
        if remaining and remaining['duplicates_remaining'] > 0:
            log.warning(f"⚠️  Ainda existem {remaining['duplicates_remaining']} emails duplicados!")
        else:
            log.info("✅ Nenhuma duplicata restante!")

if __name__ == "__main__":
    remove_duplicate_contacts()
