-- ============================================================================
-- MIGRAÇÃO: Adicionar constraint UNIQUE para evitar duplicatas em tbl_message_logs
-- ============================================================================
-- 
-- PROPÓSITO: Garantir que um contato não receba a mesma mensagem 2x
-- PROTEÇÃO: Nível 4 (BD) - última linha de defesa contra duplicatas
--
-- COMO EXECUTAR:
--   psql -h $PGHOST -U $PGUSER -d $PGDATABASE -f sql/migrations/add_unique_constraint_message_logs.sql
--
-- ============================================================================

-- 1. Verificar duplicatas existentes (se houver, remover antes)
DO $$
DECLARE
    dup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO dup_count
    FROM (
        SELECT contact_id, message_id, event_type, COUNT(*)
        FROM tbl_message_logs
        WHERE event_type = 'sent'
        GROUP BY contact_id, message_id, event_type
        HAVING COUNT(*) > 1
    ) duplicates;
    
    IF dup_count > 0 THEN
        RAISE NOTICE '⚠️  Encontradas % duplicatas. Removendo...', dup_count;
        
        -- Manter apenas o registro mais antigo de cada duplicata
        DELETE FROM tbl_message_logs a
        USING tbl_message_logs b
        WHERE a.contact_id = b.contact_id
          AND a.message_id = b.message_id
          AND a.event_type = b.event_type
          AND a.event_type = 'sent'
          AND a.id > b.id;
        
        RAISE NOTICE '✅ Duplicatas removidas';
    ELSE
        RAISE NOTICE '✅ Nenhuma duplicata encontrada';
    END IF;
END $$;

-- 2. Criar índice UNIQUE (se não existir)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_unique_contact_message_sent'
    ) THEN
        CREATE UNIQUE INDEX idx_unique_contact_message_sent 
        ON tbl_message_logs (contact_id, message_id, event_type)
        WHERE event_type = 'sent';
        
        RAISE NOTICE '✅ Índice UNIQUE criado: idx_unique_contact_message_sent';
    ELSE
        RAISE NOTICE '⚠️  Índice já existe: idx_unique_contact_message_sent';
    END IF;
END $$;

-- 3. Verificar resultado
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'tbl_message_logs'
  AND indexname = 'idx_unique_contact_message_sent';
